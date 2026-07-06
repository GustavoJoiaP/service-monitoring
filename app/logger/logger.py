import logging
import sys


class Logger:

    _instance = None

    def __new__(cls):

        if cls._instance is None:

            cls._instance = super().__new__(cls)

            cls._instance._configure()

        return cls._instance

    def _configure(self):

        self._logger = logging.getLogger("LinuxServiceHost")

        self._logger.setLevel(logging.INFO)

        if not self._logger.handlers:

            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s"
            )

            handler = logging.StreamHandler(sys.stdout)

            handler.setFormatter(formatter)

            self._logger.addHandler(handler)

    @property
    def instance(self):

        return self._logger