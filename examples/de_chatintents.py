"""
Here are some messages a chatbot might receive and their category

1. **Questions and Requests:**
   - "How can I help you?"
   - "Tell me a joke."
   - "What's the weather like tomorrow?"
   - "How does this work?"
   - "Where can I find more information?"

2. **Greetings and Salutations:**
   - "Hello!"
   - "Hi there!"
   - "Good morning."
   - "Hey, Chatbot!"

3. **Feedback and Complaints:**
   - "You're not very helpful."
   - "Thanks for the assistance."
   - "That wasn't the answer I was looking for."

4. **Technical Queries:**
   - "Can you integrate with my CRM?"
   - "Do you support multi-language queries?"
   - "How do I reset my password?"

5. **Personal Interaction:**
   - "How are you today?"
   - "Tell me something about yourself."
   - "Do you like pizza?"

6. **Random Messages and Tests:**
   - "asdfghjkl"
   - "Testing... 1, 2, 3."
   - "Is anyone there?"

7. **Commands:**
   - "Show me my account balance."
   - "Start a new session."
   - "Cancel my order."

8. **Seeking Recommendations:**
   - "Can you suggest a good book?"
   - "Where should I go for dinner?"

9. **Closing the Conversation:**
   - "Goodbye."
   - "Thanks for your help!"
   - "Talk to you later."

10. **Emotional or Philosophical Queries:**
   - "Do you have feelings?"
   - "What's the meaning of life?"
   - "Can you fall in love?"

11. **Contextual or Continued Conversations:**
   - "Based on that, what should I do next?"
   - "Tell me more."

12. **Interactive Actions:**
   - "[User sends an image]"
   - "Can you play music?"
   - "Translate this for me."

13. **Clarifications:**
   - "I didn't understand that."
   - "Can you explain that in simpler terms?"
   - "Did you mean...?"

14. **Challenging the Chatbot:**
   - "Are you smarter than a human?"
   - "I bet you can't answer this!"

15. **Feedback on Answers:**
   - "That was helpful, thanks!"
   - "That's not right. Try again."

"""
import asyncio
from pprint import pprint

import tqdm
from pydantic import BaseModel, Field

from promptedgraphs.config import Config, load_config
from promptedgraphs.extraction.data_from_text import data_from_text


async def main():
    load_config()

    ### Information Extraction of Chat intent
    messages = [
        "How can I help you?",  # Questions and Requests
        "Hello!",  # Greetings and Salutations
        "You're not very helpful.",  # Feedback and Complaints
        "Can you integrate with my CRM?",  # Technical Queries
        "How are you today?",  # Personal Interaction
        "asdfghjkl",  # Random Messages and Tests
        "Show me my account balance.",  # Commands
        "Can you suggest a good book?",  # Seeking Recommendations
        "Goodbye.",  # Closing the Conversation
        "Do you have feelings?",  # Emotional or Philosophical Queries
        "Based on that, what should I do next?",  # Contextual or Continued Conversations
        "[User sends an image]",  # Interactive Actions
        "I didn't understand that.",  # Clarifications
        "Are you smarter than a human?",  # Challenging the Chatbot
        "That was helpful, thanks!",  # Feedback on Answers
    ]

    class UserIntent(BaseModel):
        """The UserIntent entity, representing the canonical description of what a user desires to achieve in a given conversation."""

        intent_name: str = Field(
            title="Intent Name",
            description="Canonical name of the user's intent",
            examples=[
                "question",
                "command",
                "clarification",
                "chit_chat",
                "greeting",
                "feedback",
                "nonsensical",
                "closing",
                "harrassment",
                "unknown",
            ],
        )
        description: str | None = Field(
            title="Intent Description",
            description="A detailed explanation of the user's intent",
        )

    intents = []

    # TODO move to parrellel processing across messages
    # Make it an async generator
    async def parallel_data_from_text(text):
        results = []
        async for result in data_from_text(
            text=text, output_type=UserIntent, config=Config()
        ):
            results.append((result, text))
        return results

    # Create a list of coroutine objects
    tasks = [parallel_data_from_text(msg) for msg in messages]

    # Use as_completed to yield from tasks as they complete
    for future in asyncio.as_completed(tasks):
        results = await future
        intents.extend(results)

    pprint(intents)


if __name__ == "__main__":
    asyncio.run(main())
