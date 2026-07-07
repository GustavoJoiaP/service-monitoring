import asyncio

from app.core.host import Host
from app.logger.logger import Logger


async def main():

    logger = Logger().instance

    host = Host(logger)

    try:

        await host.run()

    except KeyboardInterrupt:

        logger.info("KeyboardInterrupt received.")

        await host.stop()


if __name__ == "__main__":

    asyncio.run(main())