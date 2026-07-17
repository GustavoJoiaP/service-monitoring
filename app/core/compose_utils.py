from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def find_compose() -> List[str]:
    if shutil.which("docker"):
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return ["docker", "compose"]
        except Exception:
            pass

    if shutil.which("docker-compose"):
        return ["docker-compose"]

    if shutil.which("podman-compose"):
        return ["podman-compose"]

    raise RuntimeError("No docker-compose or podman-compose found.")


async def run_compose(
    compose_file: Path,
    action: str,
    extra_args: Optional[List[str]] = None,
    logger: Optional[logging.Logger] = None,
) -> int:
    compose_bin = find_compose()
    cmd = compose_bin + ["-f", str(compose_file), action]
    if extra_args:
        cmd.extend(extra_args)

    if logger:
        logger.info("Running: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        if logger:
            logger.error(
                "Compose %s failed (rc=%s): %s",
                action,
                proc.returncode,
                stderr.decode().strip(),
            )

    return proc.returncode


async def compose_down(
    compose_file: Path,
    logger: Optional[logging.Logger] = None,
) -> int:
    return await run_compose(compose_file, "down", logger=logger)


async def compose_up(
    compose_file: Path,
    logger: Optional[logging.Logger] = None,
) -> int:
    extra_args = ["-d", "--build", "--force-recreate"]
    return await run_compose(compose_file, "up", extra_args=extra_args, logger=logger)
