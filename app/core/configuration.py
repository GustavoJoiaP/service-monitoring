import json


class Configuration:

    def __init__(self, path: str):

        with open(path, "r") as file:

            self._config = json.load(file)

    @property
    def services(self):

        return self._config["services"]