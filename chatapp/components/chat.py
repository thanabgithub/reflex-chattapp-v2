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


class CopyState(rx.State):
    """State for managing copy button icons."""

    copied_indices: dict[int, bool] = {}

    @rx.event(background=True)
    async def copy_and_reset(self, answer: str, index: int):
        """Copy text and show check mark temporarily."""
        # First yield the clipboard event
        yield rx.set_clipboard(answer)

        # Then update state within context manager
        async with self:
            self.copied_indices[index] = True
            yield

        # Wait 1 second
        import asyncio

        await asyncio.sleep(1)

        # Reset back to copy icon within context manager
        async with self:
            self.copied_indices[index] = False
            yield


def editing_answer_input(index: int) -> rx.Component:
    """Display the editing interface for an answer."""
    # Create a style that matches the answer container style
    answer_edit_container_style = style.input_container_style.copy()
    answer_edit_container_style.update(
        {
            "background_color": "#F9F9F9",  # Match answer background color
            "border": "1px solid #E9E9E9",  # Match answer border
            "box_shadow": "none",  # Match answer box shadow
        }
    )

    return rx.box(
        rx.vstack(
            rx.form(
                rx.vstack(
                    rx.text_area(
                        value=State.answer,
                        placeholder="Edit the answer...",
                        on_change=State.set_answer,
                        style=style.input_style
                        | {
                            "background_color": "transparent",  # Keep textarea background transparent
                        },
                    ),
                    rx.hstack(
                        rx.spacer(),
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
                on_submit=State.update_answer,
            ),
            width="100%",
        ),
        style=answer_edit_container_style,
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
                        rx.spacer(),
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


def message_with_context_menu(question: str, answer: str, index: int) -> rx.Component:
    """Display a message pair with a context menu for editing and deleting."""
    return rx.context_menu.root(
        rx.context_menu.trigger(
            rx.box(
                # Question container
                rx.box(
                    rx.box(
                        rx.markdown(question, style=style.question_style),
                        width="100%",
                    ),
                    width="80%",
                    margin_left="20%",
                ),
                # Answer container with its own context menu
                rx.context_menu.root(
                    rx.context_menu.trigger(
                        rx.box(
                            rx.box(
                                rx.markdown(answer, style=style.answer_style),
                                rx.box(
                                    rx.cond(
                                        CopyState.copied_indices[index],
                                        rx.icon("check", stroke_width=1, size=15),
                                        rx.icon("copy", stroke_width=1, size=15),
                                    ),
                                    on_click=lambda: CopyState.copy_and_reset(
                                        answer, index
                                    ),
                                    style=style.copy_button_style,
                                    _hover={"opacity": 1},
                                ),
                                position="relative",
                            ),
                            width="100%",
                        ),
                    ),
                    rx.context_menu.content(
                        rx.context_menu.item(
                            "Edit Answer",
                            on_click=lambda: State.start_editing_answer(index),
                        ),
                        style=style.context_menu_style,
                    ),
                ),
                margin_y="1em",
                width="100%",
            ),
        ),
        rx.context_menu.content(
            rx.context_menu.item(
                "Edit Question",
                on_click=lambda: State.start_editing_question(index),
            ),
            rx.context_menu.separator(),
            rx.context_menu.item(
                "Delete Message",
                color_scheme="red",
                on_click=lambda: State.delete_message(index),
            ),
            style=style.context_menu_style,
        ),
    )


def qa(question: str, answer: str, index: int) -> rx.Component:
    """Display a question and answer pair."""
    return rx.cond(
        State.editing_question_index == index,
        editing_question_input(index),
        rx.cond(
            State.editing_answer_index == index,
            editing_answer_input(index),
            message_with_context_menu(question, answer, index),
        ),
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
