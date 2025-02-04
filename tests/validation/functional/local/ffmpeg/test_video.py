# single-node memory copy (memif) single-node-FFMPEG

# Test Case 1: Video Transmission with Different Formats
# Description: Test video transmission using different video formats and configurations.
import os
from time import sleep
import pytest

import Engine.client_json
import Engine.connection
import Engine.connection_json
import Engine.engine_ffmpeg as utils
import Engine.execute
import Engine.payload
from Engine.media_files import yuv_files

def test_mesh_agent_start_stop():
    mesh_agent_process = utils.mesh_agent_start()
    media_proxy_process = utils.media_proxy_start()
    receiver_process = utils.receiver_run(
        f = "mcm",
        conn_type = "multipoint-group",
        frame_rate = 60,
        video_size="2048x858",
        pixel_format="yuv422p10le",
        output_file_name="out_video.yuv"
    )
    transmitter_process = utils.transmitter_run(
        f="mcm",
        conn_type="multipoint-group",
        frame_rate=60,
        video_size="2048x858",
        pixel_format="yuv422p10le",
        input_file="/mnt/media/CosmosLaundromat_2048x858_24fps_24frames_yuv422p10le.yuv"
    )
    sleep(10)
    utils.transmitter_stop(transmitter_process)
    utils.receiver_stop(receiver_process)
    utils.media_proxy_stop(media_proxy_process)
    utils.mesh_agent_stop(mesh_agent_process)

# @pytest.mark.parametrize("video_type", [k for k in yuv_files.keys()])
# def test_video_transmission(
#     test_time, build: str, media: str, nic_port_list, video_format, video_size, pixel_format, frame_rate, conn_type, transport
# ) -> None:

#     video_file = yuv_files[video_format]

#     utils.execute_test(
#         test_time=test_time,
#         build=build,
#         nic_port_list=nic_port_list,
#         video_format=video_format,
#         video_size=video_size,
#         pixel_format=pixel_format,
#         frame_rate=frame_rate,
#         conn_type=conn_type,
#         transport=transport,
#         video_url=os.path.join(media, video_file["filename"]),
#     )


# Test Case 2: Audio Transmission with Different Configurations
# Description: Test audio transmission using different audio configurations.

# Test Case 3: Simultaneous Video and Audio Transmission
# Description: Test simultaneous transmission of video and audio streams.

# Test Case 4: Video Transmission with Different Connection Types
# Description: Test video transmission using different connection types.

# Test Case 5: Audio Transmission with Different Sample Rates
# Description: Test audio transmission using different sample rates.