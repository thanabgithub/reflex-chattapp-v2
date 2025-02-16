"""Action bar component for user input."""

import reflex as rx
from chatapp.state import State
from chatapp import style


def action_bar() -> rx.Component:
    """The action bar component for user input."""
    return rx.cond(
        # Update the condition to check both editing states
        (State.editing_question_index != None) | (State.editing_answer_index != None),
        rx.fragment(),
        rx.box(
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
                                        "aion-labs/aion-1.0",
                                        "openai/gpt-4o-mini",
                                        "google/gemini-2.0-flash-thinking-exp:free",
                                    ],
                                    placeholder=State.model,
                                    disabled=State.processing,
                                    on_change=State.set_model,
                                    style=style.select_style,
                                ),
                            ),
                            rx.spacer(),
                            rx.cond(
                                State.processing,
                                rx.button(
                                    rx.icon("circle-stop", color="crimson"),
                                    on_click=State.stop_process,
                                    style=dict(
                                        background_color="transparent",
                                        border="0px solid #E9E9E9",
                                        color="black",
                                    ),
                                ),
                                rx.button(
                                    rx.icon("arrow-right"),
                                    on_click=State.process_question,
                                    style=dict(
                                        background_color="transparent",
                                        border="0px solid #E9E9E9",
                                        color="black",
                                    ),
                                ),
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
        ),
    )
