import reflex as rx
from chatapp.state import State
from chatapp import style

sidebar_style = dict(
    padding="1em",
    background_color="#F9F9F9",
    border_left="1px solid #E9E9E9",
    height="100vh",
    color="black",
)


def right_sidebar() -> rx.Component:
    """The right sidebar component with updated input styling and user prompt layout."""
    return rx.box(
        rx.vstack(
            rx.heading("My Agent", size="4"),
            rx.divider(),
            rx.text("System Instruction", font_weight="bold"),
            # Use style.input_style for system instruction with additional height/width settings
            rx.text_area(
                value=State.agent_system_instruction,
                placeholder="Enter system instructions...",
                style=style.input_style | dict(height="20vh", background_color="white"),
                on_change=State.set_agent_system_instruction,
            ),
            rx.box(
                rx.text("User prompt", font_weight="bold"),
                # Structure the user prompt similar to action_bar with a form wrapping a text_area and a model select.
                rx.form(
                    rx.vstack(
                        rx.text_area(
                            value=State.agent_question,
                            placeholder="Enter user prompts...",
                            on_change=State.set_agent_question,
                            style=style.input_style
                            | dict(height="40vh", background_color="white"),
                            on_key_down=State.handle_agent_action_bar_keydown,
                            width="100%",
                        ),
                        rx.hstack(
                            rx.select(
                                [
                                    "google/gemini-2.0-flash-001",
                                    "google/gemini-2.0-flash-thinking-exp:free",
                                ],
                                placeholder=State.agent_model,
                                disabled=State.processing,
                                on_change=State.set_agent_model,
                                style=style.select_style,
                            ),
                            rx.spacer(),
                            # Optionally, you can add a submit button here if desired.
                        ),
                        spacing="4",
                    ),
                    style=style.form_style,
                ),
                width="100%",
                background_color="#F9F9F9",
                position="sticky",
                bottom="0",
            ),
            spacing="4",
        ),
        style=sidebar_style,
    )
