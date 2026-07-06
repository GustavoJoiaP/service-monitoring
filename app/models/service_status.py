from enum import Enum, auto


class ServiceStatus(Enum):
    """
    Representa o estado atual de um serviço.
    """

    REGISTERED = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    FAILED = auto()
    RECOVERING = auto()