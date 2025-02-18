"""Chat component for message display."""

import reflex as rx
from chatapp.state import State, Message
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
    async def copy_and_reset(self, text: str, index: int):
        """Copy text and show check mark temporarily."""
        yield rx.set_clipboard(text)

        async with self:
            self.copied_indices[index] = True
            yield

        import asyncio

        await asyncio.sleep(1)

        async with self:
            self.copied_indices[index] = False
            yield


def editing_user_input(index: int) -> rx.Component:
    """Display the editing interface for a user message."""
    return rx.box(
        rx.vstack(
            rx.form(
                rx.vstack(
                    rx.text_area(
                        value=State.question,
                        placeholder="Edit your message...",
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
                on_submit=State.update_user_message,
            ),
            width="100%",
        ),
        style=style.input_container_style,
    )


def editing_assistant_content(index: int) -> rx.Component:
    """Display the editing interface for assistant content."""
    return rx.box(
        rx.vstack(
            rx.form(
                rx.vstack(
                    rx.text_area(
                        value=State.answer,
                        placeholder="Edit the content...",
                        on_change=State.set_answer,
                        style=style.input_style
                        | {
                            "padding_inline": 0,
                            "background_color": "transparent",
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
                on_submit=State.update_assistant_content,
            ),
            width="100%",
        ),
        style=style.input_container_style
        | dict(
            background_color="#F9F9F9",
            border="1px solid #E9E9E9",
            box_shadow="none",
            width="100%",
        ),
    )


def editing_assistant_reasoning(index: int) -> rx.Component:
    """Display the editing interface for assistant reasoning."""
    return rx.box(
        rx.vstack(
            rx.form(
                rx.vstack(
                    rx.text_area(
                        value=State.reasoning,
                        placeholder="Edit the reasoning...",
                        on_change=State.set_reasoning,
                        style=style.input_style
                        | {
                            "background_color": "transparent",
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
                on_submit=State.update_assistant_reasoning,
            ),
            width="100%",
        ),
        style=style.answer_style,
    )


def user_message(msg: Message, index: int) -> rx.Component:
    """Display a user message with context menu."""
    return rx.context_menu.root(
        rx.context_menu.trigger(
            rx.box(
                rx.box(
                    rx.markdown(msg.content, style=style.question_style),
                    width="100%",
                ),
                width="80%",
                margin_left="20%",
            ),
        ),
        rx.context_menu.content(
            rx.context_menu.item(
                "Edit Message",
                on_click=lambda: State.start_editing_user_message(index),
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


component_map = {
    "p": lambda text: rx.text.em(text),
}


def assistant_message(msg: Message, index: int) -> rx.Component:
    """Display an assistant message with reasoning and content."""
    return rx.vstack(
        # Reasoning section
        rx.cond(
            msg.reasoning != None,
            rx.context_menu.root(
                rx.context_menu.trigger(
                    rx.blockquote(
                        rx.box(
                            rx.markdown(msg.reasoning, component_map=component_map),
                            rx.box(
                                rx.cond(
                                    CopyState.copied_indices[f"{index}_reasoning"],
                                    rx.icon("check", stroke_width=1, size=15),
                                    rx.icon("copy", stroke_width=1, size=15),
                                ),
                                on_click=lambda: CopyState.copy_and_reset(
                                    msg.reasoning, f"{index}_reasoning"
                                ),
                                style=style.copy_button_style,
                                _hover={"opacity": 1},
                            ),
                            position="relative",
                        ),
                        width="100%",
                        size="1",
                    ),
                ),
                rx.context_menu.content(
                    rx.context_menu.item(
                        "Edit Reasoning",
                        on_click=lambda: State.start_editing_assistant_reasoning(index),
                    ),
                    style=style.context_menu_style,
                ),
            ),
            rx.box(),
        ),
        # Content section
        rx.cond(
            msg.content != None,
            rx.context_menu.root(
                rx.context_menu.trigger(
                    rx.box(
                        rx.box(
                            rx.markdown(msg.content, style=style.answer_style),
                            rx.box(
                                rx.cond(
                                    CopyState.copied_indices[f"{index}_content"],
                                    rx.icon("check", stroke_width=1, size=15),
                                    rx.icon("copy", stroke_width=1, size=15),
                                ),
                                on_click=lambda: CopyState.copy_and_reset(
                                    msg.content, f"{index}_content"
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
                        "Edit Content",
                        on_click=lambda: State.start_editing_assistant_content(index),
                    ),
                    rx.context_menu.separator(),
                    rx.context_menu.item(
                        "Delete Message",
                        color_scheme="red",
                        on_click=lambda: State.delete_message(index),
                    ),
                    style=style.context_menu_style,
                ),
            ),
            rx.box(),
        ),
        align="start",
        width="100%",
    )


def message(msg: Message, index: int) -> rx.Component:
    """Display a message with all editing capabilities."""
    return rx.cond(
        State.editing_user_message_index == index,
        editing_user_input(index),
        rx.cond(
            State.editing_assistant_content_index == index,
            editing_assistant_content(index),
            rx.cond(
                State.editing_assistant_reasoning_index == index,
                editing_assistant_reasoning(index),
                rx.cond(
                    msg.role == "user",
                    user_message(msg, index),
                    assistant_message(msg, index),
                ),
            ),
        ),
    )


def chat() -> rx.Component:
    """The main chat component."""
    return rx.vstack(
        rx.foreach(
            State.chat_history,
            lambda msg, index: message(msg, index),
        ),
        align="start",
        width="100%",
        padding_bottom="5em",
    )
