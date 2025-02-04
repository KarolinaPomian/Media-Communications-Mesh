# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import logging
from queue import Queue

import Engine.execute

#1 mesh agent
def mesh_agent_start():
    logging.debug("Starting mesh-agent.")
    result_queue = Queue()
    process = Engine.execute.run_in_background(
        command="mesh-agent",
        cwd="/usr/local/bin",
        env=None,
        result_queue=result_queue,
        timeout=0,
    )
    result = result_queue.get()
    logging.debug(f"mesh-agent output: {result}")
    return process

def mesh_agent_stop(process):
    logging.debug("Stopping mesh-agent.")
    Engine.execute.killproc(process)


#2 media proxy
def media_proxy_start():
    logging.debug("Starting media_proxy.")
    result_queue = Queue()
    process = Engine.execute.run_in_background(
        command="sudo media_proxy",
        cwd="/usr/local/bin",
        env=None,
        result_queue=result_queue,
        timeout=0,
    )
    result = result_queue.get()
    logging.debug(f"media_proxy output: {result}")
    return process

def media_proxy_stop(process):
    logging.debug("Stopping media_proxy.")
    Engine.execute.killproc(process)

#3 receiver
def receiver_run(f:str, conn_type: str, frame_rate: int, video_size: str, pixel_format: str, output_file_name: str):
    logging.debug("Starting receiver.")
    result_queue = Queue()
    process = Engine.execute.run_in_background(
        command=f"sudo ffmpeg -f {f} -conn_type {conn_type} -frame_rate {frame_rate} -video_size {video_size} -pixel_format {pixel_format} -i - {output_file_name} -y",
        cwd="/usr/local/bin",
        env=None,
        result_queue=result_queue,
        timeout=0,
    )
    result = result_queue.get()
    logging.debug(f"receiver output: {result}")
    return process

def receiver_stop(process):
    logging.debug("Stopping receiver.")
    Engine.execute.killproc(process)

#4 transmitter
def transmitter_run(f:str, conn_type: str, frame_rate: int, video_size: str, pixel_format: str, input_file: str):
    logging.debug("Starting transmitter.")
    result_queue = Queue()
    process = Engine.execute.run_in_background(
        command=f"sudo ffmpeg -stream_loop -1 -re -video_size {video_size} -pixel_format {pixel_format} -i {input_file} -f mcm -conn_type {conn_type} -frame_rate {frame_rate} -video_size {video_size} -pixel_format {pixel_format} -",
        cwd="/usr/local/bin",
        env=None,
        result_queue=result_queue,
        timeout=0,
    )
    result = result_queue.get()
    logging.debug(f"transmitter output: {result}")
    return process


def transmitter_stop(process):   
    logging.debug("Stopping transmitter.")
    Engine.execute.killproc(process)
 

# execute test
#1 mesh agent on
#2 media proxy on + param
#3 receiver on + param
#4 transmitter on + param
# log
# assure transmitter stop
# assure receiver stop
# assure media proxy stop
# assure mesh agent stop
# check file
# remove file


#-------------------------------------------------------------------------------
# import copy
# import os
# import re
# import time

# from tests.Engine import RxTxApp, rxtxapp_config
# from tests.Engine.const import LOG_FOLDER
# from tests.Engine.execute import call, log_fail, run, wait

# RXTXAPP_PATH = "./tests/tools/RxTxApp/build/RxTxApp"

# ip_dict = dict(
#     rx_interfaces="192.168.96.2",
#     tx_interfaces="192.168.96.3",
#     rx_sessions="239.168.85.20",
#     tx_sessions="239.168.85.20",
# )

# ip_dict_rgb24_multiple = dict(
#     p_sip_1="192.168.96.2",
#     p_sip_2="192.168.96.3",
#     p_tx_ip_1="239.168.108.202",
#     p_tx_ip_2="239.168.108.203",
# )


# def execute_test(
#     test_time: int,
#     build: str,
#     nic_port_list: list,
#     type_: str,
#     video_format: str,
#     pg_format: str,
#     video_url: str,
#     output_format: str,
#     multiple_sessions: bool = False,
#     tx_is_ffmpeg: bool = True,
# ):
#     video_size, fps = decode_video_format_16_9(video_format)

#     match output_format:
#         case "yuv":
#             ffmpeg_rx_f_flag = "-f rawvideo"
#         case "h264":
#             ffmpeg_rx_f_flag = "-c:v libopenh264"

#     if not multiple_sessions:
#         output_files = create_empty_output_files(output_format, 1)
#         rx_cmd = (
#             f"ffmpeg -p_port {nic_port_list[0]} -p_sip {ip_dict['rx_interfaces']} -p_rx_ip {ip_dict['rx_sessions']}"
#             + f" -udp_port 20000 -payload_type 112 -fps {fps} -pix_fmt yuv422p10le -video_size {video_size}"
#             + f" -f mtl_st20p -i k {ffmpeg_rx_f_flag} {output_files[0]} -y"
#         )

#         if tx_is_ffmpeg:
#             tx_cmd = (
#                 f"ffmpeg -stream_loop -1 -video_size {video_size} -f rawvideo -pix_fmt yuv422p10le"
#                 + f" -i {video_url} -filter:v fps={fps} -p_port {nic_port_list[1]} -p_sip {ip_dict['tx_interfaces']}"
#                 + f" -p_tx_ip {ip_dict['tx_sessions']} -udp_port 20000 -payload_type 112 -f mtl_st20p -"
#             )
#         else:  # tx is rxtxapp
#             tx_config_file = generate_rxtxapp_tx_config(
#                 nic_port_list[1], type_, video_format, pg_format, video_url
#             )
#             tx_cmd = f"{RXTXAPP_PATH} --config_file {tx_config_file}"

#     else:  # multiple sessions
#         output_files = create_empty_output_files(output_format, 2)
#         rx_cmd = (
#             f"ffmpeg -p_sip {ip_dict['rx_interfaces']} "
#             + f"-p_port {nic_port_list[0]} -p_rx_ip {ip_dict['rx_sessions']} -udp_port 20000 -payload_type 112"
#             + f" -fps {fps} -pix_fmt yuv422p10le -video_size {video_size} -f mtl_st20p -i 1 "
#             + f"-p_port {nic_port_list[0]} -p_rx_ip {ip_dict['rx_sessions']} -udp_port 20002 -payload_type 112"
#             + f" -fps {fps} -pix_fmt yuv422p10le -video_size {video_size} -f mtl_st20p -i 2 "
#             + f"-map 0:0 {ffmpeg_rx_f_flag} {output_files[0]} -y -map 1:0 {ffmpeg_rx_f_flag} {output_files[1]} -y"
#         )

#         if tx_is_ffmpeg:
#             tx_cmd = (
#                 f"ffmpeg -stream_loop -1 -video_size {video_size} -f rawvideo -pix_fmt yuv422p10le -i {video_url}"
#                 + f" -filter:v fps={fps} -p_port {nic_port_list[1]} -p_sip {ip_dict['tx_interfaces']}"
#                 + f" -p_tx_ip {ip_dict['tx_sessions']} -udp_port 20000 -payload_type 112 -f mtl_st20p -"
#             )
#         else:  # tx is rxtxapp
#             tx_config_file = generate_rxtxapp_tx_config(
#                 nic_port_list[1], type_, video_format, pg_format, video_url, True
#             )
#             tx_cmd = f"{RXTXAPP_PATH} --config_file {tx_config_file}"

#     rx_proc = call(rx_cmd, build, test_time, True)
#     tx_proc = call(tx_cmd, build, test_time, True)

#     wait(rx_proc)
#     wait(tx_proc)

#     passed = False

#     match output_format:
#         case "yuv":
#             passed = check_output_video_yuv(output_files[0])
#         case "h264":
#             passed = check_output_video_h264(output_files[0], video_size)

#     if not passed:
#         log_fail("test failed")


# def execute_test_rgb24(
#     test_time: int,
#     build: str,
#     nic_port_list: list,
#     type_: str,
#     video_format: str,
#     pg_format: str,
#     video_url: str,
# ):
#     video_size, fps = decode_video_format_16_9(video_format)

#     rx_config_file = generate_rxtxapp_rx_config(
#         nic_port_list[0], type_, [video_format], pg_format
#     )
#     rx_cmd = f"{RXTXAPP_PATH} --config_file {rx_config_file}"

#     tx_cmd = (
#         f"ffmpeg -stream_loop -1 -video_size {video_size} -f rawvideo -pix_fmt rgb24 -i {video_url}"
#         + f" -filter:v fps={fps} -p_port {nic_port_list[1]} -p_sip {ip_dict['tx_interfaces']}"
#         + f" -p_tx_ip {ip_dict['tx_sessions']} -udp_port 20000 -payload_type 112 -f mtl_st20p -"
#     )

#     rx_proc = call(rx_cmd, build, test_time, True)
#     tx_proc = call(tx_cmd, build, test_time, True)

#     wait(rx_proc)
#     wait(tx_proc)

#     if not check_output_rgb24(rx_proc.output, 1):
#         log_fail("rx video sessions failed")

#     time.sleep(5)


# def execute_test_rgb24_multiple(
#     test_time: int,
#     build: str,
#     nic_port_list: list,
#     type_: str,
#     video_format_list: list,
#     pg_format: str,
#     video_url_list: list,
# ):
#     video_size_1, fps_1 = decode_video_format_16_9(video_format_list[0])
#     video_size_2, fps_2 = decode_video_format_16_9(video_format_list[1])

#     rx_config_file = generate_rxtxapp_rx_config_rgb24_multiple(
#         nic_port_list[:2], type_, video_format_list, pg_format, True
#     )
#     rx_cmd = f"{RXTXAPP_PATH} --config_file {rx_config_file}"

#     tx_1_cmd = (
#         f"ffmpeg -stream_loop -1 -video_size {video_size_1} -f rawvideo -pix_fmt rgb24 -i {video_url_list[0]}"
#         + f" -filter:v fps={fps_1} -p_port {nic_port_list[2]} -p_sip {ip_dict_rgb24_multiple['p_sip_1']}"
#         + f" -p_tx_ip {ip_dict_rgb24_multiple['p_tx_ip_1']} -udp_port 20000 -payload_type 112 -f mtl_st20p -"
#     )
#     tx_2_cmd = (
#         f"ffmpeg -stream_loop -1 -video_size {video_size_2} -f rawvideo -pix_fmt rgb24 -i {video_url_list[1]}"
#         + f" -filter:v fps={fps_2} -p_port {nic_port_list[3]} -p_sip {ip_dict_rgb24_multiple['p_sip_2']}"
#         + f" -p_tx_ip {ip_dict_rgb24_multiple['p_tx_ip_2']} -udp_port 20000 -payload_type 112 -f mtl_st20p -"
#     )

#     rx_proc = call(rx_cmd, build, test_time, True)
#     tx_1_proc = call(tx_1_cmd, build, test_time, True)
#     tx_2_proc = call(tx_2_cmd, build, test_time, True)

#     wait(rx_proc)
#     wait(tx_1_proc)
#     wait(tx_2_proc)

#     if not check_output_rgb24(rx_proc.output, 2):
#         log_fail("rx video session failed")

#     time.sleep(5)


# def check_output_video_yuv(output_file: str):
#     output_file_size = os.path.getsize(output_file)

#     if output_file_size != 0:
#         return True

#     return False


# def check_output_video_h264(output_file: str, video_size: str):
#     code_name_pattern = r"codec_name=([^\n]+)"
#     width_pattern = r"width=(\d+)"
#     height_pattern = r"height=(\d+)"

#     ffproble_proc = run(f"ffprobe -v error -show_format -show_streams {output_file}")

#     codec_name_match = re.search(code_name_pattern, ffproble_proc.stdout)
#     width_match = re.search(width_pattern, ffproble_proc.stdout)
#     height_match = re.search(height_pattern, ffproble_proc.stdout)

#     if codec_name_match and width_match and height_match:
#         codec_name = codec_name_match.group(1)
#         width = width_match.group(1)
#         height = height_match.group(1)

#         return codec_name == "h264" and f"{width}x{height}" == video_size

#     return False


# def check_output_rgb24(rx_output: str, number_of_sessions: int):
#     lines = rx_output.splitlines()
#     ok_cnt = 0

#     for line in lines:
#         if "app_rx_video_result" in line and "OK" in line:
#             ok_cnt += 1

#     return ok_cnt == number_of_sessions


# def create_empty_output_files(output_format: str, number_of_files: int = 1) -> str:
#     output_files = []

#     for i in range(number_of_files):
#         output_file = os.path.join(
#             os.getcwd(),
#             LOG_FOLDER,
#             "latest",
#             f"{get_case_id()}_out_{i}.{output_format}",
#         )
#         output_files.append(output_file)

#         with open(output_file, "w"):
#             pass

#     return output_files


# def decode_video_format_16_9(video_format: str) -> tuple:
#     pattern = r"i(\d+)([ip])(\d+)"
#     match = re.search(pattern, video_format)

#     if match:
#         height = match.group(1)
#         width = int(height) * (16 / 9)
#         fps = match.group(3)
#         return f"{int(width)}x{height}", int(fps)
#     else:
#         log_fail("Invalid video format")
#         return None


# def get_case_id() -> str:
#     case_id = os.environ["PYTEST_CURRENT_TEST"]
#     return case_id[: case_id.rfind("(") - 1]


# def generate_rxtxapp_rx_config(
#     nic_port: str,
#     type_: str,
#     video_format_list: list,
#     pg_format: str,
#     multiple_sessions: bool = False,
# ) -> str:
#     config = copy.deepcopy(rxtxapp_config.config_empty_rx)
#     config["interfaces"][0]["name"] = nic_port
#     config["interfaces"][0]["ip"] = ip_dict["rx_interfaces"]
#     config["rx_sessions"][0]["ip"][0] = ip_dict["rx_sessions"]

#     rx_session = copy.deepcopy(rxtxapp_config.config_rx_video_session)
#     config["rx_sessions"][0]["video"].append(rx_session)
#     config["rx_sessions"][0]["video"][0]["type"] = type_
#     config["rx_sessions"][0]["video"][0]["video_format"] = video_format_list[0]
#     config["rx_sessions"][0]["video"][0]["pg_format"] = pg_format

#     if multiple_sessions:
#         rx_session = copy.deepcopy(rxtxapp_config.config_rx_video_session)
#         config["rx_sessions"][0]["video"].append(rx_session)
#         config["rx_sessions"][0]["video"][1]["type"] = type_
#         config["rx_sessions"][0]["video"][1]["start_port"] = 20002
#         config["rx_sessions"][0]["video"][1]["video_format"] = video_format_list[1]
#         config["rx_sessions"][0]["video"][1]["pg_format"] = pg_format

#     case_id = get_case_id()
#     config_file = os.path.join(os.getcwd(), LOG_FOLDER, "latest", f"{case_id}_rx.json")
#     RxTxApp.save_as_json(config_file, config)
#     return config_file


# def generate_rxtxapp_rx_config_rgb24_multiple(
#     nic_port_list: list,
#     type_: str,
#     video_format_list: list,
#     pg_format: str,
#     multiple_sessions: bool = False,
# ) -> str:
#     config = copy.deepcopy(rxtxapp_config.config_empty_rx_rgb24_multiple)
#     config["interfaces"][0]["name"] = nic_port_list[0]
#     config["interfaces"][0]["ip"] = ip_dict_rgb24_multiple["p_sip_1"]
#     config["rx_sessions"][0]["ip"][0] = ip_dict_rgb24_multiple["p_tx_ip_1"]

#     config["interfaces"][1]["name"] = nic_port_list[1]
#     config["interfaces"][1]["ip"] = ip_dict_rgb24_multiple["p_sip_2"]
#     config["rx_sessions"][1]["ip"][0] = ip_dict_rgb24_multiple["p_tx_ip_2"]

#     rx_session_1 = copy.deepcopy(rxtxapp_config.config_rx_video_session)
#     config["rx_sessions"][0]["video"].append(rx_session_1)
#     config["rx_sessions"][0]["video"][0]["type"] = type_
#     config["rx_sessions"][0]["video"][0]["video_format"] = video_format_list[0]
#     config["rx_sessions"][0]["video"][0]["pg_format"] = pg_format

#     rx_session_2 = copy.deepcopy(rxtxapp_config.config_rx_video_session)
#     config["rx_sessions"][1]["video"].append(rx_session_2)
#     config["rx_sessions"][1]["video"][0]["type"] = type_
#     config["rx_sessions"][1]["video"][0]["video_format"] = video_format_list[1]
#     config["rx_sessions"][1]["video"][0]["pg_format"] = pg_format

#     case_id = get_case_id()
#     config_file = os.path.join(os.getcwd(), LOG_FOLDER, "latest", f"{case_id}_rx.json")
#     RxTxApp.save_as_json(config_file, config)
#     return config_file


# def generate_rxtxapp_tx_config(
#     nic_port: str,
#     type_: str,
#     video_format: str,
#     pg_format: str,
#     video_url: str,
#     multiple_sessions: bool = False,
# ) -> str:
#     config = copy.deepcopy(rxtxapp_config.config_empty_tx)
#     config["interfaces"][0]["name"] = nic_port
#     config["interfaces"][0]["ip"] = ip_dict["tx_interfaces"]
#     config["tx_sessions"][0]["dip"][0] = ip_dict["tx_sessions"]

#     tx_session = copy.deepcopy(rxtxapp_config.config_tx_video_session)
#     config["tx_sessions"][0]["video"].append(tx_session)
#     config["tx_sessions"][0]["video"][0]["type"] = type_
#     config["tx_sessions"][0]["video"][0]["video_format"] = video_format
#     config["tx_sessions"][0]["video"][0]["pg_format"] = pg_format
#     config["tx_sessions"][0]["video"][0]["video_url"] = video_url

#     if multiple_sessions:
#         tx_session = copy.deepcopy(rxtxapp_config.config_tx_video_session)
#         config["tx_sessions"][0]["video"].append(tx_session)
#         config["tx_sessions"][0]["video"][1]["type"] = type_
#         config["tx_sessions"][0]["video"][1]["start_port"] = 20002
#         config["tx_sessions"][0]["video"][1]["video_format"] = video_format
#         config["tx_sessions"][0]["video"][1]["pg_format"] = pg_format
#         config["tx_sessions"][0]["video"][1]["video_url"] = video_url

#     case_id = get_case_id()
#     config_file = os.path.join(os.getcwd(), LOG_FOLDER, "latest", f"{case_id}_tx.json")
#     RxTxApp.save_as_json(config_file, config)
#     return config_file

# Receiver side setup
# Start Media Proxy

# sudo media_proxy -d 0000:32:01.1 -i 192.168.96.11 -r 192.168.97.11 -p 9200-9299 -t 8002
# Start FFmpeg to receive frames from Media Communications Mesh and stream to a remote machine via UDP

# sudo MCM_MEDIA_PROXY_PORT=8002 ffmpeg -re -f mcm \
#    -conn_type st2110 \
#    -transport st2110-20 \
#    -ip_addr 192.168.96.10 \
#    -port 9001 \
#    -frame_rate 24 \
#    -video_size nhd \
#    -pixel_format yuv422p10le \
#    -i - -vcodec mpeg4 -f mpegts udp://<remote-ip>:<remote-port>
# Sender side setup
# Start Media Proxy

# sudo media_proxy -d 0000:32:01.0 -i 192.168.96.10 -r 192.168.97.10 -p 9100-9199 -t 8001
# Start FFmpeg to stream a video file to the receiver via Media Communications Mesh

# sudo MCM_MEDIA_PROXY_PORT=8001 ffmpeg -i <video-file-path> -f mcm \
#    -conn_type st2110 \
#    -transport st2110-20 \
#    -ip_addr 192.168.96.11 \
#    -port 9001 \
#    -frame_rate 24 \
#    -video_size nhd \
#    -pixel_format yuv422p10le -
# When working with raw video files that lack metadata, you must explicitly provide FFmpeg with the necessary video frame details. This includes specifying the format -f rawvideo, pixel format -pix_fmt, and resolution -s WxH. For example:

# ffmpeg -f rawvideo -pix_fmt yuv422p10le -s 1920x1080 -i <video-file-path> ...
# VLC player setup
# On the remote machine start the VLC player and open a network stream from the next URL:

# udp://@:1234