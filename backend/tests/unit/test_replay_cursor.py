"""Unit tests for ReplayCursor state machine and seek/EOF semantics."""

from app.domain.replay.cursor import ReplayCursor
from app.domain.replay.enums import PlaybackState, ReplayExecutionMode


def test_cursor_state_machine_transitions():
    timestamps = [100.0, 101.0, 102.0, 103.0, 104.0]
    cursor = ReplayCursor(timestamps=timestamps)

    assert cursor.playback_state == PlaybackState.IDLE
    assert cursor.current_index == 0

    cursor.play()
    assert cursor.playback_state == PlaybackState.PLAYING

    cursor.pause()
    assert cursor.playback_state == PlaybackState.PAUSED

    cursor.resume()
    assert cursor.playback_state == PlaybackState.PLAYING

    cursor.reset()
    assert cursor.current_index == 0


def test_cursor_eof_semantics():
    timestamps = [10.0, 11.0, 12.0]
    cursor = ReplayCursor(timestamps=timestamps, is_looping=False)
    cursor.play()

    assert cursor.current_index == 0
    idx1 = cursor.advance()
    assert idx1 == 1
    assert cursor.current_index == 1

    idx2 = cursor.advance()
    assert idx2 == 2
    assert cursor.current_index == 2

    # Advance past final frame -> must return None and become COMPLETED
    idx3 = cursor.advance()
    assert idx3 is None
    assert cursor.playback_state == PlaybackState.COMPLETED
    assert cursor.current_index == 2  # Cursor remains at final valid frame

    # Repeated advance at EOF does NOT generate invalid frame or advance beyond N-1
    idx4 = cursor.advance()
    assert idx4 is None
    assert cursor.playback_state == PlaybackState.COMPLETED


def test_cursor_looping_semantics():
    timestamps = [10.0, 11.0]
    cursor = ReplayCursor(timestamps=timestamps, is_looping=True)
    cursor.play()

    assert cursor.current_index == 0
    assert cursor.advance() == 1
    assert cursor.advance() == 0  # Wraps around to 0
    assert cursor.playback_state == PlaybackState.PLAYING


def test_cursor_seek_index_boundary_clamping():
    timestamps = [10.0, 20.0, 30.0, 40.0, 50.0]
    cursor = ReplayCursor(timestamps=timestamps)

    # Clamping below 0
    assert cursor.seek_index(-10) == 0
    assert cursor.current_index == 0

    # Clamping above N-1
    assert cursor.seek_index(999) == 4
    assert cursor.current_index == 4

    # Direct seek
    assert cursor.seek_index(2) == 2
    assert cursor.current_index == 2


def test_cursor_seek_timestamp_binary_search():
    # Timestamps at 10.0, 10.5, 11.0, 11.5, 12.0
    timestamps = [10.0, 10.5, 11.0, 11.5, 12.0]
    cursor = ReplayCursor(timestamps=timestamps)

    # Exact match: 11.0 -> index 2
    assert cursor.seek_timestamp(11.0) == 2

    # Between frames: 11.3 -> selects last frame where frame.timestamp <= 11.3 (index 2: 11.0)
    assert cursor.seek_timestamp(11.3) == 2

    # At 11.5 -> index 3
    assert cursor.seek_timestamp(11.5) == 3

    # Before start: 5.0 -> clamps to index 0
    assert cursor.seek_timestamp(5.0) == 0

    # Past end: 20.0 -> clamps to index 4
    assert cursor.seek_timestamp(20.0) == 4


def test_cursor_speed_modes():
    cursor = ReplayCursor(timestamps=[1.0, 2.0])

    # 1x real-time
    cursor.set_speed(1.0)
    assert cursor.execution_mode == ReplayExecutionMode.REALTIME
    assert cursor.playback_speed == 1.0

    # Accelerated
    cursor.set_speed(5.0)
    assert cursor.execution_mode == ReplayExecutionMode.ACCELERATED
    assert cursor.playback_speed == 5.0

    # Offline/Batch (speed = 0 or explicit OFFLINE_BATCH mode)
    cursor.set_speed(0.0)
    assert cursor.execution_mode == ReplayExecutionMode.OFFLINE_BATCH
    assert cursor.playback_speed == 0.0

    cursor.set_speed(10.0, mode=ReplayExecutionMode.OFFLINE_BATCH)
    assert cursor.execution_mode == ReplayExecutionMode.OFFLINE_BATCH
    assert cursor.playback_speed == 0.0
