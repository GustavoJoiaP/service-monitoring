from __future__ import annotations

import asyncio
from asyncio import Task
from logging import Logger as PythonLogger
from typing import Optional

from app.models.service_status import ServiceStatus
from app.services.interfaces.iservice import IService


class CounterService(IService):

    def __init__(self, logger: PythonLogger):

        self._logger = logger

        self._task: Optional[Task] = None

        self._status = ServiceStatus.STOPPED

        self._counter = 0

    @property
    def name(self) -> str:
        return "counter"

    @property
    def status(self):
        return self._status

    @property
    def task(self):
        return self._task

    async def start(self):

        if self._task is not None:
            return

        self._status = ServiceStatus.STARTING

        self._task = asyncio.create_task(
            self._run()
        )

    async def stop(self):

        if self._task is None:
            return

        self._task.cancel()

        try:
            await self._task

        except asyncio.CancelledError:
            pass

        self._task = None

        self._status = ServiceStatus.STOPPED

    async def restart(self):

        await self.stop()

        await self.start()

    async def is_alive(self):

        return (
            self._task is not None
            and not self._task.done()
        )

    async def _run(self):

        self._status = ServiceStatus.RUNNING

        try:

            while True:

                self._counter += 1

                self._logger.info(
                    f"Counter: {self._counter}"
                )

                await asyncio.sleep(1)

        finally:

            self._status = ServiceStatus.STOPPED