"""The main Chat app."""

import reflex as rx

from chatapp.components import chat, sidebar, action_bar


def index() -> rx.Component:
    """The main app."""
    return rx.grid(
        sidebar.sidebar(),
        rx.box(
            rx.vstack(
                rx.cond(
                    ~chat.State.chat_history.length(),
                    rx.heading(
                        "お手伝いできることはありますか?",
                        size="8",
                        color="black",
                        text_align="center",
                        margin_top="25%",
                        margin_bottom="5%",
                    ),
                    rx.box(),
                ),
                chat.chat(),
                action_bar.action_bar(),
                align="center",
                spacing="4",
                width="100%",
            ),
            style=chat.chat_style,
            id="chat-container",
        ),
        rx.box(),  # Empty box for third column
        width="100%",
        height="100vh",
        background_color="white",
        grid_template_columns="250px 2fr 1fr",  # Three columns layout
    )


app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="gray",
        radius="medium",
    )
)
app.add_page(index)
