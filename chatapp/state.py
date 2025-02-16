"""State management for the chat app."""

import os
from typing import List, Tuple, Dict
import openai
from openai import AsyncOpenAI
import reflex as rx
from dotenv import load_dotenv
import asyncio

load_dotenv()


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

    # Conversation management
    chats: Dict[str, List[Tuple[str, str]]] = {"New Chat": []}
    current_chat: str = "New Chat"
    history: List[str] = ["New Chat"]

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
    def handle_keydown(self, keydown_character: str):
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
                yield rx.call_script(self.scroll_to_bottom_js)

        except Exception as e:
            async with self:
                self.chat_history[-1] = (question, f"Error: {str(e)}")
                self._save_current_chat()
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
