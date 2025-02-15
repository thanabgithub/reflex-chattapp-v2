import reflex as rx

from chatapp import style
from chatapp.state import State


def qa(question: str, answer: str) -> rx.Component:
    return rx.box(
        rx.box(
            rx.text(question, style=style.question_style),
            text_align="right",
        ),
        rx.box(
            rx.text(answer, style=style.answer_style),
            text_align="left",
        ),
        margin_y="1em",
    )


def chat() -> rx.Component:
    return rx.box(
        rx.foreach(
            State.chat_history,
            lambda messages: qa(messages[0], messages[1]),
        )
    )


def action_bar() -> rx.Component:
    return rx.hstack(
        rx.input(
            value=State.question,
            placeholder="何でも質問してください...",
            on_change=State.set_question,
            style=style.input_style,
        ),
        rx.select(
            ["GPT-4", "GPT-3.5"],
            placeholder="モデル",
            on_change=State.set_model,
            style=style.select_style,
        ),
        rx.button(
            "送信",
            on_click=State.answer,
            style=style.button_style,
        ),
    )


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("thanaya.family", size="3"),
            rx.button("新しいスレッド", on_click=State.new_thread),
            rx.heading("履歴", size="5"),
            rx.foreach(
                State.history,
                lambda item: rx.button(
                    item,
                    on_click=lambda: State.load_chat(item),
                    width="100%",
                ),
            ),
            align="start",
            spacing="4",
        ),
        style=style.sidebar_style,
    )


def index() -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            rx.vstack(
                rx.heading("お手伝いできることはありますか?", size="3"),
                chat(),
                action_bar(),
                align="start",
                spacing="4",
                width="100%",
            ),
            style=style.chat_style,
        ),
        width="100%",
        height="100vh",
    )


app = rx.App()
app.add_page(index)
