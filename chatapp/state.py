"""State management for the chat app."""

import os
from typing import *
import reflex as rx
from dotenv import load_dotenv

load_dotenv()

ENABLE_AUTO_SCROLL_DOWN = False

import json
from typing import *
import aiohttp
import asyncio


class ChatCompletion:
    def __init__(self, response_data: Dict[str, Any]):
        self.choices = response_data.get("choices", [])
        self.id = response_data.get("id")
        self.model = response_data.get("model")
        self.created = response_data.get("created")
        self.usage = response_data.get("usage")
        self.response_type = response_data.get("response_type", "content")


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


class ChatCompletionChunk:
    def __init__(self, chunk_data: Dict[str, Any], response_type: str = "content"):
        self.choices = [Choice(choice) for choice in chunk_data.get("choices", [])]
        self.id = chunk_data.get("id")
        self.model = chunk_data.get("model")
        self.created = chunk_data.get("created")
        self.response_type = response_type


class StreamResponse:
    """Wrapper for streaming response that combines reasoning and content."""

    def __init__(self, response, session, include_reasoning: bool = True):
        self.response = response
        self.session = session
        self.buffer = ""
        self._closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._closed:
            raise StopAsyncIteration

        try:
            chunk = await self.response.content.read(1024)
            if not chunk:
                await self.close()
                raise StopAsyncIteration

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
                        await self.close()
                        raise StopAsyncIteration

                    try:
                        data_obj = json.loads(data)
                        chunk = ChatCompletionChunk(data_obj)

                        if not chunk.choices:
                            continue

                        choice = chunk.choices[0]
                        delta = choice.delta

                        # Return any non-null content, whether it's reasoning or content
                        if delta.reasoning is not None:
                            return chunk
                        if delta.content is not None:
                            return chunk

                    except json.JSONDecodeError:
                        continue

            return await self.__anext__()

        except Exception as e:
            await self.close()
            raise StopAsyncIteration

    async def close(self):
        """Properly close both response and session."""
        if not self._closed:
            self._closed = True
            await self.response.release()
            await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class AsyncOpenAIOpenRouter:
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
        ) -> Union[ChatCompletion, StreamResponse]:
            """Create a chat completion with proper session management."""
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
                        return ChatCompletion(data)
                    finally:
                        await session.close()

                return StreamResponse(response, session, include_reasoning)
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
        """Process the question and get a response with both reasoning and content."""
        if not self.question.strip():
            return

        client = AsyncOpenAIOpenRouter(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        question = self.question
        answer = ""

        async with self:
            self.chat_history.append((question, answer))
            self._save_current_chat()
            self.question = ""
            self.processing = True
        yield

        try:
            messages = self.format_messages(question)

            async with await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                include_reasoning=True,  # Enable reasoning in the API call
            ) as session:
                async for item in session:
                    async with self:
                        if not self.processing:
                            break

                        delta = item.choices[0].delta
                        # Add either reasoning or content to the answer
                        if delta.reasoning is not None:
                            answer += delta.reasoning
                            self.chat_history[-1] = (question, answer)
                            self._save_current_chat()
                        elif delta.content is not None:
                            answer += delta.content
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
        if self.editing_index is None or not self.question.strip():
            return

        # Store values before clearing state
        async with self:
            new_question = self.question
            current_index = self.editing_index
            original_answer = self.chat_history[current_index][1]

            # Reset editing state
            self.editing_index = None
            self.editing_question = None
            self.question = ""

            # Update the chat history
            self.chat_history[current_index] = (new_question, "")
            self._save_current_chat()
            self.processing = True

        yield

        try:
            client = AsyncOpenAIOpenRouter(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            )

            messages = self.format_messages(new_question)

            async with await client.chat.completions.create(
                model=self.model,
                messages=messages[: 2 * current_index + 1],
                stream=True,
                include_reasoning=True,  # Enable reasoning in the API call
            ) as session:
                answer = ""
                async for item in session:
                    async with self:
                        if not self.processing:
                            break

                        delta = item.choices[0].delta
                        # Add either reasoning or content to the answer
                        if delta.reasoning is not None:
                            answer += delta.reasoning
                            self.chat_history[current_index] = (new_question, answer)
                            self._save_current_chat()
                        elif delta.content is not None:
                            answer += delta.content
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
