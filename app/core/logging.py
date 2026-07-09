"""Structured JSON logging + request correlation (NT-053).

Stdlib only (no extra dependency):
- `JsonFormatter` renders every log record as one JSON line (ts, level,
  logger, message + extra fields).
- `request_id_var` is a ContextVar filled by the correlation middleware;
  every log emitted while handling a request carries its `request_id`.
- `get_logger()` returns a child of the "nextarget" logger for services.

Never log secrets: no JWT, no refresh token, no Mistral key, no full
prompt (AGENTS security rules).
"""
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Attributes already handled explicitly (not repeated as extras).
_STANDARD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Render each record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Extra fields passed via `logger.info(..., extra={...})`.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the application logger with the JSON formatter.

    Idempotent: reconfigures the handler on repeated calls (uvicorn --reload).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    app_logger = logging.getLogger("nextarget")
    app_logger.handlers = [handler]
    app_logger.setLevel(level.upper())
    app_logger.propagate = False


def get_logger(name: str = "nextarget") -> logging.Logger:
    """Application logger (child loggers via 'nextarget.<module>')."""
    return logging.getLogger(name)
