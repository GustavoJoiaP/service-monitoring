import time
from logging import Logger as PythonLogger
from typing import Dict

from app.services.interfaces.iservice import IService


class RecoveryManager:

    def __init__(
        self,
        logger: PythonLogger,
        max_retries: int = 3,
        cooldown: int = 30,
    ):

        self._logger = logger
        self._max_retries = max_retries
        self._cooldown = cooldown

        self._attempts: Dict[str, int] = {}
        self._last_attempt: Dict[str, float] = {}

    async def recover(self, service: IService):

        now = time.monotonic()
        name = service.name

        if name in self._last_attempt:
            elapsed = now - self._last_attempt[name]

            if elapsed < self._cooldown:
                self._logger.warning(
                    f"[{name}] Recovery skipped — "
                    f"last attempt was {elapsed:.0f}s ago "
                    f"(cooldown: {self._cooldown}s)"
                )
                return

        attempts = self._attempts.get(name, 0)

        if attempts >= self._max_retries:
            self._logger.critical(
                f"[{name}] Circuit breaker OPEN — "
                f"{attempts} consecutive failures. "
                f"Manual intervention required."
            )
            return

        self._attempts[name] = attempts + 1
        self._last_attempt[name] = now

        self._logger.warning(
            f"[{name}] Recovery attempt {attempts + 1}/{self._max_retries}"
        )

        await service.restart()

        if await service.is_alive():
            self._attempts.pop(name, None)
            self._last_attempt.pop(name, None)
            self._logger.info(f"[{name}] Recovered successfully.")
        else:
            self._logger.error(
                f"[{name}] Recovery attempt {attempts + 1} failed."
            )