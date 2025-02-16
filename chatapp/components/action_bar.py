"""Action bar component for user input."""

import reflex as rx
from chatapp.state import State
from chatapp import style
from chatapp.components.loading_icon import loading_icon


def action_bar() -> rx.Component:
    """The action bar component for user input."""
    return rx.box(
        rx.vstack(
            rx.form(
                rx.vstack(
                    rx.text_area(
                        value=State.question,
                        placeholder="何でも質問してください...",
                        on_change=State.set_question,
                        style=style.input_style,
                        on_key_down=State.handle_keydown,
                    ),
                    rx.hstack(
                        rx.hstack(
                            rx.select(
                                [
                                    "deepseek/deepseek-r1",
                                    "openai/gpt-4o-mini",
                                    "google/gemini-2.0-flash-thinking-exp:free",
                                ],
                                placeholder="deepseek/deepseek-r1",
                                on_change=State.set_model,
                                style=style.select_style,
                            ),
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.cond(
                                State.processing,
                                loading_icon(),
                                rx.icon("arrow-right"),
                            ),
                            on_click=State.process_question,
                            style=style.button_style,
                        ),
                        style=style.controls_style,
                    ),
                ),
                on_submit=State.process_question,
                style=style.form_style,
            ),
            width="100%",
        ),
        style=style.input_container_style,
        position="sticky",
        bottom="0",
    )
