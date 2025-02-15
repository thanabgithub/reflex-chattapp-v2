import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
import reflex as rx

load_dotenv()

class State(rx.State):
    # The current question being asked
    question: str = ""
    
    # The selected model
    model: str = "GPT-4"
    
    # Chat history as list of (question, answer) tuples
    chat_history: list[tuple[str, str]] = []
    
    # Conversation history
    history: list[str] = ["会話 1", "会話 2", "会話 3", "会話 4", "会話 5"]

    def format_messages(self):
        """Format chat history into the required message structure"""
        messages = []

        # Add previous chat history
        for question, answer in self.chat_history:
            # Add user message
            messages.append(
                {"role": "user", "content": [{"type": "text", "text": question}]}
            )

            # Add assistant message
            messages.append(
                {"role": "assistant", "content": [{"type": "text", "text": answer}]}
            )

        # Add the current question
        messages.append(
            {"role": "user", "content": [{"type": "text", "text": self.question}]}
        )

        return messages

    def new_thread(self):
        """Start a new chat thread."""
        self.chat_history = []
        self.question = ""

    def load_chat(self, chat_id: str):
        """Load a specific chat history."""
        # In a real app, this would load from a database
        self.chat_history = []
        
    def set_model(self, model: str):
        """Set the model to use for chat."""
        self.model = model

    async def answer(self):
        """Generate an AI response."""
        # Our chatbot has some brains now!
        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

        # Get formatted message history
        messages = self.format_messages()

        session = await client.chat.completions.create(
            model="gpt-4" if self.model == "GPT-4" else "gpt-3.5-turbo",
            messages=messages,
            stop=None,
            temperature=0.7,
            stream=True,
        )

        # Add to the answer as the chatbot responds.
        answer = ""
        self.chat_history.append((self.question, answer))

        # Clear the question input.
        self.question = ""
        # Yield here to clear the frontend input before continuing.
        yield

        async for item in session:
            if hasattr(item.choices[0].delta, "content"):
                if item.choices[0].delta.content is None:
                    # presence of 'None' indicates the end of the response
                    break
                answer += item.choices[0].delta.content
                self.chat_history[-1] = (
                    self.chat_history[-1][0],
                    answer,
                )
                yield