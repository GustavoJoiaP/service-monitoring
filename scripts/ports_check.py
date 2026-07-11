import logging
import socket
import random
import shutil
import yaml
import pwd
import os
import subprocess
import time

from copy import deepcopy

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMPOSE_FILE = PROJECT_ROOT / "podman" / "podman-compose.yaml"

def __init__():
    
    logger = logging.getLogger("PortsCheck")
    logging.basicConfig(level=logging.INFO)

def fix_nvidia_cdi():

    cdi_file = "/etc/cdi/nvidia.yaml"

    if not os.path.exists(cdi_file):
        return

    with open(cdi_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []

    skip = 0

    for line in lines:

        if skip:
            skip -= 1
            continue

        if "additionalGids:" in line:
            skip = 2
            continue

        new_lines.append(
            line.replace("0.7.0", "0.5.0")
        )

    with open(cdi_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def is_port_available(port: int) -> bool:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        return s.connect_ex(("127.0.0.1", port)) != 0


def get_random_free_port(start=10000, end=65000):

    while True:

        port = random.randint(start, end)

        if is_port_available(port):
            return port


def process_port_mapping(original_mapping):

    if not isinstance(original_mapping, str):
        return original_mapping

    port_mapping = original_mapping

    protocol = ""

    if "/" in port_mapping:

        port_mapping, protocol = port_mapping.split("/", 1)

        protocol = "/" + protocol

    parts = port_mapping.split(":")

    if len(parts) != 2:
        return original_mapping

    host_port = parts[0]
    container_port = parts[1]

    if "-" in host_port:

        host_start, host_end = map(int, host_port.split("-"))

        cont_start, cont_end = map(int, container_port.split("-"))

        occupied = any(
            not is_port_available(p)
            for p in range(host_start, host_end + 1)
        )

        if not occupied:
            return original_mapping

        size = host_end - host_start

        while True:

            new_start = random.randint(
                10000,
                60000 - size
            )

            new_end = new_start + size

            all_free = all(
                is_port_available(p)
                for p in range(new_start, new_end + 1)
            )

            if all_free:

                return (
                    f"{new_start}-{new_end}:"
                    f"{cont_start}-{cont_end}"
                    f"{protocol}"
                )

    host_port_int = int(host_port)

    if is_port_available(host_port_int):

        return (
            f"{host_port}:{container_port}"
            f"{protocol}"
        )

    new_port = get_random_free_port()

    return f"{new_port}:{container_port}{protocol}"


def find_compose():

    # Docker Compose v2
    if shutil.which("docker"):

        try:

            subprocess.run(
                ["docker", "compose", "version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )

            return ["docker", "compose"]

        except Exception:
            pass

    # Docker Compose v1
    if shutil.which("docker-compose"):

        return ["docker-compose"]

    # Podman Compose
    if shutil.which("podman-compose"):

        return ["podman-compose"]

    raise RuntimeError(
        "Docker Compose or Podman Compose not found."
    )


def execute_once():

    fix_nvidia_cdi()

    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:

        compose_data = yaml.safe_load(f)

    new_compose = deepcopy(compose_data)

    services = new_compose.get("services", {})

    changes_report = []

    for service_name, service_data in services.items():

        ports = service_data.get("ports")

        if not ports:
            continue

        updated_ports = []

        for original_port in ports:

            new_port = process_port_mapping(original_port)

            updated_ports.append(new_port)

            if new_port != original_port:

                changes_report.append(
                    {
                        "service": service_name,
                        "old": original_port,
                        "new": new_port,
                    }
                )

        service_data["ports"] = updated_ports

    if changes_report:

        with open(COMPOSE_FILE, "w", encoding="utf-8") as f:

            yaml.dump(
                new_compose,
                f,
                sort_keys=False
            )

        logging.info("\nPort mappings updated.")

    compose = find_compose()

    cmd = compose + [
        "-f",
        str(COMPOSE_FILE),
        "up",
        "-d",
        "--build",
        "--force-recreate",
    ]


    subprocess.run(
        cmd,
        check=False
    )


def main():

    logging.warning("Starting PortsCheck script...")

    while True:

        started = time.monotonic()

        try:
            execute_once()

        except Exception as ex:
            logging.error(f"[ERROR] {ex}")

        elapsed = time.monotonic() - started

        remaining = max(0, 30 - elapsed)

        time.sleep(remaining)


if __name__ == "__main__":

    main()