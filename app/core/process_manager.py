import asyncio
from asyncio.subprocess import Process


class ProcessManager:

    async def start(self, command: list[str]) -> Process:

        return await asyncio.create_subprocess_exec(
            *command
        )

    async def stop(self, process: Process):

        if process.returncode is None:

            process.terminate()

            await process.wait()

    async def is_alive(self, process: Process) -> bool:

        return process.returncode is None