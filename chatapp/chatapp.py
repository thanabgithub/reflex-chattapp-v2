"""The main Chat app."""

import reflex as rx
import json
from types import SimpleNamespace
from socketio import AsyncServer
from reflex.utils import format

from chatapp.components import chat, chat_action_bar, left_sidebar, right_sidebar
from chatapp.pages import auth
from chatapp.state import State


@rx.page(on_load=State.check_auth)
def index():
    """The main app."""
    return rx.grid(
        left_sidebar.sidebar(),
        rx.box(
            rx.vstack(
                rx.cond(
                    ~chat.State.chat_history.length(),
                    rx.heading(
                        "お手伝いできることはありますか?",
                        size="8",
                        color="black",
                        text_align="center",
                        margin_top="20%",
                        margin_bottom="5%",
                    ),
                    rx.box(),
                ),
                chat.chat(),
                chat_action_bar.action_bar(),
                align="center",
                spacing="4",
                width="100%",
            ),
            style=chat.chat_style,
            id="chat-container",
        ),
        right_sidebar.right_sidebar(),
        width="100%",
        height="100vh",
        background_color="white",
        grid_template_columns="250px 2fr 1fr",
    )


# this setup require to handle long textarea input

sio = AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=("*"),
    cors_credentials=True,
    max_http_buffer_size=50000000000,
    ping_interval=120,
    ping_timeout=240,
    json=SimpleNamespace(
        dumps=staticmethod(format.json_dumps),
        loads=staticmethod(json.loads),
    ),
)

app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="gray",
        radius="medium",
    ),
    sio=sio,
)


# Configure WebSocket settings
app.api.websocket_config = {
    "max_message_size": 100 * 1024 * 1024 * 1024,  # 100 GB
    "ping_interval": 30,  # seconds
    "ping_timeout": 60,  # seconds
    "close_timeout": 60,  # seconds
    "max_queue_size": 32,
}

# Configure HTTP server settings
app.api.http_config = {
    "max_request_body_size": 100 * 1024 * 1024 * 1024,  # 100 GB
    "keepalive_timeout": 60,  # seconds
    "read_timeout": 60,  # seconds
    "write_timeout": 60,  # seconds
}

# Add pages
app.add_page(index)
app.add_page(auth.auth, route="/auth", title="Login")
