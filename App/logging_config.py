"""Centralized logging configuration for the Flask application."""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time
from typing import Any, Dict

from flask import Flask

_LOG_RECORD_RESERVED = {
    'args',
    'asctime',
    'created',
    'exc_info',
    'exc_text',
    'filename',
    'funcName',
    'levelname',
    'levelno',
    'lineno',
    'module',
    'msecs',
    'message',
    'msg',
    'name',
    'pathname',
    'process',
    'processName',
    'relativeCreated',
    'stack_info',
    'thread',
    'threadName',
}


def _extract_extras(record: logging.LogRecord) -> Dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _LOG_RECORD_RESERVED and not key.startswith('_')
    }


class JsonLogFormatter(logging.Formatter):
    """Formatter that renders log records in JSON."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name
        self._host = socket.gethostname()

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            'timestamp': int(record.created * 1000),
            'logger': record.name,
            'msg': record.getMessage(),
            'host': self._host,
            'service': self._service,
            'status': record.levelname.lower(),
            'thread': record.threadName,
        }

        extras = _extract_extras(record)
        if extras:
            payload.update(extras)

        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class HybridDevFormatter(logging.Formatter):
    """Human-friendly formatter that still exposes structured attributes."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name
        self._host = socket.gethostname()

    def format(self, record: logging.LogRecord) -> str:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        header = f"[{timestamp}] | {record.levelname} | [{record.name}] {record.getMessage()}"

        extras = _extract_extras(record)
        extras.update({'host': self._host, 'service': self._service, 'thread': record.threadName})

        structured = json.dumps(extras, ensure_ascii=False, indent=2) if extras else '{}'
        if record.exc_info:
            structured_lines = [structured, self.formatException(record.exc_info)]
            structured = '\n'.join(structured_lines)
        return f"{header}\n{structured}"


def configure_logging(app: Flask) -> None:
    """Configure logging for the application based on environment."""
    service_name = app.config.get('SERVICE_NAME', 'info3604-help-desk-rostering')
    log_level = app.config.get('LOG_LEVEL', os.environ.get('LOG_LEVEL', 'INFO')).upper()
    env = app.config.get('ENV', os.environ.get('ENV', 'development'))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in tuple(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if env in {'production', 'staging'}:
        formatter: logging.Formatter = JsonLogFormatter(service_name)
    else:
        formatter = HybridDevFormatter(service_name)
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    logging.captureWarnings(True)

    root_logger.info(
        'Logging initialized',
        extra={
            'event': 'logging_initialized',
            'service': service_name,
            'environment': env,
            'level': log_level,
        },
    )

