import asyncio
from logging import Logger

from app.core.process_inspector import ProcessInspector
from app.core.process_manager import ProcessManager

from app.models.health_status import HealthStatus
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

    @property
    def name(self):

        return self._service_name

    @property
    def health(self):

        if self._process is None:
            return HealthStatus.UNHEALTHY

        return HealthStatus.HEALTHY

    async def start(self):

        self._logger.info(
            f"Starting {self.name}"
        )

        self._process = await self._manager.start(
            self._command
        )

    async def stop(self):

        if self._process is None:
            return

        await self._manager.stop(
            self._process
        )

    async def execute(self):

        pass

    async def is_alive(self):

        if self._process is None:
            return False

        info = await self._inspector.get_process_info(
            self._process.pid
        )

        return info.exists

    async def check_health(self):

        return await self.is_alive()