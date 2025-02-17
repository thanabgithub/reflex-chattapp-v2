"""State management for the chat app."""

import os
from typing import *
from openai import AsyncOpenAI
import reflex as rx
from dotenv import load_dotenv

load_dotenv()

ENABLE_AUTO_SCROLL_DOWN = False


class QA(rx.Base):
    """A question and answer pair."""

    question: str
    answer: str


class State(rx.State):
    """The app state."""

    # Chat state
    chat_history: List[Tuple[str, str]] = []
    question: str = ""
    model: str = "deepseek/deepseek-r1"
    previous_keydown_character: str = ""

    # UI state
    processing: bool = False
    modal_open: bool = False

    # Editing
    editing_question: Optional[str] = None
    editing_index: Optional[int] = None
    editing_question_index: Optional[int] = None
    editing_answer_index: Optional[int] = None
    answer: str = ""

    # Conversation management
    chats: Dict[str, List[Tuple[str, str]]] = {"New Chat": []}
    current_chat: str = "New Chat"
    history: List[str] = ["New Chat"]

    # --- New authentication fields ---
    authenticated: bool = False
    # Set your desired passcode here (for example, "1234")
    passcode: str = os.getenv("PASSCODE")
    # Temporary field for the passcode provided by the user
    passcode_input: str = ""

    def check_auth(self):
        """Redirects to the auth page if the user is not authenticated."""
        if not self.authenticated:
            return rx.redirect("/auth")

    @rx.event
    def set_passcode_input(self, value: str):
        """Sets the passcode input from the form."""
        self.passcode_input = value

    @rx.event
    def authenticate(self):
        """Verifies the passcode and, if correct, sets the auth flag and cookie."""
        if self.passcode_input == self.passcode:
            self.authenticated = True
            self.passcode_input = ""  # Clear the temporary input
            # Set a cookie for 60 minutes using a JS call.
            # The cookie here is named "auth" with value "true" and expires in 3600 seconds.
            yield rx.call_script("document.cookie = 'auth=true; max-age=3600; path=/'")
            yield rx.toast.success(
                "Valid passcode",
            )
            # Then redirect to the main page.
            return rx.redirect("/")
        else:
            # Notify the user of a failed attempt.
            return rx.toast.error("Invalid passcode")

    def create_new_chat(self):
        """Create a new chat session."""
        new_chat_id = f"Chat {len(self.chats) + 1}"
        self.chats[new_chat_id] = []
        self.history.append(new_chat_id)
        self.current_chat = new_chat_id
        self.chat_history = self.chats[self.current_chat]
        self.processing = False

    def load_chat(self, chat_id: str):
        """Load a specific chat history."""
        if chat_id in self.chats:
            self.current_chat = chat_id
            self.chat_history = self.chats[chat_id]

    def delete_chat(self):
        """Delete the current chat."""
        if self.current_chat != "New Chat":
            del self.chats[self.current_chat]
            self.history.remove(self.current_chat)
            # Set current chat to "New Chat" or the last chat in history
            self.current_chat = "New Chat"
            self.chat_history = self.chats[self.current_chat]

    def _save_current_chat(self):
        """Save current chat history to chats dictionary."""
        if self.current_chat in self.chats:
            self.chats[self.current_chat] = self.chat_history

    @rx.event
    def handle_action_bar_keydown(self, keydown_character: str):
        """Handle keyboard shortcuts."""
        if (
            self.previous_keydown_character == "Control"
            and keydown_character == "Enter"
        ):
            return State.process_question
        self.previous_keydown_character = keydown_character

    @rx.event(background=True)
    async def stop_process(self):
        """Stop the current processing."""
        async with self:
            self.processing = False

    def format_messages(self, question: str) -> List[Dict[str, str]]:
        """Format chat history and current question into messages for the API."""
        messages = []

        # Add chat history
        for q, a in self.chat_history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        # Add the current question
        messages.append({"role": "user", "content": question})

        return messages

    @rx.event(background=True)
    async def process_question(self):
        """Process the question and get a response from the API."""
        if not self.question.strip():
            return

        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        # Store question and clear input
        question = self.question
        answer = ""

        async with self:
            # Add to the chat history
            self.chat_history.append((question, answer))
            self._save_current_chat()  # Save to chats dictionary
            # Clear the input
            self.question = ""
            self.processing = True
        yield

        try:
            # Get formatted conversation history including current question
            messages = self.format_messages(question)

            session = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
            )

            async for item in session:
                async with self:
                    if not self.processing:
                        await session.close()
                        break

                    if hasattr(item.choices[0].delta, "content"):
                        if item.choices[0].delta.content is None:
                            break
                        answer += item.choices[0].delta.content
                        self.chat_history[-1] = (question, answer)
                        self._save_current_chat()
                if ENABLE_AUTO_SCROLL_DOWN:
                    yield rx.call_script(self.scroll_to_bottom_js)

        except Exception as e:
            async with self:
                self.chat_history[-1] = (question, f"Error: {str(e)}")
                self._save_current_chat()
            if ENABLE_AUTO_SCROLL_DOWN:
                yield rx.call_script(self.scroll_to_bottom_js)
        finally:
            async with self:
                self.processing = False
            yield
        """Process the question and get a response from the API."""
        if not self.question.strip():
            return

        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        # Store question and clear input
        question = self.question
        answer = ""

        async with self:
            # Add to the chat history
            self.chat_history.append((question, answer))
            self._save_current_chat()  # Save to chats dictionary
            # Clear the input
            self.question = ""
            self.processing = True
        yield

        try:
            session = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": question}],
                stream=True,
            )

            async for item in session:
                async with self:
                    if not self.processing:
                        session.close()
                        break

                    if hasattr(item.choices[0].delta, "content"):
                        if item.choices[0].delta.content is None:
                            break
                        answer += item.choices[0].delta.content
                        self.chat_history[-1] = (question, answer)
                        self._save_current_chat()
                if ENABLE_AUTO_SCROLL_DOWN:
                    yield rx.call_script(self.scroll_to_bottom_js)

        except Exception as e:
            async with self:
                self.chat_history[-1] = (question, f"Error: {str(e)}")
                self._save_current_chat()
            if ENABLE_AUTO_SCROLL_DOWN:
                yield rx.call_script(self.scroll_to_bottom_js)
        finally:
            async with self:
                self.processing = False
            yield

    scroll_to_bottom_js = """
const chatContainer = document.getElementById('chat-container');
if (chatContainer) {
    // Get the current scroll position and container dimensions
    const currentScroll = chatContainer.scrollTop;
    const scrollHeight = chatContainer.scrollHeight;
    const clientHeight = chatContainer.clientHeight;

    // Calculate the maximum scroll position
    const maxScroll = scrollHeight - clientHeight;

    // Scroll to bottom and log any issues
    try {
        chatContainer.scrollTop = maxScroll;
        console.log('Scrolled to bottom:', maxScroll);
    } catch (error) {
        console.error('Error scrolling:', error);
    }
} else {
    console.warn('Chat container not found');
};
"""

    def start_editing(self, index: int):
        """Start editing a specific question."""
        self.editing_index = index
        self.editing_question = self.chat_history[index][0]
        self.question = self.chat_history[index][0]

    def cancel_editing(self):
        """Cancel editing mode."""
        self.editing_index = None
        self.editing_question = None
        self.question = ""

    @rx.event(background=True)
    async def update_question(self):
        """Update an existing question with new text."""
        if (
            self.editing_question_index is None or not self.question.strip()
        ):  # Changed from editing_index
            return

        # Store values before clearing state
        async with self:
            new_question = self.question
            current_index = self.editing_question_index  # Changed from editing_index
            original_answer = self.chat_history[current_index][1]

            # Reset editing state
            self.editing_question_index = None  # Changed from editing_index
            self.question = ""

            # Update the chat history
            self.chat_history[current_index] = (new_question, "")
            self._save_current_chat()
            self.processing = True

        yield

        try:
            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            )

            messages = self.format_messages(new_question)
            session = await client.chat.completions.create(
                model=self.model,
                messages=messages[: 2 * current_index + 1],
                stream=True,
            )

            answer = ""
            async for item in session:
                async with self:
                    if not self.processing:
                        session.close()
                        break
                    if hasattr(item.choices[0].delta, "content"):
                        if item.choices[0].delta.content is None:
                            break
                        answer += item.choices[0].delta.content
                        self.chat_history[current_index] = (new_question, answer)
                        self._save_current_chat()
                if ENABLE_AUTO_SCROLL_DOWN:
                    yield rx.call_script(self.scroll_to_bottom_js)

        except Exception as e:
            async with self:
                self.chat_history[current_index] = (new_question, f"Error: {str(e)}")
                self._save_current_chat()
            if ENABLE_AUTO_SCROLL_DOWN:
                yield rx.call_script(self.scroll_to_bottom_js)
        finally:
            async with self:
                self.processing = False
            yield

    def delete_message(self, index: int):
        """Delete a specific message from chat history."""
        # Remove the message at the specified index
        self.chat_history.pop(index)
        # Save the updated chat history
        self._save_current_chat()

    def start_editing_question(self, index: int):
        """Start editing a specific question."""
        self.editing_question_index = index
        self.question = self.chat_history[index][0]
        self.editing_answer_index = None

    def start_editing_answer(self, index: int):
        """Start editing a specific answer."""
        self.editing_answer_index = index
        self.answer = self.chat_history[index][1]
        self.editing_question_index = None

    def cancel_editing(self):
        """Cancel editing mode."""
        self.editing_question_index = None
        self.editing_answer_index = None
        self.question = ""
        self.answer = ""

    def update_answer(self):
        """Update an existing answer with new text."""
        if self.editing_answer_index is None or not self.answer.strip():
            return

        # Update the answer in chat history
        index = self.editing_answer_index
        question = self.chat_history[index][0]
        new_answer = self.answer

        # Update the chat history
        self.chat_history[index] = (question, new_answer)
        self._save_current_chat()

        # Reset editing state
        self.editing_answer_index = None
        self.answer = ""
