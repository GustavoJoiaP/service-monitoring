import asyncio
from asyncio.subprocess import Process
from logging import Logger as PythonLogger
from typing import Optional

from app.core.process_inspector import ProcessInspector
from app.core.process_manager import ProcessManager
from app.models.service_status import ServiceStatus
from app.services.interfaces.iservice import IService


class WorkerProcessService(IService):

    def __init__(self, logger: PythonLogger):

        self._logger = logger

        self._manager = ProcessManager()

        self._process: Optional[Process] = None

        self._status = ServiceStatus.REGISTERED
        
        self._inspector = ProcessInspector()

    @property
    def name(self):

        return "WorkerProcess"

    @property
    def status(self):

        return self._status

    @property
    def task(self):

        return None

    async def start(self):

        self._logger.info(
            "Starting WorkerProcess..."
        )

        self._process = await self._manager.start(
            [
                "python3",
                "app/workers/worker.py",
            ]
        )

        self._status = ServiceStatus.RUNNING

    async def stop(self):

        if self._process:

            await self._manager.stop(
                self._process
            )

        self._status = ServiceStatus.STOPPED

    async def restart(self):

        self._logger.warning(
            "Restarting WorkerProcess..."
        )

        await self.stop()

        await self.start()

    async def is_alive(self) -> bool:

        if self._process is None:
            return False

        info = await self._inspector.inspect(
            self._process.pid
        )

        return info.exists