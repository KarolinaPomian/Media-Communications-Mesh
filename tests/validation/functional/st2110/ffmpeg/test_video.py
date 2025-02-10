# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import os
import pytest

import Engine.engine_ffmpeg as utils
import Engine.execute
import Engine.payload
from Engine.media_files import yuv_files

@pytest.mark.parametrize("video_type", ["i720p23", "i720p24", "i720p25"])
def test_video_transmission(mesh_agent, media: str,nic_port_list,  vfio_pci_list, video_type: str) -> None:
    media_proxy_configs = [{
        "sdk_port": "8001", 
        "agent_address": None, 
        "st2110_device": vfio_pci_list[0], 
        "st2110_ip": "192.168.96.10",
        "rdma_ip": None, 
        "rdma_ports": None
    },
    {
        "sdk_port": "8002", 
        "agent_address": None, 
        "st2110_device": vfio_pci_list[1], 
        "st2110_ip": "192.168.96.11",
        "rdma_ip": None, 
        "rdma_ports": None
    }]
    payload = Engine.payload.Video(
        width=yuv_files[video_type]["width"],
        height=yuv_files[video_type]["height"],
        fps=yuv_files[video_type]["fps"],
        pixelFormat=utils.video_file_format_to_payload_format(yuv_files[video_type]["file_format"]),
    )
    # Use a specified file from media_files.py
    media_file = yuv_files[video_type]["filename"]
    transmitter_config = {  
        "mcm_media_proxy_port": None,
        "stream_loop": None,
        "video_file_path": os.path.join(media, media_file),
        "f": "mcm",
        "conn_type": "multipoint-group",
        "transport": None,
        "ip_addr": None,
        "port": None,
        "frame_rate": payload.fps,
        "video_size": f"{payload.width}x{payload.height}",
        "pixel_format": payload.pixelFormat.lower()
    }

    receiver_config = {
        "mcm_media_proxy_port": None,
        "re": None,
        "f": "mcm",
        "conn_type": "multipoint-group",
        "transport": None,
        "ip_addr": None,
        "port": None,
        "frame_rate": payload.fps,
        "video_size": f"{payload.width}x{payload.height}",
        "pixel_format": payload.pixelFormat.lower(),
        "output_file_path": "/tmp/out_video.yuv",
        "remote_ip": None,
        "remote_port": None
    }
    for nic in nic_port_list:
        utils.create_vf(nic)

    media_info = {
        "width": payload.width,
        "height": payload.height,
        "fps": payload.fps,
        "pixelFormat": payload.pixelFormat,
    }
    utils.run_ffmpeg_test(
        media_proxy_configs = media_proxy_configs,
        receiver_config = receiver_config, 
        transmitter_config = transmitter_config,
        media_info = media_info
    )
