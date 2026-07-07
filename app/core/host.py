import asyncio
from logging import Logger as PythonLogger

from app.core.configuration import Configuration
from app.core.recovery_manager import RecoveryManager
from app.core.registry import ServiceRegistry
from app.core.service_factory import ServiceFactory
from app.core.service_manager import ServiceManager

from app.services.faulty_service import FaultyService
from app.services.heartbeat_service import HeartbeatService
from app.services.counter_service import CounterService
from app.core.health_monitor import HealthMonitor
from app.services.worker_process_service import WorkerProcessService


class Host:

    def __init__(self, logger: PythonLogger):

        self._logger = logger

        self._registry = ServiceRegistry()

        self._manager = ServiceManager(self._registry)
        self._recovery_manager = RecoveryManager(self._logger)

        self._health_monitor = HealthMonitor(
            registry=self._registry,
            logger=self._logger,
            recovery_manager=self._recovery_manager
        )

    async def initialize(self):

        self._logger.info("Initializing Host...")
        configuration = Configuration("config/services.json")

        for service in configuration.services:

            if not service["enabled"]:
                continue

            instance = ServiceFactory.create(
                service["type"],
                self._logger
            )

            self._registry.register(instance)

        self._logger.info(
            f"{self._registry.count} services registered."
        )

    async def start(self):

        self._logger.info("Starting services...")

        await self._manager.start_all()
        await self._health_monitor.start()

        self._logger.info("All services started.")

    async def run(self):

        await self.initialize()

        await self.start()

        self._logger.info("Linux Service Host is running.")


        while True:

            await asyncio.sleep(1)
    
    async def stop(self):

        self._logger.info("Stopping Host...")
        await self._health_monitor.stop()

        await self._manager.stop_all()

        self._logger.info("Host stopped.")