from logging import Logger

from app.services.counter_service import CounterService
from app.services.faulty_service import FaultyService
from app.services.heartbeat_service import HeartbeatService
from app.services.worker_process_service import WorkerProcessService


class ServiceFactory:

    @staticmethod
    def create(service, logger: Logger):

        service_type = service["type"]

        if service_type == "heartbeat":
            return HeartbeatService(logger)

        if service_type == "counter":
            return CounterService(logger)

        if service_type == "faulty":
            return FaultyService(logger)

        if service_type == "worker":

            return WorkerProcessService(
                logger=logger,
                service_name=service["name"],
                command=service["command"]
            )

        raise Exception(
            f"Unknown service: {service_type}"
        )