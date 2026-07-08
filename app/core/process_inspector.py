import asyncio

from app.models.process_info import ProcessInfo


class ProcessInspector:

    async def get_process_info(self, pid: int) -> ProcessInfo:

        process = await asyncio.create_subprocess_exec(
            "ps",
            "-p",
            str(pid),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await process.communicate()

        exists = str(pid) in stdout.decode()

        return ProcessInfo(
            pid=pid,
            exists=exists
        )