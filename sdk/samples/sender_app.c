/*
 * SPDX-FileCopyrightText: Copyright (c) 2024 Intel Corporation
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

// TODO: Split the code, so video, audio and ancillary are separate sub-apps
// TODO: Push all code that duplicates in recver_app to sample_common

#include <assert.h>
#include <bsd/string.h>
#include <getopt.h>
#include <linux/limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include "sample_common.c"

static volatile bool keepRunning = true;
static char input_file[128] = "";

void intHandler(int dummy)
{
    keepRunning = 0;
}

int read_test_data(FILE* fp, mcm_buffer* buf, uint32_t frame_size)
{
    int ret = 0;

    assert(fp != NULL && buf != NULL);
    assert(buf->len >= frame_size);

    memset(buf->data, 0, buf->len);

    if (fread(buf->data, 1, frame_size, fp) < 1) {
        ret = -1;
    }
    if(ret >= 0 ) {
        buf->len = frame_size;
    }
    return ret;
}

int gen_test_data(mcm_buffer* buf, uint32_t frame_count)
{
    /* operate on the buffer */
    void* ptr = buf->data;

    /* frame counter */
    *(uint32_t*)ptr = frame_count;
    ptr += sizeof(frame_count);

    /* timestamp */
    clock_gettime( CLOCK_REALTIME , (struct timespec*)ptr);

    return 0;
}

int main(int argc, char** argv)
{
    char recv_addr[46] = DEFAULT_RECV_IP;
    char recv_port[6] = DEFAULT_RECV_PORT;
    char send_addr[46] = DEFAULT_SEND_IP;
    char send_port[6] = DEFAULT_SEND_PORT;

    char payload_type[32] = "";
    char protocol_type[32] = "";
    char pix_fmt_string[32] = DEFAULT_VIDEO_FMT;
    char socket_path[108] = DEFAULT_MEMIF_SOCKET_PATH;
    uint8_t is_master = 1; // default for sender
    uint32_t interface_id = DEFAULT_MEMIF_INTERFACE_ID;
    bool loop = DEFAULT_INFINITY_LOOP;

    /* video resolution */
    uint32_t width = DEFAULT_FRAME_WIDTH;
    uint32_t height = DEFAULT_FRAME_HEIGHT;
    double vid_fps = DEFAULT_FPS;
    video_pixel_format pix_fmt = PIX_FMT_YUV422P_10BIT_LE;
    uint32_t frame_size = 0;

    char audio_type[5] = DEFAULT_AUDIO_TYPE;
    char audio_format[5] = DEFAULT_AUDIO_FORMAT;
    char audio_sampling[3] = DEFAULT_AUDIO_SAMPLING;
    char audio_ptime[6] = DEFAULT_AUDIO_PTIME;
    char anc_type[5] = DEFAULT_ANC_TYPE;
    char payload_codec[6] = DEFAULT_PAYLOAD_CODEC;
    uint32_t audio_channels = DEFAULT_AUDIO_CHANNELS;

    mcm_conn_context* dp_ctx = NULL;
    mcm_conn_param param = { 0 };
    mcm_buffer* buf = NULL;
    uint32_t total_num = DEFAULT_TOTAL_NUM;

    int help_flag = 0;
    int opt;
    struct option longopts[] = {
        { "help", no_argument, &help_flag, 'H' },
        { "width", required_argument, NULL, 'w' },
        { "height", required_argument, NULL, 'h' },
        { "fps", required_argument, NULL, 'f' },
        { "rcv_ip", required_argument, NULL, 'r' },
        { "rcv_port", required_argument, NULL, 'i' },
        { "send_ip", required_argument, NULL, 's' },
        { "send_port", required_argument, NULL, 'p' },
        { "protocol", required_argument, NULL, 'o' },
        { "type", required_argument, NULL, 't' },
        { "socketpath", required_argument, NULL, 'k' },
        { "master", required_argument, NULL, 'm' },
        { "interfaceid", required_argument, NULL, 'd' },
        { "file", required_argument, NULL, 'b' },
        { "pix_fmt", required_argument, NULL, 'x' },
        { "audio_type", required_argument, NULL, 'a' },
        { "audio_format", required_argument, NULL, 'j' },
        { "audio_sampling", required_argument, NULL, 'g' },
        { "audio_ptime", required_argument, NULL, 'e' },
        { "audio_channels", required_argument, NULL, 'c' },
        { "anc_type", required_argument, NULL, 'q' },
        { "number", required_argument, NULL, 'n' },
        { "loop", required_argument, NULL, 'l' },
        { 0 }
    };

    /* infinite loop, to be broken when we are done parsing options */
    while (1) {
        opt = getopt_long(argc, argv,
                          "Hw:h:f:r:i:s:p:o:t:k:m:d:b:x:a:j:g:e:c:q:n:l:",
                          longopts, 0);
        if (opt == -1) {
            break;
        }

        switch (opt) {
        case 'H':
            help_flag = 1;
            break;
        case 'w':
            width = atoi(optarg);
            break;
        case 'h':
            height = atoi(optarg);
            break;
        case 'f':
            vid_fps = atof(optarg);
            break;
        case 'r':
            strlcpy(recv_addr, optarg, sizeof(recv_addr));
            break;
        case 'i':
            strlcpy(recv_port, optarg, sizeof(recv_port));
            break;
        case 's':
            strlcpy(send_addr, optarg, sizeof(send_addr));
            break;
        case 'p':
            strlcpy(send_port, optarg, sizeof(send_port));
            break;
        case 'o':
            strlcpy(protocol_type, optarg, sizeof(protocol_type));
            break;
        case 't':
            strlcpy(payload_type, optarg, sizeof(payload_type));
            break;
        case 'k':
            strlcpy(socket_path, optarg, sizeof(socket_path));
            break;
        case 'm':
            is_master = atoi(optarg);
            break;
        case 'd':
            interface_id = atoi(optarg);
            break;
        case 'b':
            strlcpy(input_file, optarg, sizeof(input_file));
            break;
        case 'x':
            strlcpy(pix_fmt_string, optarg, sizeof(pix_fmt_string));
            if (strncmp(pix_fmt_string, "yuv422p", sizeof(pix_fmt_string)) == 0){
                pix_fmt = PIX_FMT_YUV422P;
            } else if (strncmp(pix_fmt_string, "yuv422p10le", sizeof(pix_fmt_string)) == 0) {
                pix_fmt = PIX_FMT_YUV422P_10BIT_LE;
            } else if (strncmp(pix_fmt_string, "yuv444p10le", sizeof(pix_fmt_string)) == 0){
                pix_fmt = PIX_FMT_YUV444P_10BIT_LE;
            } else if (strncmp(pix_fmt_string, "rgb8", sizeof(pix_fmt_string)) == 0){
                pix_fmt = PIX_FMT_RGB8;
            } else {
                pix_fmt = PIX_FMT_NV12;
            }
            break;
        case 'a':
            strlcpy(audio_type, optarg, sizeof(audio_type));
            break;
        case 'j':
            strlcpy(audio_format, optarg, sizeof(audio_format));
            break;
        case 'g':
            strlcpy(audio_sampling, optarg, sizeof(audio_sampling));
            break;
        case 'e':
            strlcpy(audio_ptime, optarg, sizeof(audio_ptime));
            break;
        case 'c':
            audio_channels = atoi(optarg);
            break;
        case 'q':
            strlcpy(anc_type, optarg, sizeof(anc_type));
            break;
        case 'n':
            total_num = atoi(optarg);
            break;
        case 'l':
            loop = (atoi(optarg)>0);
            break;
        case '?':
            usage(stderr, argv[0], 1);
            return 1;
        default:
            break;
        }
    }

    if (help_flag) {
        usage(stdout, argv[0], 1);
        return 0;
    }

    /* is sender */
    param.type = is_tx;

    /* protocol type */
    if (strncmp(protocol_type, "memif", sizeof(protocol_type)) == 0) {
        param.protocol = PROTO_MEMIF;
        strlcpy(param.memif_interface.socket_path, socket_path, sizeof(param.memif_interface.socket_path));
        param.memif_interface.is_master = is_master;
        param.memif_interface.interface_id = interface_id;
    } else if (strncmp(protocol_type, "udp", sizeof(protocol_type)) == 0) {
        param.protocol = PROTO_UDP;
    } else if (strncmp(protocol_type, "tcp", sizeof(protocol_type)) == 0) {
        param.protocol = PROTO_TCP;
    } else if (strncmp(protocol_type, "http", sizeof(protocol_type)) == 0) {
        param.protocol = PROTO_HTTP;
    } else if (strncmp(protocol_type, "grpc", sizeof(protocol_type)) == 0) {
        param.protocol = PROTO_GRPC;
    } else {
        param.protocol = PROTO_AUTO;
    }

    /* payload type */
    if (strncmp(payload_type, "st20", sizeof(payload_type)) == 0) {
        param.payload_type = PAYLOAD_TYPE_ST20_VIDEO;
    } else if (strncmp(payload_type, "st22", sizeof(payload_type)) == 0) {
        param.payload_type = PAYLOAD_TYPE_ST22_VIDEO;
    } else if (strncmp(payload_type, "st30", sizeof(payload_type)) == 0) {
        param.payload_type = PAYLOAD_TYPE_ST30_AUDIO;
    } else if (strncmp(payload_type, "st40", sizeof(payload_type)) == 0) {
        param.payload_type = PAYLOAD_TYPE_ST40_ANCILLARY;
    } else if (strncmp(payload_type, "rtsp", sizeof(payload_type)) == 0) {
        param.payload_type = PAYLOAD_TYPE_RTSP_VIDEO;
    } else {
        param.payload_type = PAYLOAD_TYPE_NONE;
    }

    // TODO: Move whole switch-case to common
    switch (param.payload_type) {
    case PAYLOAD_TYPE_ST30_AUDIO:
        // mcm_audio_type
        if (strncmp(audio_type, "frame", sizeof(audio_type)) == 0) {
            param.payload_args.audio_args.type = AUDIO_TYPE_FRAME_LEVEL;
        } else if (strncmp(audio_type, "rtp", sizeof(audio_type)) == 0) {
            param.payload_args.audio_args.type = AUDIO_TYPE_RTP_LEVEL;
        }
        /* TODO: Only 1 to 8 channels are supported here now
                 Tested only with 1 and 2 channels*/
        if (audio_channels > 0 && audio_channels < 9){
            param.payload_args.audio_args.channel = audio_channels;
        }
        // mcm_audio_format
        if (strncmp(audio_format, "pcm8", sizeof(audio_format)) == 0) {
            param.payload_args.audio_args.format = AUDIO_FMT_PCM8;
        } else if (strncmp(audio_format, "pcm16", sizeof(audio_format)) == 0) {
            param.payload_args.audio_args.format = AUDIO_FMT_PCM16;
        } else if (strncmp(audio_format, "pcm24", sizeof(audio_format)) == 0) {
            param.payload_args.audio_args.format = AUDIO_FMT_PCM24;
        } else if (strncmp(audio_format, "am824", sizeof(audio_format)) == 0) {
            param.payload_args.audio_args.format = AUDIO_FMT_AM824;
        }
        // mcm_audio_sampling
        if (strncmp(audio_sampling, "48k", sizeof(audio_sampling)) == 0) {
            param.payload_args.audio_args.sampling = AUDIO_SAMPLING_48K;
        } else if (strncmp(audio_sampling, "96k", sizeof(audio_sampling)) == 0) {
            param.payload_args.audio_args.sampling = AUDIO_SAMPLING_96K;
        } else if (strncmp(audio_sampling, "44k", sizeof(audio_sampling)) == 0) {
            param.payload_args.audio_args.sampling = AUDIO_SAMPLING_44K;
        }
        // mcm_audio_ptime
        if (strncmp(audio_ptime, "1ms", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_1MS;
        } else if (strncmp(audio_ptime, "125us", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_125US;
        } else if (strncmp(audio_ptime, "250us", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_250US;
        } else if (strncmp(audio_ptime, "333us", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_333US;
        } else if (strncmp(audio_ptime, "4ms", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_4MS;
        } else if (strncmp(audio_ptime, "80us", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_80US;
        } else if (strncmp(audio_ptime, "1.09ms", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_1_09MS;
        } else if (strncmp(audio_ptime, "0.14ms", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_0_14MS;
        } else if (strncmp(audio_ptime, "0.09ms", sizeof(audio_ptime)) == 0) {
            param.payload_args.audio_args.ptime = AUDIO_PTIME_0_09MS;
        }
        frame_size = getAudioFrameSize(
                        param.payload_args.audio_args.format,
                        param.payload_args.audio_args.sampling,
                        param.payload_args.audio_args.ptime,
                        param.payload_args.audio_args.channel
        );
        break;
    case PAYLOAD_TYPE_ST40_ANCILLARY:
        // mcm_anc_format
        param.payload_args.anc_args.format = ANC_FORMAT_CLOSED_CAPTION; // the only possible value
        // mcm_anc_type
        if (strncmp(anc_type, "frame", sizeof(anc_type)) == 0) {
            param.payload_args.audio_args.type = ANC_TYPE_FRAME_LEVEL;
        } else if (strncmp(anc_type, "rtp", sizeof(anc_type)) == 0) {
            param.payload_args.audio_args.type = ANC_TYPE_RTP_LEVEL;
        }
        param.payload_args.anc_args.fps = vid_fps;
        break;
    case PAYLOAD_TYPE_ST22_VIDEO:
        if (strncmp(payload_codec, "jpegxs", sizeof(payload_codec)) == 0) {
            param.payload_codec = PAYLOAD_CODEC_JPEGXS;
        } else if (strncmp(payload_codec, "h264", sizeof(payload_codec)) == 0) {
            param.payload_codec = PAYLOAD_CODEC_H264;
        }
    case PAYLOAD_TYPE_RTSP_VIDEO:
    case PAYLOAD_TYPE_ST20_VIDEO:
    default:
        /* video format */
        param.payload_args.video_args.width   = param.width = width;
        param.payload_args.video_args.height  = param.height = height;
        param.payload_args.video_args.fps     = param.fps = vid_fps;
        param.payload_args.video_args.pix_fmt = param.pix_fmt = pix_fmt;
        frame_size = getFrameSize(pix_fmt, width, height, false);
        break;
    }

    strlcpy(param.remote_addr.ip, send_addr, sizeof(param.remote_addr.ip));
    strlcpy(param.remote_addr.port, send_port, sizeof(param.remote_addr.port));
    strlcpy(param.local_addr.ip, send_addr, sizeof(param.local_addr.ip));
    strlcpy(param.local_addr.port, send_port, sizeof(param.local_addr.port));
    printf("LOCAL: %s:%s\n", param.local_addr.ip, param.local_addr.port);
    printf("REMOTE: %s:%s\n", param.remote_addr.ip, param.remote_addr.port);

    dp_ctx = mcm_create_connection(&param);
    if (dp_ctx == NULL) {
        printf("Fail to connect to MCM data plane\n");
        exit(-1);
    }

    signal(SIGINT, intHandler);

    FILE* input_fp = NULL;
    uint32_t frame_count = 0;
    const uint32_t fps_interval = 30;
    double fps = 0.0;
    struct timespec ts_begin = {}, ts_end = {};
    struct timespec ts_frame_begin = {}, ts_frame_end = {};

    if (strlen(input_file) > 0) {
        struct stat statbuf = { 0 };
        if (stat(input_file, &statbuf) == -1) {
            perror(NULL);
            exit(-1);
        }

        input_fp = fopen(input_file, "rb");
        if (input_fp == NULL) {
            printf("Fail to open input file: %s\n", input_file);
            exit(-1);
        }
    }

    const __useconds_t pacing = 1000000.0 / vid_fps;
    while (keepRunning) {
        /* Timestamp for frame start. */
        clock_gettime(CLOCK_REALTIME, &ts_frame_begin);

        buf = mcm_dequeue_buffer(dp_ctx, -1, NULL);
        if (buf == NULL) {
            break;
        }
        printf("INFO: frame_size = %u\n", frame_size);

        if (input_fp == NULL) {
            gen_test_data(buf, frame_count);
        } else {
            if (read_test_data(input_fp, buf, frame_size) < 0) {
                if (input_fp != NULL) {
                    fclose(input_fp);
                    input_fp = NULL;
                }
                if (loop) {
                    input_fp = fopen(input_file, "rb");
                    if (input_fp == NULL) {
                        printf("Fail to open input file for infinity loop: %s\n", input_file);
                        break;
                    }
                    if (read_test_data(input_fp, buf, frame_size) < 0) {
                        break;
                    }
                } else {
                    break;
                }
            }
        }

        if (mcm_enqueue_buffer(dp_ctx, buf) != 0) {
            break;
        }

        if (frame_count % fps_interval == 0) {
            /* calculate FPS */
            clock_gettime(CLOCK_REALTIME, &ts_end);

            fps = 1e9 * (ts_end.tv_sec - ts_begin.tv_sec);
            fps += (ts_end.tv_nsec - ts_begin.tv_nsec);
            fps /= 1e9;
            fps = (double)fps_interval / fps;

            clock_gettime(CLOCK_REALTIME, &ts_begin);
        }

        printf("TX frames: [%d], FPS: %0.2f [%0.2f]\n", frame_count, fps, vid_fps);

        frame_count++;

        if (param.payload_type != PAYLOAD_TYPE_ST30_AUDIO
            && total_num > 0 && frame_count >= total_num) {
            break;
        }

        /* Timestamp for frame end. */
        clock_gettime(CLOCK_REALTIME, &ts_frame_end);

        /* sleep for 1/fps */
        __useconds_t spend = 1000000 * (ts_frame_end.tv_sec - ts_frame_begin.tv_sec) + (ts_frame_end.tv_nsec - ts_frame_begin.tv_nsec)/1000;
        printf("pacing: %d\n", pacing);
        printf("spend: %d\n", spend);
    }

    sleep(2);

    /* Clean up */
    mcm_destroy_connection(dp_ctx);

    if (input_fp != NULL) {
        fclose(input_fp);
    }

    return 0;
}
