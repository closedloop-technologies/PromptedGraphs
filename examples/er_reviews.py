import asyncio

from spacy import displacy

from promptedgraphs.config import Config, load_config
from promptedgraphs.entity_recognition import extract_entities


async def main():
    load_config()

    ### Canonical Text Labeling Task: Sentiment Analysis of Customer Reviews

    text_of_reviews = """
1. "I absolutely love this product. It's been a game changer!"
2. "The service was quite poor and the staff was rude."
3. "The item is okay. Nothing special, but it gets the job done."
"""

    labels = {
        "POSITIVE": "A postive review of a product or service.",
        "NEGATIVE": "A negative review of a product or service.",
        "NEUTRAL": "A neutral review of a product or service.",
    }

    ents = []
    async for msg in extract_entities(
        name="sentiment",
        description="Sentiment Analysis of Customer Reviews",
        text=text_of_reviews,
        labels=labels,
        config=Config(),
        include_reason=False,
    ):
        ents.append(msg)

    print(ents)

    displacy.render(
        {
            "text": text_of_reviews,
            "ents": ents,
        },
        style="ent",
        jupyter=True,
        manual=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
