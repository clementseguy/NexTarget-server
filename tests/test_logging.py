"""Structured logging + request correlation (NT-053)."""
import json
import logging

import pytest

from app.core.logging import JsonFormatter, get_logger, request_id_var
from tests.conftest import client


# ---------------------------------------------------------------------------
# JsonFormatter
# ---------------------------------------------------------------------------

def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonFormatter().format(record))


def _record(msg="hello", **extra):
    record = logging.LogRecord(
        name="nextarget.test", level=logging.INFO, pathname=__file__,
        lineno=1, msg=msg, args=(), exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


def test_formatter_outputs_valid_json_with_base_fields():
    payload = _format(_record())
    assert payload["level"] == "INFO"
    assert payload["logger"] == "nextarget.test"
    assert payload["message"] == "hello"
    assert "ts" in payload


def test_formatter_includes_extra_fields():
    payload = _format(_record(method="GET", path="/health", status=200, duration_ms=1.2))
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 1.2


def test_formatter_includes_request_id_from_contextvar():
    token = request_id_var.set("req-abc123")
    try:
        payload = _format(_record())
    finally:
        request_id_var.reset(token)
    assert payload["request_id"] == "req-abc123"


def test_formatter_without_request_context_has_no_request_id():
    payload = _format(_record())
    assert "request_id" not in payload


# ---------------------------------------------------------------------------
# Middleware de corrélation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_carries_generated_request_id():
    async with client() as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_inbound_request_id_is_propagated():
    async with client() as ac:
        r = await ac.get("/health", headers={"X-Request-ID": "gateway-42"})
    assert r.headers["X-Request-ID"] == "gateway-42"


@pytest.mark.asyncio
async def test_request_log_line_is_structured(caplog):
    # Le logger applicatif ne propage pas (handler JSON dédié) : on attache
    # directement le handler de capture de pytest.
    http_logger = get_logger("nextarget.http")
    http_logger.addHandler(caplog.handler)
    try:
        async with client() as ac:
            await ac.get("/health", headers={"X-Request-ID": "corr-1"})
    finally:
        http_logger.removeHandler(caplog.handler)

    records = [r for r in caplog.records if r.getMessage() == "request"]
    assert records, "aucune ligne de log 'request' émise"
    record = records[-1]
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status == 200
    assert record.duration_ms >= 0
