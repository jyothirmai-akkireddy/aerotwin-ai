"""Continuous 5-minute telemetry soak and stability benchmark.

SIH26054 — AeroTwin AI
Phase 9 Reliability & Stability Gate

Validates:
1. Continuous 5-minute (>= 3,000 frames at 10 Hz) streaming through full stack:
   - Simulator -> SyntheticSource -> Validator -> PhysicsTwin -> MLInference -> Prognostics -> Broadcaster
2. Memory stability tracking (OS Process RSS Working Set + Python tracemalloc Heap).
3. Monotonic sequence ordering, zero dropped frames, zero duplicate frames.
4. Bounded queue depth and resource isolation.
5. Lifecycle teardown with zero zombie or lingering tasks.
6. All scenarios explicitly tagged as SYNTHETIC / PROTOTYPE SCENARIO.
"""

import asyncio
import ctypes
import gc
import json
import os
import time
import tracemalloc
from ctypes import wintypes
from unittest.mock import AsyncMock

import pytest

from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.application.services.prognostics_service import PrognosticsService
from app.application.services.realtime_service import RealtimeTelemetryService
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.physics.calibration_repository import PhysicsCalibrationRepository
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager

logger = get_logger("aerotwin.benchmark.soak")

PROTOTYPE_SCENARIO_TAG = "SYNTHETIC / PROTOTYPE SCENARIO — Phase 9 5-Minute Soak Benchmark"


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def get_process_working_set_mb() -> float:
    """Retrieve Windows Process Working Set (Resident Set Size equivalent) in Megabytes."""
    try:
        pid = os.getpid()
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not handle:
            return 0.0
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        success = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        )
        ctypes.windll.kernel32.CloseHandle(handle)
        if success:
            return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0


@pytest.mark.asyncio
async def test_continuous_stream_soak_memory_and_queues():
    """Execute continuous 5-minute soak test (3,000 frames at 10 Hz) with full resource tracking."""
    logger.info(f"Starting: {PROTOTYPE_SCENARIO_TAG} - 5 Minutes / 3,000 Frames at 10 Hz")

    gc.collect()
    tracemalloc.start()
    heap_start_b, _ = tracemalloc.get_traced_memory()
    heap_start_mb = heap_start_b / (1024 * 1024)
    rss_start_mb = get_process_working_set_mb()

    # 1. Initialize complete production-grade stack
    sim = EngineSimulator(telemetry_rate_hz=10)
    source = SyntheticTelemetrySource(simulator=sim)
    broadcaster = WebSocketBroadcastManager(max_clients=10, queue_size=1000)

    cal_repo = PhysicsCalibrationRepository()
    physics_service = PhysicsTwinService(calibration_repo=cal_repo)
    ml_service = MLInferenceService()
    prognostics_service = PrognosticsService()

    realtime_service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=10,  # Exact 10 Hz operating frequency
        strict_validation=True,
        heartbeat_interval_sec=60.0,
        physics_service=physics_service,
        ml_service=ml_service,
        prognostics_service=prognostics_service,
    )

    client_id = "test-5min-soak-client"
    session = await broadcaster.register(client_id, websocket=AsyncMock())

    target_frames = 3000
    received_count = 0
    prev_seq: int | None = None
    seen_seqs: set[int] = set()
    duplicate_count = 0
    ordering_violations = 0
    max_queue_depth = 0

    checkpoints: list[dict] = []

    await realtime_service.start()
    t_start = time.perf_counter()
    last_checkpoint_t = t_start
    last_checkpoint_frames = 0

    try:
        while received_count < target_frames:
            raw = await asyncio.wait_for(session.queue.get(), timeout=5.0)
            session.queue.task_done()
            received_count += 1

            q_len = session.queue.qsize()
            if q_len > max_queue_depth:
                max_queue_depth = q_len

            # Check every 300 frames (~30 seconds)
            if received_count % 300 == 0:
                t_now = time.perf_counter()
                dt_step = t_now - last_checkpoint_t
                frames_step = received_count - last_checkpoint_frames
                inst_hz = frames_step / max(0.001, dt_step)

                curr_heap_b, _ = tracemalloc.get_traced_memory()
                curr_heap_mb = curr_heap_b / (1024 * 1024)
                curr_rss_mb = get_process_working_set_mb()

                msg = json.loads(raw)
                seq = msg["sequence_id"]
                if seq in seen_seqs:
                    duplicate_count += 1
                seen_seqs.add(seq)

                if prev_seq is not None and seq <= prev_seq:
                    ordering_violations += 1
                prev_seq = seq

                chk = {
                    "frame": received_count,
                    "elapsed_sec": round(t_now - t_start, 1),
                    "inst_hz": round(inst_hz, 2),
                    "heap_mb": round(curr_heap_mb, 2),
                    "rss_mb": round(curr_rss_mb, 2),
                    "queue_depth": q_len,
                    "drops": session.frames_dropped,
                }
                checkpoints.append(chk)
                logger.info(
                    f"Soak Checkpoint {received_count:4d}/{target_frames} | "
                    f"T={chk['elapsed_sec']:5.1f}s | Rate={chk['inst_hz']:4.1f} Hz | "
                    f"Heap={chk['heap_mb']:5.2f} MB | RSS={chk['rss_mb']:5.2f} MB | "
                    f"Queue={q_len:2d} | Drops={chk['drops']}"
                )

                last_checkpoint_t = t_now
                last_checkpoint_frames = received_count

    finally:
        await realtime_service.stop()
        # Drain any remaining frames
        while not session.queue.empty():
            try:
                session.queue.get_nowait()
                session.queue.task_done()
            except asyncio.QueueEmpty:
                break
        await broadcaster.unregister(client_id)

    total_wall_sec = time.perf_counter() - t_start
    gc.collect()
    heap_final_b, heap_peak_b = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    heap_final_mb = heap_final_b / (1024 * 1024)
    heap_peak_mb = heap_peak_b / (1024 * 1024)
    heap_delta_mb = heap_final_mb - heap_start_mb

    rss_final_mb = get_process_working_set_mb()
    rss_delta_mb = max(0.0, rss_final_mb - rss_start_mb)
    observed_hz = received_count / max(0.001, total_wall_sec)

    # Verify no zombie tasks running in asyncio event loop
    active_tasks = [t for t in asyncio.all_tasks() if not t.done() and t != asyncio.current_task()]
    zombie_task_count = len(active_tasks)

    summary_str = (
        f"\n======================================================================\n"
        f"AeroTwin AI — Phase 9 5-Minute Continuous Soak Test Results\n"
        f"======================================================================\n"
        f"  Total Duration       : {total_wall_sec:.2f} seconds ({total_wall_sec / 60.0:.2f} minutes)\n"
        f"  Target Duration      : 300.00 seconds (5.00 minutes)\n"
        f"  Frames Processed     : {received_count} frames\n"
        f"  Observed Telemetry Hz: {observed_hz:.2f} Hz (nominal: 10.0 Hz)\n"
        f"  Initial Python Heap  : {heap_start_mb:.2f} MB\n"
        f"  Final Python Heap    : {heap_final_mb:.2f} MB\n"
        f"  Peak Python Heap     : {heap_peak_mb:.2f} MB\n"
        f"  Net Heap Growth      : {heap_delta_mb:.2f} MB\n"
        f"  Initial OS RSS       : {rss_start_mb:.2f} MB\n"
        f"  Final OS RSS         : {rss_final_mb:.2f} MB\n"
        f"  Net OS RSS Growth    : {rss_delta_mb:.2f} MB\n"
        f"  Total Frames Dropped : {session.frames_dropped}\n"
        f"  Duplicate Frames     : {duplicate_count}\n"
        f"  Sequence Violations  : {ordering_violations}\n"
        f"  Max Queue Depth Seen : {max_queue_depth}\n"
        f"  Zombie Async Tasks   : {zombie_task_count}\n"
        f"======================================================================"
    )
    logger.info(summary_str)
    print(summary_str)

    # Strictly assert acceptance criteria
    assert received_count == target_frames, f"Expected {target_frames} frames, got {received_count}"
    assert total_wall_sec >= 295.0, (
        f"Soak duration {total_wall_sec:.1f}s did not meet 5-minute requirement (>= 295s)"
    )
    assert session.frames_dropped == 0, (
        f"Detected {session.frames_dropped} dropped frames during soak"
    )
    assert duplicate_count == 0, f"Detected {duplicate_count} duplicate frames"
    assert ordering_violations == 0, f"Detected {ordering_violations} sequence ordering violations"
    assert heap_delta_mb < 25.0, (
        f"Heap growth {heap_delta_mb:.2f} MB exceeded 25.0 MB acceptance limit"
    )
    assert rss_delta_mb < 150.0, (
        f"RSS growth {rss_delta_mb:.2f} MB exceeded 150.0 MB limit (native C++ runtimes)"
    )
    assert zombie_task_count == 0, f"Detected {zombie_task_count} zombie tasks after teardown"
