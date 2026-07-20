import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.compose_utils import find_compose


class Configuration:

    def __init__(self, path: str):

        with open(path, "r") as file:
            self._config = json.load(file)

        self._config_path = Path(path).resolve()

    @property
    def services(self):
        return self._config["services"]

    @property
    def compose_config(self) -> Optional[Dict[str, Any]]:
        raw = self._config.get("compose")
        if not raw:
            return None

        compose_file = raw.get("file")
        if not compose_file:
            return None

        file_path = Path(compose_file)
        if not file_path.is_absolute():
            file_path = self._config_path.parent.parent.parent / file_path

        try:
            compose_bin = find_compose()
        except RuntimeError:
            return None

        return {
            "file": file_path,
            "bin": compose_bin,
        }