"""Replay telemetry source implementing ITelemetrySource port.

Drives historical flight frames through the application telemetry bus, respecting
authoritative ReplayCursor state, execution modes, and pacing.
"""

import asyncio
from collections.abc import AsyncIterator

from app.application.ports.telemetry_ports import ITelemetrySource
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.replay.cursor import ReplayCursor
from app.domain.replay.enums import PlaybackState, ReplayExecutionMode
from app.domain.replay.models import ReplayCursorStatus


class ReplayTelemetrySource(ITelemetrySource):
    """Adapter bridging historical flight logs to the application telemetry pipeline."""

    def __init__(
        self,
        frames: list[TelemetryFrame],
        source_filename: str | None = None,
        is_looping: bool = False,
    ):
        self._frames = frames
        timestamps = [f.timestamp for f in frames]
        self._cursor = ReplayCursor(
            timestamps=timestamps,
            source_filename=source_filename,
            is_looping=is_looping,
        )
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def cursor(self) -> ReplayCursor:
        return self._cursor

    @property
    def total_frames(self) -> int:
        return len(self._frames)

    def get_status(self) -> ReplayCursorStatus:
        """Return snapshot DTO of replay cursor state."""
        return self._cursor.get_status()

    def play(self) -> None:
        self._cursor.play()

    def pause(self) -> None:
        self._cursor.pause()

    def resume(self) -> None:
        self._cursor.resume()

    def reset(self) -> None:
        self._cursor.reset()

    def seek_index(self, index: int) -> int:
        return self._cursor.seek_index(index)

    def seek_timestamp(self, timestamp: float) -> int:
        return self._cursor.seek_timestamp(timestamp)

    def set_speed(self, multiplier: float, mode: ReplayExecutionMode | None = None) -> None:
        self._cursor.set_speed(multiplier, mode=mode)

    async def connect(self) -> None:
        self._is_connected = True

    async def disconnect(self) -> None:
        self._is_connected = False

    async def get_next_frame(self) -> TelemetryFrame:
        """Produce the next sequential telemetry frame according to cursor position."""
        if not self._frames:
            raise RuntimeError("Replay source has no loaded frames")

        idx = self._cursor.current_index
        frame = self._frames[idx]

        # Advance cursor for subsequent calls if playing
        if self._cursor.playback_state == PlaybackState.PLAYING:
            self._cursor.advance()

        return frame

    async def stream_frames(
        self,
        max_frames: int | None = None,
        realtime: bool = True,
    ) -> AsyncIterator[TelemetryFrame]:
        """Asynchronously stream replayed frames governed by cursor pacing."""
        if not self._is_connected:
            await self.connect()

        frames_emitted = 0
        self._cursor.play()

        while self._is_connected and self._cursor.playback_state != PlaybackState.COMPLETED:
            if max_frames is not None and frames_emitted >= max_frames:
                break

            if self._cursor.playback_state == PlaybackState.PAUSED:
                await asyncio.sleep(0.05)
                continue

            idx = self._cursor.current_index
            frame = self._frames[idx]
            frames_emitted += 1
            yield frame

            next_idx = self._cursor.advance()
            if next_idx is None:
                # Reached end-of-file without looping
                break

            # Calculate pacing delay
            if realtime and self._cursor.execution_mode != ReplayExecutionMode.OFFLINE_BATCH:
                # Inter-frame delta in data time
                t_curr = self._frames[idx].timestamp
                t_next = self._frames[next_idx].timestamp
                dt_data = max(0.001, t_next - t_curr)

                # Wall-clock sleep delay scaled by speed multiplier
                speed = max(0.1, self._cursor.playback_speed)
                dt_wall = dt_data / speed
                await asyncio.sleep(dt_wall)
