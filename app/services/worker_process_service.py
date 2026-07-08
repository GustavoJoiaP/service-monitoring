import asyncio
from asyncio import Task
from logging import Logger
from typing import Optional

from app.core.process_inspector import ProcessInspector
from app.core.process_manager import ProcessManager

from app.models.service_status import ServiceStatus
from app.services.interfaces.iservice import IService


class WorkerProcessService(IService):

    def __init__(
        self,
        logger: Logger,
        service_name: str,
        command: list[str]
    ):

        self._logger = logger
        self._service_name = service_name
        self._command = command

        self._manager = ProcessManager()
        self._inspector = ProcessInspector()

        self._process = None
        self._task: Optional[Task] = None

        self._status = ServiceStatus.STOPPED

    @property
    def name(self) -> str:
        return self._service_name

    @property
    def status(self) -> ServiceStatus:
        return self._status

    @property
    def task(self) -> Optional[Task]:
        return self._task

    async def start(self) -> None:

        if self._status == ServiceStatus.RUNNING:
            return

        self._logger.info(
            f"Starting worker {self.name}"
        )

        self._process = await self._manager.start(
            self._command
        )

        self._status = ServiceStatus.RUNNING

    async def stop(self) -> None:

        if self._process is None:
            return

        self._logger.info(
            f"Stopping worker {self.name}"
        )

        await self._manager.stop(
            self._process
        )

        self._status = ServiceStatus.STOPPED

    async def restart(self) -> None:

        self._logger.warning(
            f"Restarting worker {self.name}"
        )

        await self.stop()

        await asyncio.sleep(1)

        await self.start()

    async def is_alive(self) -> bool:

        self._logger.info(f"Checking {self.name}")

        if self._process is None:
            self._logger.warning(f"{self.name}: process is None")
            return False

        info = await self._inspector.get_process_info(
            self._process.pid
        )

        self._logger.info(
            f"{self.name}: pid={self._process.pid} exists={info.exists}"
        )

        return info.exists