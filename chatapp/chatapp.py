"""The main Chat app."""

import reflex as rx

from chatapp.components import chat, left_sidebar, action_bar, right_sidebar
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
                action_bar.action_bar(),
                align="center",
                spacing="4",
                width="100%",
            ),
            style=chat.chat_style,
            id="chat-container",
        ),
        right_sidebar.right_sidebar(),  # 新しいコンポーネントをここに追加
        width="100%",
        height="100vh",
        background_color="white",
        grid_template_columns="250px 2fr 1fr",  # 三列レイアウト
    )


app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="gray",
        radius="medium",
    )
)

# Add pages
app.add_page(index)
app.add_page(auth.auth, route="/auth", title="Login")
