"""Logging configuration for the Doce Esperança application."""

from __future__ import annotations

import atexit
import logging
import sys
from logging import Logger
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue
from typing import Iterable, Optional


_listener: Optional[QueueListener] = None
_queue: Optional[SimpleQueue] = None


def _create_console_handler(level: int, formatter: logging.Formatter) -> logging.Handler:
    """Return a console handler that emits logs to stdout."""

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    return console_handler


def _configure_root_logger(handler: QueueHandler, level: int) -> Logger:
    """Attach the queue handler to the root logger and configure the log level."""

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    return root_logger


def _start_listener(handlers: Iterable[logging.Handler]) -> QueueListener:
    """Start a queue listener for the provided handlers."""

    if _queue is None:
        raise RuntimeError("Logging queue is not initialised.")

    listener = QueueListener(_queue, *handlers, respect_handler_level=True)
    listener.start()
    return listener


def configure_logging(app) -> None:
    """Configure application logging in a re-entrant safe manner.

    The configuration uses a queue-based logging pipeline to isolate the
    application code from the actual I/O operations performed by the handlers.
    This prevents re-entrant writes to ``sys.stderr`` that can occur when an
    exception is raised while the logging module is already writing to the same
    stream.
    """

    global _listener, _queue

    if getattr(app, "logging_configured", False):
        return

    if _listener is not None:
        app.logging_configured = True
        return

    log_level_name = app.config.get("LOG_LEVEL", "INFO")
    log_level = logging.getLevelName(log_level_name)
    if isinstance(log_level, str):
        # Fallback to INFO if ``getLevelName`` returned the level name itself
        log_level = logging.INFO

    formatter = logging.Formatter(
        fmt=app.config.get(
            "LOG_FORMAT",
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        ),
        datefmt=app.config.get("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S"),
    )

    logging.raiseExceptions = False

    _queue = SimpleQueue()
    queue_handler = QueueHandler(_queue)
    queue_handler.setLevel(log_level)

    console_handler = _create_console_handler(log_level, formatter)
    handlers = [console_handler]

    _configure_root_logger(queue_handler, log_level)

    logging.captureWarnings(True)

    _listener = _start_listener(handlers)
    atexit.register(_listener.stop)

    app.logging_configured = True


__all__ = ["configure_logging"]
