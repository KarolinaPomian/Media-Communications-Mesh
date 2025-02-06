# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024-2025 Intel Corporation
# Media Communications Mesh

import logging
import os
from queue import Queue
from typing import Dict

import pytest

import Engine.execute

from .stash import clear_result_media, remove_result_media

phase_report_key = pytest.StashKey[Dict[str, pytest.CollectReport]]()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    rep = yield

    # store test results for each phase of a call, which can
    # be "setup", "call", "teardown"
    item.stash.setdefault(phase_report_key, {})[rep.when] = rep

    return rep


@pytest.fixture(scope="session")
def media(request):
    media = request.config.getoption("--media")
    if media is None:
        media = "/mnt/media"
    os.environ["media"] = media
    return media


@pytest.fixture(scope="session")
def build(request):
    build = request.config.getoption("--build")
    if build is None:
        build = "../.."
    os.environ["build"] = build
    return build


@pytest.fixture(scope="session", autouse=True)
def keep(request):
    keep = request.config.getoption("--keep")
    if keep is None:
        keep = "none"
    if keep.lower() not in ["all", "failed", "none"]:
        raise RuntimeError(f"Wrong option --keep={keep}")
    os.environ["keep"] = keep.lower()
    return keep.lower()


@pytest.fixture(scope="session", autouse=True)
def dmesg(request):
    dmesg = request.config.getoption("--dmesg")
    if dmesg is None:
        dmesg = "keep"
    if dmesg.lower() not in ["clear", "keep"]:
        raise RuntimeError(f"Wrong option --dmesg={dmesg}")
    os.environ["dmesg"] = dmesg.lower()
    return dmesg.lower()


@pytest.fixture(scope="function", autouse=True)
def fixture_remove_result_media(request):
    clear_result_media()
    yield

    if os.environ["keep"] == "all":
        return
    if os.environ["keep"] == "failed":
        report = request.node.stash[phase_report_key]
        if "call" in report and report["call"].failed:
            return
    remove_result_media()


@pytest.fixture(scope="session")
def dma_port_list(request):
    dma = request.config.getoption("--dma")
    assert dma is not None, "--dma parameter not provided"
    return dma.split(",")


@pytest.fixture(scope="session")
def nic_port_list(request):
    nic = request.config.getoption("--nic")
    assert nic is not None, "--nic parameter not provided"
    return nic.split(",")


@pytest.fixture(scope="session")
def test_time(request):
    test_time = request.config.getoption("--time")
    if test_time is None:
        return 30
    return int(test_time)


@pytest.fixture(scope="session", autouse=True)
def mtl_path(request):
    mtl_path = request.config.getoption("--mtl_path")
    if mtl_path is None:
        mtl_path = "../../../Media-Transport-Library"
    os.environ["mtl_path"] = mtl_path
    return mtl_path


@pytest.fixture(scope="session")
def mesh_agent():
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

    yield process

    logging.debug("Stopping mesh-agent.")
    Engine.execute.killproc(process)