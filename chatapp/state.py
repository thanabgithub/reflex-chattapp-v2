"""State management for the chat app."""

import os
from typing import *
from openai import AsyncOpenAI
import reflex as rx
from dotenv import load_dotenv

load_dotenv()

ENABLE_AUTO_SCROLL_DOWN = False

import json
from typing import *
import aiohttp
import asyncio
from asyncio import Queue
from dataclasses import dataclass


@dataclass
class StreamChunk:
    content: Optional[str] = None
    reasoning: Optional[str] = None
    is_done: bool = False
    error: Optional[str] = None


class StreamProcessor:
    """Improved stream processor that handles long responses and reasoning tokens."""

    def __init__(self, response, session):
        self.response = response
        self.session = session
        self.buffer = ""
        self._closed = False
        self._done = False
        self._complete_messages = []
        self._current_message = {"content": "", "reasoning": ""}
        self._lock = asyncio.Lock()

    async def start(self):
        """Start processing the stream."""
        return self

    async def _process_line(self, line):
        """Process a single line of SSE data."""
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                self._done = True
                return True

            try:
                data_obj = json.loads(data)
                chunk = ChatCompletionChunk(data_obj)

                if chunk.choices:
                    choice = chunk.choices[0]
                    delta = choice.delta

                    # Store both content and reasoning from this chunk
                    if delta.content is not None:
                        self._current_message["content"] += delta.content
                    if delta.reasoning is not None:
                        self._current_message["reasoning"] += delta.reasoning

                    # Create a StreamChunk with all available data
                    return StreamChunk(
                        content=delta.content, reasoning=delta.reasoning, is_done=False
                    )

            except json.JSONDecodeError:
                pass
        return None

    async def _read_chunk(self):
        """Read a chunk from the response and process it."""
        try:
            chunk = await self.response.content.read(1024)
            if not chunk:
                return None
            return chunk.decode("utf-8")
        except Exception as e:
            return None

    async def __aiter__(self):
        """Iterate over the stream chunks with improved error handling."""
        while not self._done and not self._closed:
            try:
                chunk = await self._read_chunk()
                if not chunk:
                    break

                self.buffer += chunk

                while True:
                    line_end = self.buffer.find("\n")
                    if line_end == -1:
                        break

                    line = self.buffer[:line_end].strip()
                    self.buffer = self.buffer[line_end + 1 :]

                    result = await self._process_line(line)
                    if result:
                        if result.is_done:
                            self._done = True
                            break
                        if result.content is not None or result.reasoning is not None:
                            yield result

            except Exception as e:
                # Log error if needed
                break

        # Final cleanup
        if not self._closed:
            await self.close()

    async def close(self):
        """Close the stream processor and clean up resources."""
        if not self._closed:
            self._closed = True
            if self.response:
                await self.response.release()
            if self.session:
                await self.session.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class ChatCompletionChunk:
    def __init__(self, chunk_data: Dict[str, Any]):
        self.choices = [Choice(choice) for choice in chunk_data.get("choices", [])]
        self.id = chunk_data.get("id")
        self.model = chunk_data.get("model")
        self.created = chunk_data.get("created")


class Choice:
    def __init__(self, choice_data: Dict[str, Any]):
        self.delta = Delta(choice_data.get("delta", {}))
        self.index = choice_data.get("index")
        self.finish_reason = choice_data.get("finish_reason")


class Delta:
    def __init__(self, delta_data: Dict[str, Any]):
        self.content = delta_data.get("content")
        self.role = delta_data.get("role")
        self.reasoning = delta_data.get("reasoning")


class AsyncOpenRouterAI:
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.chat = self.Chat(self)

    class Chat:
        def __init__(self, client):
            self.client = client
            self.completions = self

        async def create(
            self,
            model: str,
            messages: List[Dict[str, str]],
            stream: bool = False,
            include_reasoning: bool = False,
            **kwargs,
        ) -> Union[ChatCompletionChunk, StreamProcessor]:
            """Create a chat completion with queue-based streaming."""
            url = f"{self.client.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.client.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "include_reasoning": include_reasoning,
                **kwargs,
            }

            session = aiohttp.ClientSession()
            try:
                response = await session.post(url, headers=headers, json=payload)

                if not stream:
                    try:
                        data = await response.json()
                        return ChatCompletionChunk(data)
                    finally:
                        await session.close()

                return await StreamProcessor(response, session).start()

            except Exception as e:
                await session.close()
                raise


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

    # Authentication state
    authenticated: bool = False
    auth_token: str = rx.Cookie("")
    passcode: str = os.getenv("PASSCODE")
    passcode_input: str = ""

    @rx.event
    def check_auth(self):
        """Checks authentication status from cookie and redirects if not authenticated."""
        # Read authentication status from cookie
        self.authenticated = self.auth_token == "is_login"

        if not self.authenticated:
            return rx.redirect("/auth")

    @rx.event
    def authenticate(self):
        """Verifies the passcode and sets auth cookie if correct."""
        if self.passcode_input == self.passcode:
            self.authenticated = True
            self.auth_token = "is_login"
            self.passcode_input = ""

            yield rx.toast.success("Valid passcode")
            return rx.redirect("/")
        else:
            return rx.toast.error("Invalid passcode")

    @rx.event
    def logout(self):
        """Logs out the user by clearing the auth cookie."""
        self.authenticated = False
        self.auth_token = ""  # Clear the auth cookie
        return rx.redirect("/auth")

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

    @rx.event(background=True)
    async def handle_action_bar_keydown(self, keydown_character: str):
        """Handle keyboard shortcuts."""
        async with self:
            if (
                self.previous_keydown_character == "Control"
                and keydown_character == "Enter"
            ):
                yield State.process_question
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
        """Process the current question and add the Q&A pair to chat history."""
        if not self.question.strip():
            return

        # Store the current question but don't clear it yet
        current_question = self.question

        try:
            # Initialize API client
            client = AsyncOpenRouterAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            )

            # Format messages for the API
            messages = self.format_messages(current_question)

            # Start the stream processor
            processor = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                include_reasoning=True,
            )

            # Now that we have a processor, we can safely update the state
            async with self:
                self.processing = True
                self.question = ""  # Clear the input
                self.chat_history.append((current_question, ""))  # Add new Q&A pair
                self._save_current_chat()

            yield  # Allow UI to update

            # Process the stream
            async with processor:
                answer = ""
                async for chunk in processor:
                    if not self.processing:
                        break

                    async with self:
                        if chunk.reasoning:
                            answer += chunk.reasoning
                            self.chat_history[-1] = (current_question, answer)
                            self._save_current_chat()
                        if chunk.content:
                            answer += chunk.content
                            self.chat_history[-1] = (current_question, answer)
                            self._save_current_chat()

                    if ENABLE_AUTO_SCROLL_DOWN:
                        yield rx.call_script(self.scroll_to_bottom_js)

        except Exception as e:
            # Handle any errors that occur
            async with self:
                if (
                    len(self.chat_history) > 0
                    and self.chat_history[-1][0] == current_question
                ):
                    self.chat_history[-1] = (current_question, f"Error: {str(e)}")
                else:
                    self.chat_history.append((current_question, f"Error: {str(e)}"))
                self._save_current_chat()

            if ENABLE_AUTO_SCROLL_DOWN:
                yield rx.call_script(self.scroll_to_bottom_js)

        finally:
            # Always clean up
            async with self:
                self.processing = False
            yield

    @rx.event(background=True)
    async def update_question(self):
        """Update an existing question with new text."""
        if self.editing_question_index is None or not self.question.strip():
            return

        client = AsyncOpenRouterAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        # Store values before clearing state
        async with self:
            new_question = self.question
            current_index = self.editing_question_index

            # Reset editing state
            self.editing_question_index = None
            self.question = ""

            # Update the chat history
            self.chat_history[current_index] = (new_question, "")
            self._save_current_chat()
            self.processing = True

        yield

        try:
            messages = self.format_messages(new_question)
            session = await client.chat.completions.create(
                model=self.model,
                messages=messages[: 2 * current_index + 1],
                stream=True,
                include_reasoning=True,
            )

            answer = ""
            async for chunk in session:
                async with self:
                    if not self.processing:
                        await session.close()
                        break

                    # Handle both content and reasoning from the chunk
                    if chunk.reasoning:
                        answer += chunk.reasoning
                        self.chat_history[current_index] = (new_question, answer)
                        self._save_current_chat()
                    if chunk.content:
                        answer += chunk.content
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
