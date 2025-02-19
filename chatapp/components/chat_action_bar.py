"""Action bar component for user input."""

import reflex as rx
from chatapp.state import State
from chatapp import style


class ActionBarState(rx.State):
    """State for managing action bar behavior."""

    @rx.event
    def auto_resize_textarea(self):
        """Auto resize the textarea based on content."""
        return rx.call_script(
            """
            function autoResizeTextArea(element) {
                if (!element) return;
                
                // Get the computed styles
                const computed = window.getComputedStyle(element);
                
                // Create a hidden div to measure the height
                const hiddenDiv = document.createElement('div');
                hiddenDiv.style.cssText = `
                    width: ${computed.width};
                    padding: ${computed.padding};
                    border: ${computed.border};
                    font: ${computed.font};
                    letter-spacing: ${computed.letterSpacing};
                    position: absolute;
                    top: -9999px;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    white-space: pre-wrap;
                `;
                
                document.body.appendChild(hiddenDiv);
                hiddenDiv.textContent = element.value;
                
                // Calculate target height
                const maxHeight = window.innerHeight * 0.6;
                const targetHeight = Math.min(hiddenDiv.offsetHeight, maxHeight);
                
                // Clean up
                document.body.removeChild(hiddenDiv);
                
                // Only update if the height would actually change
                const currentHeight = element.getBoundingClientRect().height;
                if (Math.abs(currentHeight - targetHeight) > 1) {
                    element.style.height = targetHeight + 'px';
                }
            }
            autoResizeTextArea(document.getElementById('input-textarea--action-bar'));
            """
        )


def action_bar() -> rx.Component:
    """The action bar component for user input."""
    return rx.cond(
        # Check editing states as before.
        (State.editing_user_message_index != None)
        | (State.editing_assistant_content_index != None)
        | (State.editing_assistant_reasoning_index != None),
        rx.fragment(),
        rx.box(
            rx.vstack(
                rx.form(
                    rx.vstack(
                        rx.text_area(
                            id="input-textarea--action-bar",
                            value=State.question,
                            placeholder="何でも質問してください...",
                            on_change=[
                                State.set_question,
                            ],
                            style=style.input_style,
                            on_key_down=[
                                State.handle_action_bar_keydown,
                                ActionBarState.auto_resize_textarea,
                            ],
                        ),
                        rx.hstack(
                            rx.hstack(
                                rx.select(
                                    [
                                        "aion-labs/aion-1.0",
                                        "mistralai/codestral-2501",
                                        "google/gemini-2.0-flash-thinking-exp:free",
                                        "deepseek/deepseek-r1",
                                        "openai/gpt-4o-mini",
                                    ],
                                    placeholder=State.model,
                                    disabled=State.processing,
                                    on_change=State.set_model,
                                    style=style.select_style,
                                    height="100%",
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
                                    type="submit",
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
