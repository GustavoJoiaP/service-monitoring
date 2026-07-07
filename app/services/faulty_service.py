import asyncio
from asyncio import Task
from logging import Logger as PythonLogger
from typing import Optional

from app.models.service_status import ServiceStatus
from app.services.interfaces.iservice import IService


class FaultyService(IService):

    def __init__(self, logger: PythonLogger):

        self._logger = logger

        self._status = ServiceStatus.REGISTERED

        self._task: Optional[Task] = None

        self._running = False

        self._counter = 0

    @property
    def name(self) -> str:
        return "FaultyService"

    @property
    def status(self) -> ServiceStatus:
        return self._status

    @property
    def task(self) -> Optional[Task]:
        return self._task

    async def start(self) -> None:

        if self._running:
            return

        self._logger.info(f"Starting {self.name}")

        self._running = True
        self._status = ServiceStatus.RUNNING

        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:

        self._running = False

        if self._task:

            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._status = ServiceStatus.STOPPED

        self._logger.info(f"{self.name} stopped.")

    async def restart(self) -> None:

        self._logger.warning(f"Restarting {self.name}")

        self._counter = 0

        await self.stop()

        await self.start()

    async def is_alive(self) -> bool:

        return (
            self._task is not None
            and not self._task.done()
            and self._status == ServiceStatus.RUNNING
        )

    async def _run(self):

        try:

            while self._running:

                self._counter += 1

                self._logger.info(
                    f"FaultyService Counter: {self._counter}"
                )

                if self._counter == 10:
                    raise RuntimeError(
                        "Simulated service failure."
                    )

                await asyncio.sleep(1)

        except Exception as ex:

            self._status = ServiceStatus.FAILED

            self._running = False

            self._logger.error(
                f"{self.name} failed: {ex}"
            )