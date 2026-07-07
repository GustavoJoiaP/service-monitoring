from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProcessInfo:

    pid: Optional[int] = None

    exists: bool = False

    command: Optional[str] = None

    user: Optional[str] = None

    cpu_percent: Optional[float] = None

    memory_mb: Optional[float] = None

    uptime_seconds: Optional[int] = None
    