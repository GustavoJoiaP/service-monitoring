from typing import Dict, List

from services.interfaces.iservice import IService



class ServiceRegistry:


    def __init__(self) -> None:
        self._services: Dict[str, IService] = {} 

    @property
    def count(self) -> int:

        return len(self._services)

    def register(self, service: IService) -> None:


        if service.name in self._services:
            raise ValueError(
                f'Service "{service.name}" is already registered.'
            )

        self._services[service.name] = service

    def unregister(self, service_name: str) -> None:


        self._services.pop(service_name, None)

    def exists(self, service_name: str) ->bool:


        return service_name in self._services

    def get(self, service_name: str) -> IService:


        if not self.exists(service_name):
            raise KeyError(
                f'Service "{service_name}" not found.'
            )

        return self._services[service_name]

    def get_all(self) -> List[IService]: 


        return list(self._services.values())

    def clear(self) -> None:


        self._services.clear()