import asyncio

from app.core.host import Host
from app.logger.logger import Logger


async def main():

    logger = Logger().instance

    host = Host(logger)

    await host.run()


if __name__ == "__main__":
    asyncio.run(main())