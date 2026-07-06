import asyncio

from core import host
from logger.logger import Logger


async def main():

    logger = Logger().instance


    await host.run()


if __name__ == "__main__":

    asyncio.run(main())