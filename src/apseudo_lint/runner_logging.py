"""Runner logging helpers with optional structlog support."""

from __future__ import annotations

import importlib.util
import json
import logging
from typing import Protocol


class RunnerLogger(Protocol):
    """Minimal logger protocol used by the runner."""

    def info(self, event: str, **kwargs: object) -> None: ...

    def warning(self, event: str, **kwargs: object) -> None: ...

    def error(self, event: str, **kwargs: object) -> None: ...


class _StdlibJsonLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            self._logger.addHandler(logging.NullHandler())
        self._logger.setLevel(logging.INFO)

    def info(self, event: str, **kwargs: object) -> None:
        self._emit("info", event, kwargs)

    def warning(self, event: str, **kwargs: object) -> None:
        self._emit("warning", event, kwargs)

    def error(self, event: str, **kwargs: object) -> None:
        self._emit("error", event, kwargs)

    def _emit(self, level: str, event: str, payload: dict[str, object]) -> None:
        record: dict[str, object] = {"level": level, "event": event}
        record.update(payload)
        getattr(self._logger, level)(json.dumps(record, sort_keys=True))


def get_runner_logger(name: str = "apseudo.runner") -> RunnerLogger:
    """Return a structlog logger when structlog is installed, otherwise stdlib JSON logging."""

    if importlib.util.find_spec("structlog") is not None:
        import structlog  # type: ignore[import-not-found]

        return structlog.get_logger(name)  # type: ignore[no-any-return]
    return _StdlibJsonLogger(name)
