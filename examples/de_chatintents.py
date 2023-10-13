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

import tqdm
from pydantic import BaseModel, Field

from promptedgraphs.config import Config, load_config
from promptedgraphs.data_extraction import extract_data


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
    #     """Hello fellow travelers! We're venturing to New Zealand from March 5-18th as a couple. We'll primarily be in Auckland visiting my sister, but we're hoping to explore more of the North Island. Since we're big fans of adventure sports and nature, we're thinking of places like the Tongariro Alpine Crossing or maybe Waitomo Caves. However, we're unsure about the best routes or if there are any hidden gems nearby. Any tips or suggestions? Has anyone been around those areas in March? Recommendations for cozy accommodations, local eateries, or any must-visit spots around Auckland would be greatly appreciated. Cheers!"""

    for i, msg in tqdm.tqdm(enumerate(messages)):
        async for intent in extract_data(
            text=msg, output_type=UserIntent, config=Config()
        ):
            print(i, intent)
            intents.append((i, intent))

    # for i, msg in enumerate(messages):
    #     async for intent in extract_data(
    #     ):

    print(intents)


if __name__ == "__main__":
    asyncio.run(main())
