"""Domain enumerations for flight log replay and playback state machines."""

from enum import Enum


class PlaybackState(str, Enum):
    """Authoritative state machine states for the replay cursor."""

    IDLE = "IDLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"


class ReplayExecutionMode(str, Enum):
    """Explicit playback execution pacing modes."""

    REALTIME = "REALTIME"  # 1.0x wall-clock pacing
    ACCELERATED = "ACCELERATED"  # Paced at scaled multiplier (0.5x, 2x, 5x, 10x)
    OFFLINE_BATCH = "OFFLINE_BATCH"  # Unpaced maximum throughput processing


class ReplayFormat(str, Enum):
    """Supported storage formats for historical flight log replay."""

    PARQUET = "PARQUET"
    SQLITE = "SQLITE"
    CSV = "CSV"
