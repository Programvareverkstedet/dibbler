from __future__ import annotations

import logging
import socket
import threading
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import select

from dibbler.conf import config
from dibbler.lib.syslog import get_syslog_logger

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

try:
    from dibbler._version import version
except ImportError:
    version = None

logger = get_syslog_logger()


class About(BaseModel):
    name: str
    version: str | None


class Health(BaseModel):
    status: str


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI(title="Dibbler", version=version or "unknown")

    @app.get("/")
    async def about() -> About:
        """What am I?"""
        return About(name="dibbler", version=version)

    @app.get("/health")
    def health() -> Health:
        """Do we have a db connection?"""
        with engine.connect() as connection:
            connection.execute(select(1))
        return Health(status="ok")

    return app


class Server:
    def __init__(self, app: FastAPI, address: str, port: int) -> None:
        ipv6 = ":" in address
        sock = socket.create_server(
            (address, port),
            family=socket.AF_INET6 if ipv6 else socket.AF_INET,
            dualstack_ipv6=ipv6,
        )

        # To support 0 port (automatic), we get the port from the socket.
        self.port: int = sock.getsockname()[1]
        self._uvicorn = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False))

        self._thread = threading.Thread(
            target=self._uvicorn.run,
            kwargs={"sockets": [sock]},
            name="http",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stops serving. Probably shouldnt happen ever.."""
        self._uvicorn.should_exit = True
        self._thread.join()


def _set_up_syslog() -> None:
    uvicorn_logger = logging.getLogger("uvicorn")
    if uvicorn_logger.handlers:
        return
    uvicorn_logger.addHandler(logging.NullHandler())
    for handler in logger.handlers:
        uvicorn_logger.addHandler(handler)


def start(engine: Engine) -> Server | None:
    section = config.get("http")
    if section is None:
        return None

    _set_up_syslog()

    try:
        server = Server(create_app(engine), section["address"], section["port"])
    except OSError as error:
        print(f"Not serving HTTP: {error}")
        logger.error("HTTP: not serving: %s", error)
        return None

    logger.info("HTTP: serving on %s:%s", section["address"], server.port)
    return server
