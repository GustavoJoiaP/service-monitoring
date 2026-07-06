from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class HealthStatus:


    healthy: bool

    last_check: datetime

    last_failure: Optional[datetime] = None

    message: str = ""

    recovery_attempts: int = 0