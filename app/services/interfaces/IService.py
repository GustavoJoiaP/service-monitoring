from abc import ABC, abstractmethod

from models.health_status import HealthStatus
from models.service_status import ServiceStatus


class IService(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def status(self) -> ServiceStatus:
        ...

    @property
    @abstractmethod
    def health(self) -> HealthStatus:
        ...

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def restart(self) -> None:
        ...

    @abstractmethod
    async def check_health(self) -> HealthStatus:
        ...