import reflex as rx
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


config = rx.Config(
    app_name="chatapp",
    tailwind={},
    env=rx.Env.DEV,
    loglevel=LogLevel.DEBUG,
    frontend_port=3000,
    backend_port=8000,
)
