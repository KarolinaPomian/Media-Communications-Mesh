# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import logging
import os
from queue import Queue
import subprocess
from time import sleep

import Engine.execute

video_format_matches = {
    # file_format : payload format
    "YUV422PLANAR10LE": "yuv422p10le",
    "YUV422RFC4175PG2BE10": "yuv422p10rfc4175",
}

def video_file_format_to_payload_format(pixel_format: str) -> str:
    return video_format_matches.get(pixel_format, pixel_format) # matched if matches, else original

def disable_vf(nic: str):
    Engine.execute.run(f"sudo {os.environ['mtl_path']}/script/nicctl.sh disable_vf {nic}", timeout=120)

def create_vf(nic: str):
    Engine.execute.run(f"sudo {os.environ['mtl_path']}/script/nicctl.sh create_vf {nic}", timeout=120)

#2 media proxy
def media_proxy_start(sdk_port = None, agent_address = None, st2110_device = None, st2110_ip = None, rdma_ip = None, rdma_ports = None) -> Engine.execute.AsyncProcess:
    logging.debug("Starting media_proxy.")
    result_queue = Queue()
    command = "sudo media_proxy"
    if sdk_port:
        command += f" -t {sdk_port}"
    if agent_address:
        command += f" -a {agent_address}"
    if st2110_device:
        command += f" -d {st2110_device}"
    if st2110_ip:
        command += f" -i {st2110_ip}"
    if rdma_ip:
        command += f" -r {rdma_ip}"
    if rdma_ports:
        command += f" -p {rdma_ports}"
    
    process = Engine.execute.run_in_background(
        command=command,
        cwd="/usr/local/bin",
        env=None,
        result_queue=result_queue,
        timeout=0,
    )
    result = result_queue.get()
    logging.debug(f"media_proxy output: {result}")
    return process

def media_proxy_stop(process):
    logging.debug(f"Stopping media_proxy.")
    Engine.execute.killproc(process)

#3 receiver
def receiver_run(config: dict) -> Engine.execute.AsyncProcess:
    logging.debug("Starting receiver.")
    command = "sudo"
    if config.get("mcm_media_proxy_port"):
        command += f" MCM_MEDIA_PROXY_PORT={config['mcm_media_proxy_port']}"
    command += f" ffmpeg"
    if config.get("re"):
        command += f" -re"
    if config.get("f"):
        command += f" -f {config['f']}"
    if config.get("conn_type"):
        command += f" -conn_type {config['conn_type']}"
    if config.get("transport"):
        command += f" -transport {config['transport']}"
    if config.get("ip_addr"):
        command += f" -ip_addr {config['ip_addr']}"
    if config.get("port"):
        command += f" -port {config['port']}"
    if config.get("frame_rate"):
        command += f" -frame_rate {config['frame_rate']}"
    if config.get("video_size"):
        command += f" -video_size {config['video_size']}"
    if config.get("pixel_format"):
        command += f" -pixel_format {config['pixel_format']}"
    if config.get("output_file_path"):
        command += f" -i - {config['output_file_path']} -y"
    if config.get("remote_ip") and config.get("remote_port"):
        command += f" -i - -vcodec mpeg4 -f mpegts udp://{config['remote_ip']}:{config['remote_port']}"
    
    return Engine.execute.call(command, cwd="/usr/local/bin", timeout=0)

def receiver_stop(process: Engine.execute.AsyncProcess) -> None:
    logging.debug("Stopping receiver.")
    process.process.terminate()
    process.process.wait()



#4 transmitter
def transmitter_run(config: dict) -> subprocess.CompletedProcess:
    logging.debug("Starting transmitter.")
    command = "sudo"
    if config.get("mcm_media_proxy_port"):
        command += f" MCM_MEDIA_PROXY_PORT={config['mcm_media_proxy_port']}"
    command += f" ffmpeg"
    if config.get("stream_loop"):
        command += f" -stream_loop -1" 
    command += f" -re"
    if config.get("video_size"):
        command += f" -video_size {config['video_size']}"
    if config.get("pixel_format"):
        command += f" -pixel_format {config['pixel_format']}"
    if config.get("video_file_path"):
        command += f" -i {config['video_file_path']}"
    if config.get("f"):
        command += f" -f {config['f']}"
    if config.get("conn_type"):
        command += f" -conn_type {config['conn_type']}"
    if config.get("transport"):
        command += f" -transport {config['transport']}"
    if config.get("ip_addr"):
        command += f" -ip_addr {config['ip_addr']}"
    if config.get("port"):
        command += f" -port {config['port']}"
    if config.get("frame_rate"):
        command += f" -frame_rate {config['frame_rate']}"
    if config.get("video_size"):
        command += f" -video_size {config['video_size']}"
    if config.get("pixel_format"):
        command += f" -pixel_format {config['pixel_format']}"
    command += " -"
    
    return Engine.execute.run(command, cwd="/usr/local/bin")

def handle_transmitter_failure(tx: subprocess.CompletedProcess) -> None:
    if tx.returncode != 0:
        Engine.execute.log_fail(f"Transmitter failed with return code {tx.returncode}")


# execute test
def run(media_proxy_configs: list[dict], receiver_config: dict, transmitter_config: dict) -> None:
    try:
        media_proxy_processes = []
        for config in media_proxy_configs:
            media_proxy_process = media_proxy_start(**config)
            media_proxy_processes.append(media_proxy_process)
        receiver_process = receiver_run(receiver_config)       
        transmitter_process = transmitter_run(transmitter_config)
        handle_transmitter_failure(transmitter_process)
        receiver_stop(receiver_process)
        for media_proxy_process in media_proxy_processes:
            media_proxy_stop(media_proxy_process)
    finally:
        # TODO: integrity
        pass

