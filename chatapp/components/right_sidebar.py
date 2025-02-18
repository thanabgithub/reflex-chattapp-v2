"""Right sidebar component for additional features."""

import reflex as rx

sidebar_style = dict(
    padding="1em",
    background_color="#F9F9F9",
    border_left="1px solid #E9E9E9",
    height="100vh",
    color="black",
)


def right_sidebar() -> rx.Component:
    """The right sidebar component."""
    return rx.box(
        rx.vstack(
            rx.heading("My Agent", size="4"),
            rx.divider(),
            rx.text("System Instruction", font_weight="bold"),
            rx.text_area(
                placeholder="Enter system instructions...",
                height="50vh",
                width="100%",
            ),
            rx.text("User prompt", font_weight="bold"),
            rx.text_area(
                placeholder="Enter user prompts...",
                width="100%",
            ),
            spacing="4",
        ),
        style=sidebar_style,
    )
