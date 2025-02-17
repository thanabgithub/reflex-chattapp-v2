import reflex as rx
from chatapp.state import State


def auth():
    """A simple passcode authentication page."""
    return rx.center(
        rx.vstack(
            rx.heading("Enter Passcode", size="4"),
            rx.form(
                rx.input(
                    placeholder="Passcode",
                    value=State.passcode_input,
                    on_change=State.set_passcode_input,
                    type="password",  # Hide the passcode characters
                ),
                rx.button("Login", type="submit", style=dict(margin_top="0.5em")),
                on_submit=State.authenticate,
                reset_on_submit=True,
            ),
            spacing="1",
        ),
        style=dict(margin_top="10%"),
    )
