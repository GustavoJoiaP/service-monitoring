import asyncio
from asyncio import Task
from logging import Logger as PythonLogger
from typing import Optional

from app.core.registry import ServiceRegistry
from app.core.recovery_manager import RecoveryManager


class HealthMonitor:

    def __init__(
        self,
        registry: ServiceRegistry,
        logger: PythonLogger,
        recovery_manager: RecoveryManager,
        interval: int = 5,
    ):

        self._registry = registry
        self._logger = logger
        self._recovery_manager = recovery_manager
        self._interval = interval

        self._running = False
        self._task: Optional[Task] = None

    async def start(self):

        if self._running:
            return

        self._running = True

        self._task = asyncio.create_task(self._monitor())

        self._logger.info("HealthMonitor started.")

    async def stop(self):

        self._running = False

        if self._task:

            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._logger.info("HealthMonitor stopped.")

    async def _monitor(self):

        while self._running:

            for service in self._registry.get_all():

                alive = await service.is_alive()

                if alive:

                    self._logger.info(
                        f"[HEALTH] {service.name} -> HEALTHY"
                    )

                else:

                    self._logger.warning(
                        f"[HEALTH] {service.name} -> FAILED"
                    )
                    await self._recovery_manager.recover(service)

            await asyncio.sleep(self._interval)