import os
import asyncio

from app.models.process_info import ProcessInfo


class ProcessInspector:

    async def get_process_info(self, pid: int) -> ProcessInfo:

        loop = asyncio.get_running_loop()

        def _check():
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

        exists = await loop.run_in_executor(None, _check)

        return ProcessInfo(
            pid=pid,
            exists=exists
        )