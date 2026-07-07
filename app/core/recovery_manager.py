from logging import Logger as PythonLogger

from app.services.interfaces.iservice import IService


class RecoveryManager:

    def __init__(self, logger: PythonLogger):

        self._logger = logger

    async def recover(self, service: IService):

        self._logger.warning(
            f"Recovery started for [{service.name}]"
        )

        await service.restart()

        self._logger.info(
            f"Service [{service.name}] recovered successfully."
        )