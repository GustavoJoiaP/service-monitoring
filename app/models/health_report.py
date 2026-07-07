from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.models.process_info import ProcessInfo


@dataclass(frozen=True)
class HealthReport:

    service_name: str

    healthy: bool

    checked_at: datetime

    process: Optional[ProcessInfo] = None

    message: str = ""