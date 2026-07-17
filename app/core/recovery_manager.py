import asyncio
import time
from logging import Logger as PythonLogger
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.compose_utils import compose_down, compose_up
from app.services.interfaces.iservice import IService


class RecoveryManager:

    def __init__(
        self,
        logger: PythonLogger,
        max_retries: int = 3,
        cooldown: int = 30,
        compose_config: Optional[Dict[str, Any]] = None,
    ):

        self._logger = logger
        self._max_retries = max_retries
        self._cooldown = cooldown
        self._compose_config = compose_config

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
                f"Escalating to compose-level recovery."
            )
            await self._compose_recover(service, name)
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

    async def _compose_recover(self, service: IService, name: str) -> None:
        if not self._compose_config:
            self._logger.critical(
                f"[{name}] No compose config available. "
                f"Manual intervention required."
            )
            return

        compose_file: Path = self._compose_config["file"]

        if not compose_file.exists():
            self._logger.critical(
                f"[{name}] Compose file not found: {compose_file}. "
                f"Manual intervention required."
            )
            return

        self._logger.critical(
            f"[{name}] Running compose down on {compose_file}..."
        )

        rc_down = await compose_down(compose_file, logger=self._logger)

        self._logger.critical(
            f"[{name}] Compose down finished (rc={rc_down}). "
            f"Running compose up..."
        )

        rc_up = await compose_up(compose_file, logger=self._logger)

        self._logger.critical(
            f"[{name}] Compose up finished (rc={rc_up}). "
            f"Waiting for services to stabilize..."
        )

        await asyncio.sleep(10)

        self._attempts.pop(name, None)
        self._last_attempt.pop(name, None)

        if await service.is_alive():
            self._logger.info(
                f"[{name}] Compose-level recovery succeeded."
            )
        else:
            self._logger.critical(
                f"[{name}] Compose-level recovery FAILED. "
                f"Manual intervention required."
            )