"""Pure domain finite state machine governing flight replay timeline cursor.

Adheres strictly to Clean Architecture: zero framework, I/O, or asyncio dependencies.
"""

import bisect

from app.domain.replay.enums import PlaybackState, ReplayExecutionMode
from app.domain.replay.models import ReplayCursorStatus

APPROVED_REALTIME_SPEED: float = 1.0
APPROVED_ACCELERATED_SPEEDS: set[float] = {0.5, 1.0, 2.0, 5.0, 10.0}


class ReplayCursor:
    """Authoritative state machine managing replay index, state transitions, and time mapping."""

    def __init__(
        self,
        timestamps: list[float],
        source_filename: str | None = None,
        is_looping: bool = False,
    ):
        self._timestamps = timestamps
        self._total_frames = len(timestamps)
        self.source_filename = source_filename
        self.is_looping = is_looping

        self.current_index = 0
        self.playback_state = PlaybackState.IDLE
        self.execution_mode = ReplayExecutionMode.REALTIME
        self.playback_speed = 1.0

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def is_empty(self) -> bool:
        return self._total_frames == 0

    @property
    def start_timestamp(self) -> float:
        return self._timestamps[0] if self._timestamps else 0.0

    @property
    def end_timestamp(self) -> float:
        return self._timestamps[-1] if self._timestamps else 0.0

    @property
    def current_timestamp(self) -> float:
        if 0 <= self.current_index < self._total_frames:
            return self._timestamps[self.current_index]
        return self.start_timestamp

    @property
    def total_sim_time_sec(self) -> float:
        if self._total_frames <= 1:
            return 0.0
        return max(0.0, self.end_timestamp - self.start_timestamp)

    @property
    def elapsed_sim_time_sec(self) -> float:
        if self.is_empty:
            return 0.0
        return max(0.0, self.current_timestamp - self.start_timestamp)

    @property
    def progress_pct(self) -> float:
        if self._total_frames <= 1:
            return 100.0 if self.playback_state == PlaybackState.COMPLETED else 0.0
        return round(
            min(100.0, max(0.0, (self.current_index / (self._total_frames - 1)) * 100.0)), 2
        )

    def play(self) -> None:
        """Initiate or resume playback."""
        if self.is_empty:
            return
        if self.playback_state == PlaybackState.COMPLETED:
            self.current_index = 0
        self.playback_state = PlaybackState.PLAYING

    def pause(self) -> None:
        """Pause playback at current frame index."""
        if self.playback_state == PlaybackState.PLAYING:
            self.playback_state = PlaybackState.PAUSED

    def resume(self) -> None:
        """Resume playback if currently paused."""
        if self.playback_state == PlaybackState.PAUSED:
            self.playback_state = PlaybackState.PLAYING

    def stop(self) -> None:
        """Halt playback and reset cursor to beginning."""
        self.playback_state = PlaybackState.STOPPED
        self.current_index = 0

    def reset(self) -> None:
        """Reset cursor position to beginning without losing loaded status."""
        self.current_index = 0
        if self.playback_state == PlaybackState.COMPLETED:
            self.playback_state = PlaybackState.IDLE

    def seek_index(self, target_index: int) -> int:
        """Seek directly to a 0-indexed frame with strict boundary clamping.

        Boundary handling:
            target < 0 clamps to 0.
            target >= total_frames clamps to total_frames - 1.
        """
        if self.is_empty:
            self.current_index = 0
            return 0

        clamped = max(0, min(self._total_frames - 1, target_index))
        self.current_index = clamped

        if self.playback_state == PlaybackState.COMPLETED and clamped < self._total_frames - 1:
            self.playback_state = PlaybackState.PAUSED

        return self.current_index

    def seek_timestamp(self, target_timestamp: float) -> int:
        """Seek to timestamp selecting the last frame where frame.timestamp <= target_timestamp.

        If target is before start_timestamp, clamps to 0.
        Uses binary search for O(log N) performance.
        """
        if self.is_empty:
            return 0

        # bisect_right returns index where target would be inserted after all elements <= target
        idx = bisect.bisect_right(self._timestamps, target_timestamp) - 1
        return self.seek_index(idx)

    def advance(self) -> int | None:
        """Advance cursor to the next sequential frame.

        Returns:
            The new current_index if advanced, or None if reached end of file without looping.
        """
        if self.is_empty:
            return None

        if self.current_index < self._total_frames - 1:
            self.current_index += 1
            return self.current_index

        # Cursor is at the final frame
        if self.is_looping:
            self.current_index = 0
            return 0

        self.playback_state = PlaybackState.COMPLETED
        return None

    def set_speed(
        self,
        multiplier: float,
        mode: ReplayExecutionMode | None = None,
    ) -> None:
        """Configure playback rate and execution pacing mode according to approved contract.

        Approved contract:
            REALTIME: exactly 1.0x
            ACCELERATED: exactly 0.5x, 1.0x, 2.0x, 5.0x, 10.0x
            OFFLINE_BATCH: unpaced execution (speed = 0.0)

        Args:
            multiplier: Speed factor.
            mode: Explicit execution mode (REALTIME, ACCELERATED, OFFLINE_BATCH).
        """
        if mode == ReplayExecutionMode.OFFLINE_BATCH:
            self.execution_mode = ReplayExecutionMode.OFFLINE_BATCH
            self.playback_speed = 0.0
            return

        if mode == ReplayExecutionMode.REALTIME:
            if abs(multiplier - APPROVED_REALTIME_SPEED) > 1e-6:
                raise ValueError(
                    f"REALTIME execution mode accepts exactly 1.0x speed, got {multiplier}x."
                )
            self.execution_mode = ReplayExecutionMode.REALTIME
            self.playback_speed = APPROVED_REALTIME_SPEED
            return

        if mode == ReplayExecutionMode.ACCELERATED:
            matched = next(
                (s for s in APPROVED_ACCELERATED_SPEEDS if abs(multiplier - s) < 1e-6), None
            )
            if matched is None:
                raise ValueError(
                    f"ACCELERATED execution mode accepts only speeds in "
                    f"{sorted(APPROVED_ACCELERATED_SPEEDS)}, got {multiplier}x. "
                    f"(0.25x and other arbitrary speeds are rejected)."
                )
            self.execution_mode = ReplayExecutionMode.ACCELERATED
            self.playback_speed = matched
            return

        # mode is None -> infer mode from multiplier
        if abs(multiplier) < 1e-6:
            self.execution_mode = ReplayExecutionMode.OFFLINE_BATCH
            self.playback_speed = 0.0
            return

        if abs(multiplier - APPROVED_REALTIME_SPEED) < 1e-6:
            self.execution_mode = ReplayExecutionMode.REALTIME
            self.playback_speed = APPROVED_REALTIME_SPEED
            return

        matched = next((s for s in APPROVED_ACCELERATED_SPEEDS if abs(multiplier - s) < 1e-6), None)
        if matched is not None:
            self.execution_mode = ReplayExecutionMode.ACCELERATED
            self.playback_speed = matched
            return

        raise ValueError(
            f"Playback speed {multiplier}x is not permitted. "
            f"Approved contract: REALTIME (1.0x), "
            f"ACCELERATED ({sorted(APPROVED_ACCELERATED_SPEEDS)}), or OFFLINE_BATCH (unpaced)."
        )

    def set_execution_mode(
        self,
        mode: ReplayExecutionMode,
        speed: float | None = None,
    ) -> None:
        """Set explicit execution mode adhering to the approved contract."""
        if mode == ReplayExecutionMode.REALTIME:
            self.set_speed(1.0, mode=ReplayExecutionMode.REALTIME)
        elif mode == ReplayExecutionMode.OFFLINE_BATCH:
            self.set_speed(0.0, mode=ReplayExecutionMode.OFFLINE_BATCH)
        elif mode == ReplayExecutionMode.ACCELERATED:
            target_speed = (
                speed
                if speed is not None
                else (
                    self.playback_speed
                    if self.playback_speed in APPROVED_ACCELERATED_SPEEDS
                    else 2.0
                )
            )
            self.set_speed(target_speed, mode=ReplayExecutionMode.ACCELERATED)

    def get_status(self) -> ReplayCursorStatus:
        """Generate an immutable snapshot DTO of the current cursor state."""
        return ReplayCursorStatus(
            playback_state=self.playback_state,
            execution_mode=self.execution_mode,
            current_index=self.current_index,
            total_frames=self._total_frames,
            data_timestamp=self.current_timestamp,
            start_timestamp=self.start_timestamp,
            end_timestamp=self.end_timestamp,
            elapsed_sim_time_sec=self.elapsed_sim_time_sec,
            total_sim_time_sec=self.total_sim_time_sec,
            progress_pct=self.progress_pct,
            playback_speed=self.playback_speed,
            source_filename=self.source_filename,
            is_looping=self.is_looping,
        )
