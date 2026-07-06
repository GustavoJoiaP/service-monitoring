import asyncio

from app.core import host
from app.logger.logger import Logger


async def main():

    logger = Logger().instance


    await host.run()


if __name__ == "__main__":

    asyncio.run(main())