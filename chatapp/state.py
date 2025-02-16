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
from asyncio import Queue
from dataclasses import dataclass


@dataclass
class StreamChunk:
    content: Optional[str] = None
    reasoning: Optional[str] = None
    is_done: bool = False
    error: Optional[str] = None


class StreamProcessor:
    def __init__(self, response, session):
        self.response = response
        self.session = session
        self.queue: Queue[StreamChunk] = Queue()
        self._task: Optional[asyncio.Task] = None
        self._closed = False
        self._buffer = ""
        self._lock = asyncio.Lock()

    async def start(self):
        """Start processing the stream in the background."""
        self._task = asyncio.create_task(self._process_stream())
        return self

    async def _read_chunk(self) -> Optional[str]:
        """Read a chunk from the response with proper locking."""
        async with self._lock:
            try:
                chunk = await self.response.content.readline()
                return chunk.decode("utf-8") if chunk else None
            except Exception:
                return None

    async def _process_stream(self):
        """Process the stream and put chunks into the queue."""
        try:
            while not self._closed:
                line = await self._read_chunk()
                if not line:
                    break

                line = line.strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        await self.queue.put(StreamChunk(is_done=True))
                        break

                    try:
                        data_obj = json.loads(data)
                        chunk = ChatCompletionChunk(data_obj)

                        if chunk.choices:
                            delta = chunk.choices[0].delta
                            if delta.content is not None:
                                await self.queue.put(StreamChunk(content=delta.content))
                            elif delta.reasoning is not None:
                                await self.queue.put(
                                    StreamChunk(reasoning=delta.reasoning)
                                )

                            if chunk.choices[0].finish_reason is not None:
                                await self.queue.put(StreamChunk(is_done=True))
                                break

                    except json.JSONDecodeError:
                        continue

            # End of stream
            if not self._closed:
                await self.queue.put(StreamChunk(is_done=True))

        except Exception as e:
            if not self._closed:
                await self.queue.put(StreamChunk(error=str(e)))
        finally:
            await self.close()

    async def __aiter__(self):
        """Iterate over the stream chunks."""
        try:
            while True:
                chunk = await self.queue.get()
                if chunk.error:
                    raise Exception(chunk.error)
                if chunk.is_done:
                    break
                yield chunk
                self.queue.task_done()
        except asyncio.CancelledError:
            await self.close()
            raise

    async def close(self):
        """Close the stream processor."""
        if not self._closed:
            self._closed = True
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            await self.response.release()
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
                        return ChatCompletion(data)
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
                model=self.model, messages=messages, stream=True, include_reasoning=True
            ) as stream:
                async for chunk in stream:
                    async with self:
                        if not self.processing:
                            break

                        if chunk.reasoning is not None:
                            answer += chunk.reasoning
                            self.chat_history[-1] = (question, answer)
                            self._save_current_chat()
                        elif chunk.content is not None:
                            answer += chunk.content
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

    @rx.event(background=True)
    async def update_question(self):
        """Update an existing question with new text."""
        if self.editing_index is None or not self.question.strip():
            return

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
                include_reasoning=True,
            ) as stream:
                answer = ""
                async for chunk in stream:
                    async with self:
                        if not self.processing:
                            break

                        if chunk.reasoning is not None:
                            answer += chunk.reasoning
                            self.chat_history[current_index] = (new_question, answer)
                            self._save_current_chat()
                        elif chunk.content is not None:
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
