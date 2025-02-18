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
    """Stream processor that follows the official OpenRouter documentation approach."""

    def __init__(self, response, session):
        self.response = response
        self.session = session
        self.buffer = ""
        self._closed = False

    async def start(self):
        """Start processing the stream."""
        return self

    async def __aiter__(self):
        """Iterate over the stream chunks following the official approach."""
        try:
            while not self._closed:
                chunk = await self.response.content.read(1024)
                if not chunk:
                    break

                self.buffer += chunk.decode("utf-8")

                while True:
                    line_end = self.buffer.find("\n")
                    if line_end == -1:
                        break

                    line = self.buffer[:line_end].strip()
                    self.buffer = self.buffer[line_end + 1 :]

                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            self._closed = True
                            break

                        try:
                            data_obj = json.loads(data)
                            content = data_obj["choices"][0]["delta"].get("content")
                            reasoning = data_obj["choices"][0]["delta"].get("reasoning")

                            # Only yield if we have content or reasoning
                            if content or reasoning:
                                yield StreamChunk(
                                    content=content, reasoning=reasoning, is_done=False
                                )
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"Error processing chunk: {str(e)}")
                            continue

        except Exception as e:
            print(f"Stream error: {str(e)}")
        finally:
            await self.close()

    async def close(self):
        """Close the stream processor and clean up resources."""
        if not self._closed:
            self._closed = True
            if not self.response.closed:
                await self.response.release()
            await self.session.close()

    async def __aenter__(self):
        """Support for async context manager."""
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting async context."""
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


class Message(rx.Base):
    """A chat message."""

    role: str
    content: Optional[str] = None
    reasoning: Optional[str] = None


class State(rx.State):
    """The app state."""

    # Chat state
    chat_history: List[Message] = []
    question: str = ""
    model: str = "deepseek/deepseek-r1"
    previous_keydown_character: str = ""

    # UI state
    processing: bool = False
    modal_open: bool = False

    # Editing
    editing_user_message_index: Optional[int] = None
    editing_assistant_content_index: Optional[int] = None
    editing_assistant_reasoning_index: Optional[int] = None
    reasoning: str = ""
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
        for msg in self.chat_history:
            if msg.content:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": question})
        return messages

    @rx.event(background=True)
    async def process_question(self):
        """Process the current question and add it to chat history."""
        if not self.question.strip():
            return

        current_question = self.question

        try:
            # Initialize API client
            client = AsyncOpenRouterAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            )

            messages = self.format_messages(current_question)

            processor = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                include_reasoning=True,
            )

            async with self:
                self.processing = True
                self.question = ""  # Clear the input
                # Add user message
                self.chat_history.append(Message(role="user", content=current_question))
                # Add initial assistant message
                self.chat_history.append(Message(role="assistant"))
                self._save_current_chat()

            yield

            async with processor:
                answer = ""
                reasoning = ""
                async for chunk in processor:
                    if not self.processing:
                        break

                    async with self:
                        if chunk.reasoning:
                            reasoning += chunk.reasoning
                            self.chat_history[-1].reasoning = reasoning
                            self._save_current_chat()
                        if chunk.content:
                            answer += chunk.content
                            self.chat_history[-1].content = answer
                            self._save_current_chat()

                    if ENABLE_AUTO_SCROLL_DOWN:
                        yield rx.call_script(self.scroll_to_bottom_js)

        except Exception as e:
            # Handle any errors that occur
            async with self:
                error_msg = f"Error: {str(e)}"
                self.chat_history.append(Message(role="assistant", content=error_msg))
                self._save_current_chat()

            if ENABLE_AUTO_SCROLL_DOWN:
                yield rx.call_script(self.scroll_to_bottom_js)

        finally:
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

    def start_editing_user_message(self, index: int):
        """Start editing a user message."""
        self.editing_user_message_index = index
        self.question = self.chat_history[index].content

    def start_editing_assistant_content(self, index: int):
        """Start editing assistant content."""
        self.editing_assistant_content_index = index
        self.answer = self.chat_history[index].content

    def start_editing_assistant_reasoning(self, index: int):
        """Start editing assistant reasoning."""
        self.editing_assistant_reasoning_index = index
        self.reasoning = self.chat_history[index].reasoning

    def cancel_editing(self):
        """Cancel all editing modes."""
        self.editing_user_message_index = None
        self.editing_assistant_content_index = None
        self.editing_assistant_reasoning_index = None
        self.question = ""
        self.answer = ""
        self.reasoning = ""

    @rx.event(background=True)
    async def update_user_message(self):
        """Update an existing user message and regenerate the answer."""
        if self.editing_user_message_index is None or not self.question.strip():
            return

        client = AsyncOpenRouterAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        # Store values before clearing state
        async with self:
            new_question = self.question
            current_index = self.editing_user_message_index

            # Reset editing state
            self.editing_user_message_index = None
            self.question = ""

            # Update the user message
            self.chat_history[current_index].content = new_question
            # Remove all subsequent messages
            self.chat_history = self.chat_history[: current_index + 1]
            self._save_current_chat()
            self.processing = True

        yield

        try:
            messages = self.format_messages(new_question)
            session = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                include_reasoning=True,
            )

            # Initialize empty assistant message
            async with self:
                self.chat_history.append(Message(role="assistant"))
                self._save_current_chat()

            answer = ""
            reasoning = ""
            async for chunk in session:
                if not self.processing:
                    await session.close()
                    break

                async with self:
                    if chunk.reasoning:
                        reasoning += chunk.reasoning
                        self.chat_history[-1].reasoning = reasoning
                        self._save_current_chat()
                    if chunk.content:
                        answer += chunk.content
                        self.chat_history[-1].content = answer
                        self._save_current_chat()

                if ENABLE_AUTO_SCROLL_DOWN:
                    yield rx.call_script(self.scroll_to_bottom_js)

        except Exception as e:
            async with self:
                self.chat_history.append(
                    Message(role="assistant", content=f"Error: {str(e)}")
                )
                self._save_current_chat()

            if ENABLE_AUTO_SCROLL_DOWN:
                yield rx.call_script(self.scroll_to_bottom_js)

        finally:
            async with self:
                self.processing = False
            yield

    @rx.event
    def update_assistant_content(self):
        """Update assistant content."""
        if self.editing_assistant_content_index is None or not self.answer.strip():
            return

        index = self.editing_assistant_content_index
        self.chat_history[index].content = self.answer
        self._save_current_chat()

        # Reset editing state
        self.editing_assistant_content_index = None
        self.answer = ""

    @rx.event
    def update_assistant_reasoning(self):
        """Update assistant reasoning."""
        if self.editing_assistant_reasoning_index is None or not self.reasoning.strip():
            return

        index = self.editing_assistant_reasoning_index
        self.chat_history[index].reasoning = self.reasoning
        self._save_current_chat()

        # Reset editing state
        self.editing_assistant_reasoning_index = None
        self.reasoning = ""

    def delete_message(self, index: int):
        """Delete a message and its associated messages."""
        # If deleting a user message, also delete the following assistant message
        if self.chat_history[index].role == "user" and index + 1 < len(
            self.chat_history
        ):
            self.chat_history.pop(index + 1)

        # Delete the selected message
        self.chat_history.pop(index)
        self._save_current_chat()
