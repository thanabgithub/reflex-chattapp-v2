"""Chat component for message display."""

import reflex as rx
from chatapp.state import State
from chatapp import style

chat_style = dict(
    padding="2em",
    height="100vh",
    overflow_y="auto",
    background_color="white",
    color="black",
    scroll_behavior="smooth",
)


def qa(question: str, answer: str) -> rx.Component:
    """Display a question and answer pair."""
    return rx.fragment(
        rx.box(
            rx.markdown(question, style=style.question_style),
            text_align="left",
        ),
        rx.box(
            rx.markdown(answer, style=style.answer_style),
            text_align="left",
            width="100%",
        ),
        margin_y="1em",
    )


def chat() -> rx.Component:
    """The main chat component."""
    return rx.vstack(
        rx.foreach(
            State.chat_history,
            lambda messages: qa(messages[0], messages[1]),
        ),
        align="end",
        width="100%",
        padding_bottom="5em",
    )
