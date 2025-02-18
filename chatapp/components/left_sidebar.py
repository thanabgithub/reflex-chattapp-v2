"""Sidebar component for chat navigation."""

import reflex as rx
from chatapp.state import State

sidebar_style = dict(
    padding="1em",
    background_color="#FFFFFF",
    border_right="1px solid #E9E9E9",
    height="100vh",
    width="250px",
    color="black",
)


def chat_item(chat: str) -> rx.Component:
    """A chat item in the sidebar."""
    return rx.button(
        rx.hstack(
            rx.text(chat),
            rx.spacer(),
            rx.cond(
                chat != "New Chat",
                rx.icon(
                    "trash",
                    on_click=State.delete_chat,
                    color="red",
                ),
            ),
        ),
        on_click=lambda: State.load_chat(chat),
        width="100%",
        padding="0.5em",
        border_radius="8px",
        _hover={"background_color": "#F5F5F5"},
        style={"text_align": "left"},
    )


def sidebar() -> rx.Component:
    """The sidebar component containing chat history."""
    return rx.box(
        rx.vstack(
            rx.heading("thanaya.family", size="3"),
            rx.button(
                "新しいスレッド",
                on_click=State.create_new_chat,
                width="100%",
            ),
            rx.divider(),
            rx.heading("履歴", size="5"),
            rx.foreach(
                State.history,
                lambda item: chat_item(item),
            ),
            align="start",
            spacing="4",
            height="100%",
        ),
        style=sidebar_style,
    )
