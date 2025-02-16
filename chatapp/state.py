"""State management for the chat app."""

import os
from typing import List, Tuple
import openai
from openai import AsyncOpenAI
import reflex as rx
from dotenv import load_dotenv

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

    # Conversation history
    history: List[str] = ["New Chat"]
    current_chat: str = "New Chat"

    def create_new_chat(self):
        """Create a new chat session."""
        self.chat_history = []
        self.processing = False

    def load_chat(self, chat_id: str):
        """Load a specific chat history."""
        # In a real app, this would load from a database
        self.chat_history = []
        self.current_chat = chat_id

    @rx.event
    def handle_keydown(self, keydown_character: str):
        """Handle keyboard shortcuts."""
        if (
            self.previous_keydown_character == "Control"
            and keydown_character == "Enter"
        ):
            return State.process_question
        self.previous_keydown_character = keydown_character

    @rx.event
    async def process_question(self):
        """Process the question and get a response from the API."""
        if not self.question.strip():
            return

        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        # Add to the chat history
        answer = ""
        self.chat_history.append((self.question, answer))
        # Clear the input
        question = self.question
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
                if hasattr(item.choices[0].delta, "content"):
                    if item.choices[0].delta.content is None:
                        break
                    answer += item.choices[0].delta.content
                    self.chat_history[-1] = (
                        self.chat_history[-1][0],
                        answer,
                    )
                    yield

        except Exception as e:
            self.chat_history[-1] = (self.chat_history[-1][0], f"Error: {str(e)}")

        finally:
            self.processing = False
