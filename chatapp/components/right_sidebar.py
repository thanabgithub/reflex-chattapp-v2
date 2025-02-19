import reflex as rx
from chatapp.state import State
from chatapp import style

sidebar_style = dict(
    padding="1em",
    background_color="#F9F9F9",
    border_left="1px solid #E9E9E9",
    height="100vh",  # Fixed height instead of min-height
    overflow_y="hidden",  # Prevent overflow on the container level
    color="black",
    display="flex",
    flex_direction="column",
)


def right_sidebar() -> rx.Component:
    """The right sidebar component with proper height management and scrolling."""
    return rx.box(
        rx.vstack(
            # Fixed header section
            rx.vstack(
                rx.heading("My Agent", size="4"),
                rx.divider(),
                spacing="4",
                width="100%",
            ),
            # Scrollable content section
            rx.vstack(
                # System instruction section
                rx.box(
                    rx.text("System Instruction", font_weight="bold"),
                    rx.text_area(
                        value=State.agent_system_instruction,
                        placeholder="Enter system instructions...",
                        style=style.input_style
                        | dict(
                            height="90%",
                            background_color="white",
                            min_height="3em",
                        ),
                        on_change=State.set_agent_system_instruction,
                    ),
                    width="100%",
                    height="100%",
                ),
                # Document section
                rx.box(
                    rx.text("DOCUMENT", font_weight="bold"),
                    rx.text_area(
                        value=State.agent_document,
                        placeholder="Enter DOCUMENT...",
                        style=style.input_style
                        | dict(
                            height="90%",
                            background_color="white",
                            min_height="3em",
                        ),
                        on_change=State.set_agent_document_as_dict,
                    ),
                    width="100%",
                    height="100%",
                ),
                # User prompt section
                rx.box(
                    rx.text("User prompt", font_weight="bold"),
                    rx.form(
                        rx.vstack(
                            rx.text_area(
                                value=State.agent_question,
                                placeholder="Enter user prompts...",
                                on_change=State.set_agent_question,
                                style=style.input_style
                                | dict(
                                    height="30vh",
                                    background_color="white",
                                    min_height="200px",
                                ),
                                on_key_down=State.handle_agent_action_bar_keydown,
                            ),
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
                        ),
                        style=style.form_style,
                    ),
                    width="100%",
                    position="sticky",
                    bottom="0",
                ),
                spacing="4",
                width="100%",
                height="100%",
                overflow_y="auto",
                justify="between",
            ),
            spacing="4",
            height="100%",
            width="100%",
        ),
        style=sidebar_style,
    )
