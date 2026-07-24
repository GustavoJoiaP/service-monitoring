from __future__ import annotations

import asyncio
import urllib.request
from asyncio import Task
from logging import Logger as PythonLogger
from typing import Any, Dict, Optional
from urllib.error import URLError

from app.models.service_status import ServiceStatus
from app.services.interfaces.iservice import IService


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


_no_redirect_opener = urllib.request.build_opener(_NoRedirectHandler())


class ContainerService(IService):

    def __init__(self, logger: PythonLogger, config: Dict[str, Any]) -> None:
        self._logger = logger
        self._config = config
        self._service_name: str = config["name"]
        self._container_name: str = config["container_name"]
        self._check_type: str = config.get("check", "container_state")
        self._runtime: str = config.get("runtime", "docker")
        self._status = ServiceStatus.STOPPED
        self._task: Optional[Task] = None

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

        self._status = ServiceStatus.STARTING

        exists = await self._container_exists()

        if exists:
            self._status = ServiceStatus.RUNNING
            self._logger.info(f"[{self.name}] Container '{self._container_name}' found. Monitoring started.")
        else:
            self._logger.warning(
                f"[{self.name}] Container '{self._container_name}' not found. "
                f"Will attempt recovery if configured."
            )
            self._status = ServiceStatus.FAILED

    async def stop(self) -> None:
        if self._status == ServiceStatus.STOPPED:
            return

        self._logger.info(f"[{self.name}] Monitoring stopped (container left running).")
        self._status = ServiceStatus.STOPPED

    async def restart(self) -> None:
        self._logger.warning(f"[{self.name}] Restarting container '{self._container_name}'...")

        for attempt in range(1, 4):
            self._logger.info(
                f"[{self.name}] Restart attempt {attempt}/3..."
            )

            proc = await asyncio.create_subprocess_exec(
                self._runtime, "restart", self._container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                await asyncio.sleep(3)

                if await self.is_alive():
                    self._logger.info(f"[{self.name}] Container restarted and healthy.")
                    self._status = ServiceStatus.RUNNING
                    return

                self._logger.warning(
                    f"[{self.name}] Container started but service is unhealthy "
                    f"(health check failed)"
                )
            else:
                self._logger.warning(
                    f"[{self.name}] {self._runtime} restart failed (attempt {attempt}): "
                    f"{stderr.decode().strip()}"
                )

            await asyncio.sleep(2 ** attempt)

        self._logger.error(f"[{self.name}] All restart attempts failed.")
        self._status = ServiceStatus.FAILED

    async def is_alive(self) -> bool:
        try:
            if self._check_type == "container_state":
                return await self._check_container_state()
            elif self._check_type == "tcp":
                return await self._check_tcp()
            elif self._check_type == "http":
                return await self._check_http()
            else:
                self._logger.error(f"[{self.name}] Unknown check type: {self._check_type}")
                return False
        except Exception as ex:
            self._logger.error(f"[{self.name}] Health check error: {ex}")
            return False

    async def _container_exists(self) -> bool:
        proc = await asyncio.create_subprocess_exec(
            self._runtime, "ps", "-a", "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await proc.communicate()
        return self._container_name in stdout.decode().splitlines()

    async def _check_container_state(self) -> bool:
        proc = await asyncio.create_subprocess_exec(
            self._runtime, "inspect", "--format", "{{.State.Status}}", self._container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        status = stdout.decode().strip()

        if status == "running":
            return True

        self._logger.warning(
            f"[{self.name}] Container status is '{status}' (expected 'running')"
        )
        return False

    async def _check_tcp(self) -> bool:
        host = self._config.get("host", "127.0.0.1")
        port = self._config["port"]

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError):
            self._logger.warning(
                f"[{self.name}] TCP check failed for {host}:{port}"
            )
            return False

    async def _check_http(self) -> bool:
        url = self._config["url"]
        expected_status = self._config.get("expected_status", 200)
        timeout = self._config.get("timeout", 10)
        retries = self._config.get("retries", 2)

        loop = asyncio.get_running_loop()

        def _request() -> Optional[int]:
            try:
                req = urllib.request.Request(url, method="GET")
                with _no_redirect_opener.open(req, timeout=timeout) as response:
                    return response.status
            except (URLError, OSError, ValueError):
                return None

        for attempt in range(1 + retries):
            status = await loop.run_in_executor(None, _request)

            if status == expected_status:
                return True

            if status is None:
                self._logger.warning(
                    f"[{self.name}] HTTP check attempt {attempt + 1}/{1 + retries} "
                    f"for {url} failed (connection/request error)"
                )
            else:
                self._logger.warning(
                    f"[{self.name}] HTTP check attempt {attempt + 1}/{1 + retries} "
                    f"for {url} returned {status} (expected {expected_status})"
                )

            if attempt < retries:
                await asyncio.sleep(1 + attempt)

        return False
