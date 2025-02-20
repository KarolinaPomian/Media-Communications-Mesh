# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import logging
import os
from pathlib import Path
from queue import Queue
import subprocess
from time import sleep
from Engine.integrity import calculate_yuv_frame_size, check_st20p_integrity
import Engine.execute
from Engine.fixtures_mcm import kill_all_existing_media_proxies
from Engine.media_files import ffmpeg_files

video_format_matches = {
    # file_format : payload format
    "YUV422PLANAR10LE": "yuv422p10le",
    "YUV422RFC4175PG2BE10": "yuv422p10rfc4175",
}

def video_file_format_to_payload_format(pixel_format: str) -> str:
    return video_format_matches.get(pixel_format, pixel_format) # matched if matches, else original


def choose_file(**params) -> dict:
    """
    Choose a file based on provided parameters.
    
    :param params: A dictionary of parameters to match (e.g., format, file_format, dimensions).
    :return: A dictionary containing file information.
    """
    for file_info in ffmpeg_files.values():
        if all(file_info.get(key) == value for key, value in params.items()):
            return file_info
    raise ValueError(f"No matching file found for parameters: {params}")

def list_vfs():
    try:
        result = subprocess.run(
            ["sudo", f"{os.environ['mtl_path']}/script/nicctl.sh", "list", "all"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logging.error(f"Failed to list VFs: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        logging.error(f"An error occurred while listing VFs: {e}")
        return None

def is_vf_present(nic: str):
    vfs_list = list_vfs()
    if vfs_list is None:
        return False
    return nic in vfs_list

def disable_vf(nic: str):
    if not is_vf_present(nic):
        logging.debug(f"VF for NIC {nic} is not present, no need to disable.")
        return

    try:
        result = subprocess.run(
            ["sudo", f"{os.environ['mtl_path']}/script/nicctl.sh", "disable_vf", nic],
            capture_output=True,
            text=True
        )
        if "succ" in result.stdout:
            logging.debug(f"Successfully disabled VF for NIC {nic}")
        else:
            logging.error(f"Failed to disable VF for NIC {nic}")
    except Exception as e:
        logging.error(f"An error occurred while disabling VF for NIC {nic}: {e}")

def create_vf(nic: str):
    result = Engine.execute.run(f"sudo {os.environ['mtl_path']}/script/nicctl.sh create_vf {nic}")
    if "succ" in result.stdout:
        logging.debug(f"Successfully created VF for NIC {nic}")
    else:
        logging.error(f"Failed to create VF for NIC {nic}")
        

def mesh_agent():
    logging.debug("Starting mesh-agent.")
    result_queue = Queue()
    process = Engine.execute.call(
        command="mesh-agent",
        cwd=".",
    )
    result = result_queue.get()
    logging.debug(f"mesh-agent output: {result}")

    yield process

    logging.debug("Stopping mesh-agent.")
    Engine.execute.killproc(process)


def media_proxy_start(sdk_port = None, agent_address = None, st2110_device = None, st2110_ip = None, rdma_ip = None, rdma_ports = None) -> Engine.execute.AsyncProcess:
    logging.debug("Starting media_proxy.")
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
    
    process = Engine.execute.call(
        command=command,
        cwd="."
    )
    sleep(0.2) # short sleep used for mesh-agent to spin up
    if process.process.returncode:
        logging.debug(f"media_proxy's return code: {process.returncode} of type {type(process.returncode)}")
    return process

def media_proxy_stop(process):
    logging.debug(f"Stopping media_proxy.")
    process.process.terminate()
    if not process.process.returncode:
        logging.debug(f"media_proxy terminated properly")
    sleep(2)

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

def remove_sent_file(full_path: Path) -> None:
    try:
        os.remove(full_path)
        logging.debug(f"Removed: {full_path}")
    # except makes the test pass if there's no file to remove
    except (FileNotFoundError, NotADirectoryError):
        logging.debug(f"Cannot remove. File does not exist: {full_path}")


def run_ffmpeg_test(media_proxy_configs: list[dict], receiver_config: dict, transmitter_config: dict, media_info = {}) -> None:
    """
    Run an FFmpeg test with the given media proxy, receiver, and transmitter configurations.

    Parameters:
    media_proxy_configs (list[dict]): List of configurations for media proxy processes.
    receiver_config (dict): Configuration for the receiver process.
    transmitter_config (dict): Configuration for the transmitter process.

    Returns:
    None
    """
    media_proxy_processes = []
    receiver_process = None
    mesh_agent_proc = None
    try:
        kill_all_existing_media_proxies()
        mesh_agent_proc = Engine.execute.call(f"mesh-agent", cwd=".")
        sleep(0.2)  # short sleep used for mesh-agent to spin up
        if mesh_agent_proc.process.returncode:
            logging.debug(f"mesh-agent's return code: {mesh_agent_proc.returncode} of type {type(mesh_agent_proc.returncode)}")
        
        for config in media_proxy_configs:
            media_proxy_process = media_proxy_start(**config)
            media_proxy_processes.append(media_proxy_process)
            logging.debug("sleeping for 0.2 seconds")
            sleep(0.2)
        
        logging.debug("sleeping for 2 seconds")
        sleep(2)
        
        receiver_process = receiver_run(receiver_config)
        logging.debug("sleeping for 5 seconds")
        sleep(5)
        
        transmitter_process = transmitter_run(transmitter_config)
        sleep(30)
        if transmitter_process.returncode != 0:
            logging.error(f"Transmitter failed with return code {transmitter_process.returncode}")
            return
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # TODO: integrity
        frame_size = calculate_yuv_frame_size(media_info.get("width"), media_info.get("height"), media_info.get("pixelFormat"))
        integrity_check = check_st20p_integrity(transmitter_config["video_file_path"], str(receiver_config["output_file_path"]), frame_size)
        logging.debug(f"Integrity: {integrity_check}")
        if "output_file_path" in receiver_config:
            remove_sent_file(receiver_config["output_file_path"])
        if not integrity_check:
            Engine.execute.log_fail("At least one of the received frames has not passed the integrity test")

        if receiver_process:
            receiver_stop(receiver_process)
        for media_proxy_process in media_proxy_processes:
            if media_proxy_process:
                media_proxy_stop(media_proxy_process)
        if mesh_agent_proc:
            mesh_agent_proc.process.terminate()
            if not mesh_agent_proc.process.returncode:
                logging.debug(f"mesh-agent terminated properly")