from __future__ import annotations

import asyncio
from asyncio import Task
from typing import Optional

from app.models.service_status import ServiceStatus
from app.services.interfaces.iservice import IService


class HeartbeatService(IService):

    def __init__(self) -> None:

        self._status = ServiceStatus.STOPPED

        self._task: Optional[Task] = None

    @property
    def name(self) -> str:
        return "heartbeat"

    @property
    def status(self) -> ServiceStatus:
        return self._status

    @property
    def task(self) -> Optional[Task]:
        return self._task

    async def start(self) -> None:

        if self._task is not None:
            return

        self._status = ServiceStatus.STARTING

        self._task = asyncio.create_task(
            self._run()
        )

    async def stop(self) -> None:

        if self._task is None:
            return

        self._task.cancel()

        try:

            await self._task

        except asyncio.CancelledError:

            pass

        self._task = None

        self._status = ServiceStatus.STOPPED

    async def restart(self) -> None:

        await self.stop()

        await self.start()

    async def is_alive(self) -> bool:

        return (
            self._task is not None
            and not self._task.done()
        )

    async def _run(self) -> None:

        self._status = ServiceStatus.RUNNING

        try:

            while True:

                print("Heartbeat ❤️")

                await asyncio.sleep(5)

        except asyncio.CancelledError:

            self._status = ServiceStatus.STOPPING

            raise

        finally:

            self._status = ServiceStatus.STOPPED