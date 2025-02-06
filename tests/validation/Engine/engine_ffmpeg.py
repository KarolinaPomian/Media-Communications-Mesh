# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import logging
from queue import Queue
import subprocess
from time import sleep

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

media_proxy = {
    "device": None,
    "ip": None,
    "remote_ip": None,
    "port_range": None,
    "proxy_port": None
}

media_proxy_test_1 = {
    "device": None,
    "ip": None,
    "remote_ip": None,
    "port_range": None,
    "proxy_port": None
}

def media_proxy_start(device=None, ip=None, remote_ip=None, port_range=None, proxy_port=None):
    logging.debug("Starting media_proxy.")
    result_queue = Queue()
    command = "sudo media_proxy"
    if device:
        command += f" -d {device}"
    if ip:
        command += f" -i {ip}"
    if remote_ip:
        command += f" -r {remote_ip}"
    if port_range:
        command += f" -p {port_range}"
    if proxy_port:
        command += f" -t {proxy_port}"
    
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
    logging.debug(f"Stopping media_proxy {p}.")
    Engine.execute.killproc(process)

#3 receiver
receiver = {
    "mcm_media_proxy_port": None,
    "re": None,
    "f": None,
    "conn_type": None,
    "transport": None,
    "ip_addr": None,
    "port": None,
    "frame_rate": None,
    "video_size": None,
    "pixel_format": None,
    "output_file_path": None,
    "remote_ip": None,
    "remote_port": None
}

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

transmitter = {
    "mcm_media_proxy_port": None,
    "stream_loop": None,
    "video_file_path": None,
    "f": None,
    "conn_type": None,
    "transport": None,
    "ip_addr": None,
    "port": None,
    "frame_rate": None,
    "video_size": None,
    "pixel_format": None
}

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
        # Start mesh agent
        mesh_agent_process = mesh_agent_start()
        
        # Start media proxies
        media_proxy_processes = []
        for config in media_proxy_configs:
            media_proxy_process = media_proxy_start(**config)
            media_proxy_processes.append(media_proxy_process)
        
        # Start receiver
        receiver_process = receiver_run(receiver_config)
        
        sleep(2)
        
        # Start transmitter
        transmitter_process = transmitter_run(transmitter_config)
        
        sleep(5)
        
        # Handle transmitter failure
        handle_transmitter_failure(transmitter_process)

        # Stop receiver
        receiver_stop(receiver_process)
        
        # Stop media proxies
        for media_proxy_process in media_proxy_processes:
            media_proxy_stop(media_proxy_process)
        
        # Stop mesh agent
        mesh_agent_stop(mesh_agent_process)
    finally:
        # TODO: integrity
        pass

