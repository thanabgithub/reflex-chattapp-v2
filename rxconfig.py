import reflex as rx
from enum import Enum
from reflex.state import StateManager


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


from reflex import constants

config = rx.Config(
    app_name="chatapp",
    loglevel=LogLevel.DEBUG,
    env=rx.Env.DEV,
    state_manager_mode=constants.StateManagerMode.MEMORY,
    # env=rx.Env.PROD,
    # frontend_port=80,
    # backend_host="152.42.211.214",
    # api_url="http://152.42.211.214:8000",
    # deploy_url="http://152.42.211.214:80",
)
