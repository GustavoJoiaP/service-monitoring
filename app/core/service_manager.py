from __future__ import annotations

import asyncio
from typing import List

from app.core.registry import ServiceRegistry
from app.services.interfaces.iservice import IService


class ServiceManager:


    def __init__(self, registry: ServiceRegistry) -> None:
        self._registry = registry

    @property
    def services(self) -> List[IService]:

        return self._registry.get_all()

    async def start(self, service_name: str) -> None:

        service = self._registry.get(service_name)
        self._logger.info(
            f"Starting service [{service.name}]"
        )

        await service.start()

    async def stop(self, service_name: str) -> None:

        service = self._registry.get(service_name)

        await service.stop()

    async def restart(self, service_name: str) -> None:

        service = self._registry.get(service_name)

        await service.restart()

    async def start_all(self) -> None:

        tasks = [
            service.start()
            for service in self.services
        ]

        await asyncio.gather(*tasks)

    async def stop_all(self) -> None:

        tasks = [
            service.stop()
            for service in self.services
        ]

        await asyncio.gather(*tasks)

    async def restart_all(self) -> None:

        tasks = [
            service.restart()
            for service in self.services
        ]

        await asyncio.gather(*tasks)