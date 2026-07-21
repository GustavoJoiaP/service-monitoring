import argparse
import json
import logging
import os
import random
import shutil
import socket
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE_FILE = PROJECT_ROOT / "podman-compose.yaml"
DEFAULT_SERVICES_JSON = PROJECT_ROOT / "app" / "config" / "services.json"


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
        new_lines.append(line.replace("0.7.0", "0.5.0"))

    with open(cdi_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    logging.info("NVIDIA CDI fixed.")


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
            new_start = random.randint(10000, 60000 - size)
            new_end = new_start + size

            if all(is_port_available(p) for p in range(new_start, new_end + 1)):
                return f"{new_start}-{new_end}:{cont_start}-{cont_end}{protocol}"

    host_port_int = int(host_port)

    if is_port_available(host_port_int):
        return f"{host_port}:{container_port}{protocol}"

    new_port = get_random_free_port()
    return f"{new_port}:{container_port}{protocol}"


def _extract_host_port(port_mapping: str) -> int | None:
    """Extract the host port from a mapping like '8080:80' or '8080:80/tcp'."""
    mapping = port_mapping.split("/")[0]
    parts = mapping.split(":")

    if len(parts) != 2:
        return None

    host_port = parts[0]

    if "-" in host_port:
        return None

    try:
        return int(host_port)
    except ValueError:
        return None


def update_services_json(
    changes_report: list[dict],
    services_json_path: Path,
):
    """Update services.json to reflect port changes made in docker-compose.yaml.

    For TCP checks: updates the 'port' field.
    For HTTP checks: replaces the port in the 'url' field.
    """
    if not changes_report:
        return

    if not services_json_path.exists():
        logging.warning("services.json not found: %s — skipping sync.", services_json_path)
        return

    with open(services_json_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    services = config.get("services", [])
    updated = False

    for change in changes_report:
        service_name = change["service"]
        new_host_port = _extract_host_port(change["new"])

        if new_host_port is None:
            logging.warning(
                "  Cannot parse new port mapping for %s: %s",
                service_name, change["new"],
            )
            continue

        for svc in services:
            if svc.get("name") != service_name:
                continue

            check_type = svc.get("check", "container_state")

            if check_type == "tcp":
                old_port = svc.get("port")
                svc["port"] = new_host_port
                logging.info(
                    "  services.json [%s] port: %s -> %s",
                    service_name, old_port, new_host_port,
                )
                updated = True

            elif check_type == "http":
                old_url = svc.get("url", "")
                parsed = urlparse(old_url)
                new_netloc = f"{parsed.hostname}:{new_host_port}"
                new_url = urlunparse(parsed._replace(netloc=new_netloc))
                svc["url"] = new_url
                logging.info(
                    "  services.json [%s] url: %s -> %s",
                    service_name, old_url, new_url,
                )
                updated = True

            break

    if updated:
        with open(services_json_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logging.info("services.json updated successfully.")
    else:
        logging.info("No matching services found in services.json to update.")


def find_compose():
    if shutil.which("podman"):
        try:
            subprocess.run(
                ["podman", "compose", "version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return ["podman", "compose"]
        except Exception:
            pass

    if shutil.which("docker"):
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return ["docker", "compose"]
        except Exception:
            pass

    if shutil.which("docker-compose"):
        return ["docker-compose"]

    if shutil.which("podman-compose"):
        return ["podman-compose"]

    raise RuntimeError("Docker Compose or Podman Compose not found.")


def deploy(
    compose_file: Path,
    services_json: Path,
    fix_cdi: bool = False,
):
    if fix_cdi:
        fix_nvidia_cdi()

    logging.info("Reading compose file: %s", compose_file)

    with open(compose_file, "r", encoding="utf-8") as f:
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
                changes_report.append({
                    "service": service_name,
                    "old": original_port,
                    "new": new_port,
                })

        service_data["ports"] = updated_ports

    if changes_report:
        with open(compose_file, "w", encoding="utf-8") as f:
            yaml.dump(new_compose, f, sort_keys=False)

        for change in changes_report:
            logging.warning(
                "  Port conflict: %s: %s -> %s",
                change["service"],
                change["old"],
                change["new"],
            )

        update_services_json(changes_report, services_json)

    compose = find_compose()

    cmd = compose + [
        "-f",
        str(compose_file),
        "up",
        "-d",
        "--build",
        "--force-recreate",
    ]

    logging.info("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, check=False)

    if result.returncode == 0:
        logging.info("Deploy completed successfully.")
    else:
        logging.error("Deploy failed with return code %s.", result.returncode)

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Deploy services from a Docker Compose file with automatic port conflict resolution."
    )
    parser.add_argument(
        "-f", "--file",
        type=Path,
        default=DEFAULT_COMPOSE_FILE,
        help="Path to compose file (default: podman-compose.yaml)",
    )
    parser.add_argument(
        "-s", "--services-json",
        type=Path,
        default=DEFAULT_SERVICES_JSON,
        help="Path to services.json (default: app/config/services.json)",
    )
    parser.add_argument(
        "--fix-cdi",
        action="store_true",
        help="Fix NVIDIA CDI configuration before deploying",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    if not args.file.exists():
        logging.error("Compose file not found: %s", args.file)
        return 1

    return deploy(
        compose_file=args.file,
        services_json=args.services_json,
        fix_cdi=args.fix_cdi,
    )


if __name__ == "__main__":
    sys.exit(main())
