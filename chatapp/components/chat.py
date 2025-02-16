"""Chat component for message display."""

import reflex as rx
from chatapp.state import State
from chatapp import style
from chatapp.components.action_bar import action_bar

chat_style = dict(
    padding="2em",
    height="100vh",
    overflow_y="auto",
    background_color="white",
    color="black",
    scroll_behavior="smooth",
)


def question_display(question: str, index: int) -> rx.Component:
    """Display a question with context menu for editing."""
    return rx.context_menu.root(
        rx.context_menu.trigger(
            rx.box(
                rx.markdown(question, style=style.question_style),
                text_align="left",
            ),
        ),
        rx.context_menu.content(
            rx.context_menu.item(
                "Edit Question",
                on_click=lambda: State.start_editing(index),
            ),
            style=style.context_menu_style,
        ),
    )


def editing_question_input(index: int) -> rx.Component:
    """Display the editing interface for a question."""
    return rx.box(
        rx.vstack(
            rx.form(
                rx.vstack(
                    rx.text_area(
                        value=State.question,
                        placeholder="Edit your question...",
                        on_change=State.set_question,
                        style=style.input_style,
                    ),
                    rx.hstack(
                        rx.button(
                            "Cancel",
                            on_click=State.cancel_editing,
                            style=style.button_style,
                        ),
                        rx.button(
                            "Update",
                            type="submit",
                            style=style.button_style,
                        ),
                        justify="end",
                        width="100%",
                    ),
                ),
                on_submit=State.update_question,
            ),
            width="100%",
        ),
        style=style.input_container_style,
    )


def qa(question: str, answer: str, index: int) -> rx.Component:
    """Display a question and answer pair."""
    return rx.fragment(
        rx.cond(
            State.editing_index == index,
            editing_question_input(index),
            question_display(question, index),
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
            lambda messages, index: qa(messages[0], messages[1], index),
        ),
        align="end",
        width="100%",
        padding_bottom="5em",
    )
