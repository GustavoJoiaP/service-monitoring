import asyncio
from asyncio import Task
from logging import Logger as PythonLogger
from typing import Dict, Optional

from app.core.registry import ServiceRegistry
from app.core.recovery_manager import RecoveryManager


class HealthMonitor:

    def __init__(
        self,
        registry: ServiceRegistry,
        logger: PythonLogger,
        recovery_manager: RecoveryManager,
        interval: int = 5,
        max_failures: int = 3,
    ):

        self._registry = registry
        self._logger = logger
        self._recovery_manager = recovery_manager
        self._interval = interval
        self._max_failures = max_failures

        self._running = False
        self._task: Optional[Task] = None
        self._failures: Dict[str, int] = {}

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

            services = self._registry.get_all()

            tasks = [self._check_service(svc) for svc in services]

            await asyncio.gather(*tasks)

            await asyncio.sleep(self._interval)

    async def _check_service(self, service):

        try:

            alive = await service.is_alive()

            if alive:

                self._failures.pop(service.name, None)

                self._logger.info(
                    f"[HEALTH] {service.name} -> HEALTHY"
                )

            else:

                count = self._failures.get(service.name, 0) + 1
                self._failures[service.name] = count

                self._logger.warning(
                    f"[HEALTH] {service.name} -> FAILED "
                    f"({count}/{self._max_failures})"
                )

                if count >= self._max_failures:

                    self._failures.pop(service.name, None)

                    await self._recovery_manager.recover(service)

        except Exception as ex:

            self._logger.exception(
                f"Health check failed for {service.name}: {ex}"
            )