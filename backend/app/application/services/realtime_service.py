"""Realtime telemetry application service.

Coordinates the asynchronous publication loop, rate pacing, frame validation,
and client broadcast without coupling the domain simulator to network transports.
"""

import asyncio
import time
from typing import Any

from app.application.ports.telemetry_ports import ITelemetrySource
from app.domain.telemetry.validation import TelemetryValidator
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager
from app.infrastructure.websocket.protocol import (
    HeartbeatMessage,
    StatusMessage,
    TelemetryMessage,
)

logger = get_logger("aerotwin.service.realtime")


class RealtimeTelemetryService:
    """Application service executing a rate-controlled asynchronous publication loop.

    Pulls frames from ITelemetrySource, passes them through TelemetryValidator,
    and forwards them to WebSocketBroadcastManager.
    """

    def __init__(
        self,
        telemetry_source: ITelemetrySource,
        broadcaster: WebSocketBroadcastManager,
        rate_hz: int = 10,
        strict_validation: bool = False,
        heartbeat_interval_sec: float = 5.0,
        physics_service: Any = None,
        ml_service: Any = None,
        prognostics_service: Any = None,
        replay_service: Any = None,
    ):
        self.telemetry_source = telemetry_source
        self.broadcaster = broadcaster
        self.rate_hz = rate_hz
        self.strict_validation = strict_validation
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self.physics_service = physics_service
        self.ml_service = ml_service
        self.prognostics_service = prognostics_service
        self.replay_service = replay_service

        self._source_mode: str = "LIVE"  # "LIVE" | "REPLAY"
        self._live_telemetry_source = telemetry_source
        self._source_lock = asyncio.Lock()
        self._current_mission_context: Any = None

        self._state: str = "stopped"  # "running" | "paused" | "stopped"
        self._loop_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._validator = TelemetryValidator()

    @property
    def source_mode(self) -> str:
        """Return active telemetry source mode ('LIVE' | 'REPLAY')."""
        return self._source_mode

    def set_mission_context(self, context: Any) -> None:
        """Attach active flight mission context to outbound telemetry broadcasts."""
        self._current_mission_context = context

    @property
    def state(self) -> str:
        """Return the current streaming state ('running', 'paused', 'stopped')."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Return whether the realtime stream is currently publishing."""
        return self._state == "running"

    async def start(self) -> None:
        """Start the realtime publication loop and periodic heartbeat task."""
        if self._state == "running":
            return

        self._shutdown_event.clear()
        self._state = "running"
        await self.telemetry_source.connect()

        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(
                self._realtime_loop(), name="realtime-stream-loop"
            )
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(), name="realtime-heartbeat-loop"
            )

        logger.info(f"Realtime telemetry publication service started at {self.rate_hz} Hz")
        await self.broadcaster.broadcast_status(
            StatusMessage(
                status="running", message=f"Telemetry streaming active at {self.rate_hz} Hz"
            )
        )

    async def pause(self) -> None:
        """Pause frame publication while keeping connections and simulator state intact."""
        self._state = "paused"
        logger.info("Realtime telemetry publication paused")
        await self.broadcaster.broadcast_status(
            StatusMessage(status="paused", message="Telemetry streaming paused")
        )

    async def resume(self) -> None:
        """Resume frame publication."""
        if self._state == "paused":
            self._state = "running"
            logger.info("Realtime telemetry publication resumed")
            await self.broadcaster.broadcast_status(
                StatusMessage(status="running", message="Telemetry streaming resumed")
            )

    async def reset(self) -> None:
        """Reset the underlying simulator if supported."""
        if hasattr(self.telemetry_source, "simulator") and hasattr(
            self.telemetry_source.simulator, "reset"
        ):
            self.telemetry_source.simulator.reset()
        if self.physics_service is not None and hasattr(self.physics_service, "reset"):
            self.physics_service.reset()
        if self.prognostics_service is not None and hasattr(self.prognostics_service, "reset"):
            self.prognostics_service.reset()
        if hasattr(self, "_validator") and hasattr(self._validator, "reset"):
            self._validator.reset()
        logger.info("Engine simulator state reset")
        await self.broadcaster.broadcast_status(
            StatusMessage(status="running", message="Simulator state reset to initial conditions")
        )

    async def set_scenario(self, scenario_name: str) -> None:
        """Change the active flight scenario profile driving the simulator."""
        from app.domain.simulation.scenarios import get_scenario

        profile = get_scenario(scenario_name)
        if profile and profile.phases:
            initial_phase = profile.phases[0]
            if hasattr(self.telemetry_source, "set_scenario"):
                self.telemetry_source.set_scenario(profile)
            elif hasattr(self.telemetry_source, "set_phase"):
                self.telemetry_source.set_phase(initial_phase)

            canonical_name = profile.scenario_name
            logger.info(f"Flight scenario changed to {canonical_name}")
            await self.broadcaster.broadcast_status(
                StatusMessage(status="running", message=f"Scenario switched to {canonical_name}")
            )
        else:
            logger.warning(f"Unknown scenario profile requested: {scenario_name}")

    async def set_rate(self, new_rate_hz: int) -> None:
        """Dynamically adjust publication frequency (1 - 100 Hz)."""
        if 1 <= new_rate_hz <= 100:
            self.rate_hz = new_rate_hz
            logger.info(f"Telemetry publication rate updated to {self.rate_hz} Hz")
            await self.broadcaster.broadcast_status(
                StatusMessage(
                    status="running",
                    message=f"Telemetry streaming rate updated to {self.rate_hz} Hz",
                )
            )

    async def set_source_mode(self, mode: str) -> bool:
        """Execute the safe 6-step lifecycle to switch telemetry source mode ('LIVE' | 'REPLAY')."""
        normalized = mode.strip().upper()
        if normalized not in ("LIVE", "REPLAY"):
            logger.warning(f"Invalid telemetry source mode requested: {mode}")
            return False

        async with self._source_lock:
            if self._source_mode == normalized:
                return True

            logger.info(f"Transitioning telemetry source mode: {self._source_mode} -> {normalized}")
            was_running = self._state == "running"

            # 1. Stop current source
            if was_running:
                self._state = "paused"
                await asyncio.sleep(0.05)

            # 2. Clean up current source
            try:
                await self.telemetry_source.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting previous source: {e}")

            # 3. Set new source
            if normalized == "LIVE":
                self.telemetry_source = self._live_telemetry_source
            else:
                if self.replay_service is None or not self.replay_service.is_loaded:
                    logger.error(
                        "Cannot switch to REPLAY mode: No replay dataset loaded in ReplayService"
                    )
                    self._state = "running" if was_running else "paused"
                    return False
                self.telemetry_source = self.replay_service.active_source

            # 4. Reset source-specific state
            if normalized == "LIVE":
                if hasattr(self.telemetry_source, "simulator") and hasattr(
                    self.telemetry_source.simulator, "reset"
                ):
                    self.telemetry_source.simulator.reset()
            else:
                if hasattr(self.telemetry_source, "reset"):
                    self.telemetry_source.reset()

            if self.physics_service is not None and hasattr(self.physics_service, "reset"):
                self.physics_service.reset()

            if self.prognostics_service is not None and hasattr(self.prognostics_service, "reset"):
                self.prognostics_service.reset()

            if hasattr(self, "_validator") and hasattr(self._validator, "reset"):
                self._validator.reset()

            # 5. Start new source if was previously running
            self._source_mode = normalized
            if was_running:
                await self.telemetry_source.connect()
                self._state = "running"

            # 6. Broadcast active source mode notification
            logger.info(f"Successfully switched telemetry source mode to {self._source_mode}")
            await self.broadcaster.broadcast_status(
                StatusMessage(
                    status="running" if self._state == "running" else "paused",
                    message=f"Telemetry source switched to {self._source_mode} mode",
                )
            )
            return True

    async def execute_command(self, command: str, params: dict[str, Any]) -> None:
        """Execute a validated client command."""
        cmd = command.lower()
        if cmd == "start":
            await self.start()
        elif cmd == "pause":
            await self.pause()
        elif cmd == "resume":
            await self.resume()
        elif cmd == "reset":
            await self.reset()
        elif cmd == "set_scenario":
            scenario = params.get("phase_name") or params.get("scenario")
            if scenario and isinstance(scenario, str):
                await self.set_scenario(scenario)
        elif cmd == "set_rate":
            rate = params.get("rate_hz")
            if rate is not None and isinstance(rate, int | float):
                await self.set_rate(int(rate))
        elif cmd == "set_source":
            mode = params.get("mode") or params.get("source_mode")
            if mode and isinstance(mode, str):
                await self.set_source_mode(mode)
        elif cmd.startswith("replay_"):
            action = cmd.replace("replay_", "")
            target = (
                params.get("target")
                or params.get("speed")
                or params.get("index")
                or params.get("timestamp")
            )
            if self.replay_service:
                try:
                    self.replay_service.control(action, target)
                except Exception as re:
                    logger.error(f"Error executing replay command {cmd}: {re}")
        else:
            logger.warning(f"Ignored unrecognized command: {command}")

    async def stop(self) -> None:
        """Gracefully stop the realtime loop and disconnect telemetry source."""
        self._state = "stopped"
        self._shutdown_event.set()

        tasks = [t for t in (self._loop_task, self._heartbeat_task) if t and not t.done()]
        for t in tasks:
            t.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._loop_task = None
        self._heartbeat_task = None

        await self.telemetry_source.disconnect()
        await self.broadcaster.broadcast_status(
            StatusMessage(status="stopped", message="Telemetry streaming terminated")
        )
        logger.info("Realtime telemetry publication service stopped cleanly")

    async def _realtime_loop(self) -> None:
        """Main asynchronous pacing and publication loop."""
        while not self._shutdown_event.is_set():
            if self._state == "running":
                start_time = time.perf_counter()
                try:
                    frame = await self.telemetry_source.get_next_frame()

                    # Domain validation
                    val_result = self._validator.validate(frame)
                    if not val_result.is_valid and self.strict_validation:
                        logger.warning(
                            f"Frame seq={frame.sequence_id} rejected by validator: {val_result.errors}"
                        )
                    else:
                        physics_res = None
                        if self.physics_service is not None:
                            try:
                                physics_res = self.physics_service.evaluate_frame(frame)
                            except Exception as pe:
                                logger.error(f"Error evaluating physics twin: {pe}")

                        ml_res = None
                        if self.ml_service is not None:
                            try:
                                ml_res = self.ml_service.evaluate(frame, physics_res)
                            except Exception as me:
                                logger.error(f"Error evaluating ML diagnostics: {me}")

                        prognostics_res = None
                        if self.prognostics_service is not None:
                            try:
                                prognostics_res = self.prognostics_service.evaluate(
                                    frame, physics_res, ml_res
                                )
                            except Exception as pre:
                                logger.error(f"Error evaluating prognostics: {pre}")

                        replay_status = None
                        if self._source_mode == "REPLAY" and self.replay_service:
                            replay_status = self.replay_service.get_status()

                        msg = TelemetryMessage(
                            timestamp=frame.timestamp,
                            sequence_id=frame.sequence_id,
                            server_time=time.time(),
                            source_mode=self._source_mode,
                            payload=frame,
                            physics=physics_res,
                            ml=ml_res,
                            prognostics=prognostics_res,
                            mission=self._current_mission_context,
                            replay=replay_status,
                        )
                        await self.broadcaster.broadcast_telemetry(msg)

                except Exception as e:
                    logger.error(f"Error in realtime publication loop: {e}", exc_info=True)

                # Monotonic timing compensation to maintain target rate_hz
                dt = 1.0 / self.rate_hz
                elapsed = time.perf_counter() - start_time
                sleep_time = max(0.0, dt - elapsed)
                try:
                    await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    break
            else:
                try:
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    break

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat emitter ensuring idle or slow connections do not time out."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.heartbeat_interval_sec)
                if not self._shutdown_event.is_set():
                    await self.broadcaster.broadcast_heartbeat(
                        HeartbeatMessage(server_time=time.time())
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
