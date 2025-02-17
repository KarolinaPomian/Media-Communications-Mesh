# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import os
import pytest

import Engine.engine_ffmpeg as utils
import Engine.execute
import Engine.payload

# Define the dimensions and their IDs
dimensions = [dict(width=1280, height=720), dict(width=1920, height=1080), dict(width=3840, height=2160)]
dimension_ids = [f'{dim["width"]}x{dim["height"]}' for dim in dimensions]

# ST20ffmpeg6.1 Tests
@pytest.mark.parametrize("dimensions", [dict(width=1280, height=720), dict(width=1920, height=1080)], ids=dimension_ids[:2])
@pytest.mark.parametrize("frame_rate", [30, 60])
def test_st20ffmpeg(nic_port_list, vfio_pci_list, dimensions: dict, frame_rate: int) -> None:
    format = "YUV_422_10bit"
    file_format = "YUV422PLANAR10LE"
    protocol = "auto"
    conn_type = "st2110"
    transport = "st2110-20"
    print(f"ST20ffmpeg: VIDEO_SIZE={dimensions['width']}x{dimensions['height']}; PIXEL_FORMAT={file_format}; FRAME_RATE={frame_rate}; PROTOCOL={protocol}")
    run_video_transmission(io_pci_list, format, file_format, dimensions, frame_rate, conn_type, transport)

# ST22ffmpeg Tests
@pytest.mark.parametrize("dimensions", [dict(width=1920, height=1080), dict(width=3840, height=2160)], ids=dimension_ids[1:])
@pytest.mark.parametrize("frame_rate", [30, 60])
def test_st22ffmpeg(list, dimensions: dict, frame_rate: int) -> None:
    format = "YUV_422_10bit"
    file_format = "YUV422PLANAR10LE"
    payload_type = "st22"
    protocol = "auto"
    print(f"ST22ffmpeg: VIDEO_SIZE={dimensions['width']}x{dimensions['height']}; PIXEL_FORMAT={file_format}; FRAME_RATE={frame_rate}; PAYLOAD_TYPE={payload_type}; PROTOCOL={protocol}")
    run_video_transmission(media, nic_port_list, vfio_pci_list, format, file_format, dimensions, frame_rate)

# ST30ffmpeg Tests
audio_files = dict(
    PCM8={
        "filename": "bits8_channels2_rate48000.pcm",
        "format": "pcm_s8",
        "channels": 2,
        "sample_rate": 48000,
    },
    PCM16={
        "filename": "bits16_channels2_rate48000.pcm",
        "format": "pcm_s16be",
        "channels": 2,
        "sample_rate": 48000,
    },
    PCM24={
        "filename": "bits24_channels2_rate48000.pcm",
        "format": "pcm_s24be",
        "channels": 2,
        "sample_rate": 48000,
    },
)

@pytest.mark.parametrize("audio_config", list(audio_files.values()), ids=list(audio_files.keys()))
def test_st30ffmpeg(media: str, nic_port_list, vfio_pci_list, audio_config: dict) -> None:
    print(f"ST30ffmpeg: SAMPLE_RATE={audio_config['sample_rate']}; BIT_DEPTH={audio_config['format']}; CHANNELS={audio_config['channels']}")
    run_audio_transmission(media, nic_port_list, vfio_pci_list, audio_config)

# The actual test function that runs the video transmission test
def run_video_transmission(media: str, nic_port_list, vfio_pci_list, format: str, file_format: str, dimensions: dict, frame_rate: int, conn_type: str, transport: str) -> None:
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
        "conn_type": conn_type,
        "transport": transport,
        "ip_addr": None,
        "port": 9001,
        "frame_rate": payload.fps,
        "video_size": f"{payload.width}x{payload.height}",
        "pixel_format": payload.pixelFormat.lower()
    }

    receiver_config = {
        "mcm_media_proxy_port": None,
        "re": None,
        "f": "mcm",
        "conn_type": conn_type,
        "transport": transport,
        "ip_addr": None,
        "port": 9001,
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

# The actual test function that runs the audio transmission test
def run_audio_transmission(media: str, nic_port_list, vfio_pci_list, audio_config: dict) -> None:
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

    payload = Engine.payload.Audio(
        sample_rate=audio_config["sample_rate"],
        bit_depth=audio_config["format"],
        channels=audio_config["channels"],
    )
    
    media_file = audio_config["filename"]
    transmitter_config = {  
        "mcm_media_proxy_port": None,
        "stream_loop": None,
        "audio_file_path": os.path.join(media, media_file),
        "f": "mcm",
        "conn_type": "multipoint-group",
        "transport": None,
        "ip_addr": None,
        "port": None,
        "sample_rate": payload.sample_rate,
        "bit_depth": payload.bit_depth,
        "channels": payload.channels
    }

    receiver_config = {
        "mcm_media_proxy_port": None,
        "re": None,
        "f": "mcm",
        "conn_type": "multipoint-group",
        "transport": None,
        "ip_addr": None,
        "port": None,
        "sample_rate": payload.sample_rate,
        "bit_depth": payload.bit_depth,
        "channels": payload.channels,
        "output_file_path": "/tmp/out_audio.pcm",
        "remote_ip": None,
        "remote_port": None
    }
    for nic in nic_port_list:
        utils.create_vf(nic)

    media_info = {
        "sample_rate": payload.sample_rate,
        "bit_depth": payload.bit_depth,
        "channels": payload.channels,
    }
    utils.run_ffmpeg_test(
        media_proxy_configs = media_proxy_configs,
        receiver_config = receiver_config, 
        transmitter_config = transmitter_config,
        media_info = media_info
    )