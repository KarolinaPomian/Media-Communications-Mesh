# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import os
import pytest

import Engine.engine_ffmpeg as utils
import Engine.execute
import Engine.payload

dimensions = [dict(width=1280, height=720), dict(width=1920, height=1080)]
dimension_ids = [f'{dim["width"]}x{dim["height"]}' for dim in dimensions]
@pytest.mark.parametrize("format", ["YUV_422_10bit"])
@pytest.mark.parametrize("file_format", ["YUV422PLANAR10LE"])
@pytest.mark.parametrize("dimensions", dimensions, ids=dimension_ids)
@pytest.mark.parametrize("frame_rate", [23, 24, 25, 30, 60])
def test_video_transmission(mesh_agent, media: str,nic_port_list,  vfio_pci_list, format: str, file_format: str, dimensions: dict,  frame_rate: int) -> None:
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

    file_info = utils.choose_file(format=format, file_format=file_format, width=dimensions['width'], height=dimensions['height'])
    
    payload = Engine.payload.Video(
        width=dimensions['width'],
        height=dimensions['height'],
        fps=frame_rate,
        pixelFormat=utils.video_file_format_to_payload_format(file_info["file_format"]),
    )
    
    media_file = file_info["filename"]
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
