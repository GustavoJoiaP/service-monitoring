from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Task
from typing import Optional

from app.models.service_status import ServiceStatus


class IService(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def status(self) -> ServiceStatus:
        pass

    @property
    @abstractmethod
    def task(self) -> Optional[Task]:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def restart(self) -> None:
        pass

    @abstractmethod
    async def is_alive(self) -> bool:
        pass