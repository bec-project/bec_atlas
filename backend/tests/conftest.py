import contextlib
import os
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from pytest_docker.plugin import DockerComposeExecutor, Services

from bec_atlas.main import AtlasApp


def pytest_addoption(parser):
    parser.addoption(
        "--skip-docker",
        action="store_true",
        default=False,
        help="Skip spinning up docker containers",
    )


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    test_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_directory, "docker-compose.yml")


@pytest.fixture(scope="session")
def docker_compose_project_name() -> str:
    """Generate a project name using the current process PID. Override this
    fixture in your tests if you need a particular project name."""

    return "pytest_9070_atlas"


@contextlib.contextmanager
def get_docker_services(
    docker_compose_command: str,
    docker_compose_file: list[str] | str,
    docker_compose_project_name: str,
    docker_setup: list[str] | str,
    docker_cleanup: list[str] | str,
) -> Iterator[Services]:
    docker_compose = DockerComposeExecutor(
        docker_compose_command, docker_compose_file, docker_compose_project_name
    )

    try:
        if docker_cleanup:
            # Maintain backwards compatibility with the string format.
            if isinstance(docker_cleanup, str):
                docker_cleanup = [docker_cleanup]
            for command in docker_cleanup:
                docker_compose.execute(command)
    except Exception:
        pass

    # setup containers.
    if docker_setup:
        # Maintain backwards compatibility with the string format.
        if isinstance(docker_setup, str):
            docker_setup = [docker_setup]
        for command in docker_setup:
            docker_compose.execute(command)

    try:
        # Let test(s) run.
        yield Services(docker_compose)
    finally:
        # Clean up.
        if docker_cleanup:
            # Maintain backwards compatibility with the string format.
            if isinstance(docker_cleanup, str):
                docker_cleanup = [docker_cleanup]
            for command in docker_cleanup:
                docker_compose.execute(command)


@pytest.fixture(scope="session")
def docker_services(
    docker_compose_command: str,
    docker_compose_file: list[str] | str,
    docker_compose_project_name: str,
    docker_setup: str,
    docker_cleanup: str,
    request,
) -> Iterator[Services]:
    """Start all services from a docker compose file (`docker-compose up`).
    After test are finished, shutdown all services (`docker-compose down`)."""

    if request.config.getoption("--skip-docker"):
        yield
        return

    with get_docker_services(
        docker_compose_command,
        docker_compose_file,
        docker_compose_project_name,
        docker_setup,
        docker_cleanup,
    ) as docker_service:
        yield docker_service


@pytest.fixture(scope="session")
def redis_container(docker_ip, docker_services):
    host = docker_ip
    if os.path.exists("/.dockerenv"):
        host = "redis"
    if docker_services is None:
        port = 6380
    else:
        port = docker_services.port_for("redis", 6379)

    return "localhost", port


@pytest.fixture(scope="session")
def mongo_container(docker_ip, docker_services):
    host = docker_ip
    if os.path.exists("/.dockerenv"):
        host = "mongo"
    if docker_services is None:
        port = 27017
    else:
        port = docker_services.port_for("mongodb", 27017)

    return "localhost", port


@pytest.fixture(scope="session")
def backend(redis_container, mongo_container):
    redis_host, redis_port = redis_container
    mongo_host, mongo_port = mongo_container
    config = {
        "redis": {
            "host": redis_host,
            "port": redis_port,
            "username": "ingestor",
            "password": "ingestor",
        },
        "mongodb": {"host": mongo_host, "port": mongo_port},
    }

    app = AtlasApp(config)

    with TestClient(app.app) as _client:
        yield _client, app
