# PromptedGraphs

**From Dataset Labeling to Deployment: The Power of NLP and LLMs Combined.**

## Description

PromptedGraphs is a Python library that aims to seamlessly integrate traditional NLP methods with the capabilities of modern Large Language Models (LLMs) in the realm of knowledge graphs. Our library offers tools tailored for dataset labeling, model training, and smooth deployment to production environments. We leverage the strengths of [spacy](https://github.com/explosion/spaCy) for core NLP tasks, [snorkel](https://github.com/closedloop-technologies/snorkel) for effective data labeling, and `async` to ensure enhanced performance. Our mission is to provide a harmonized solution to knowledge graph development when you have to merge traditional and LLM-driven approaches, squarely addressing the challenges associated with accuracy, efficiency, and affordability.

## ✨ Features

- **Named Entity Recognition (NER)**: Customize ER labels based on your domain.
- **Structured Data Extraction**: Extract structured data from unstructured text.
- **Entity Resolution**: Deduplication and normalization
- **Relationship Extraction**: Either open ended labels or constrain to your domain
- **Entity Linking**: Link references in text to entities in a graph
- **Graph Construction**: Create or update knowledge graphs

## Core Functions

- **Dataset Labeling**: Efficient tools for labeling datasets, powered by `haystack`.
- **Model Training**: Combine the reliability of NLP and the prowess of LLMs.
- **Deployment**: Streamlined processes to ensure smooth transition to production.

## Requirements

- Python 3.10 or newer.

## 📦 Installation

To install `PromptedGraphs` via pip:

```bash
pip install promptedgraphs
# or
poetry add promptedgraphs
```

## Usage
### Entity Recognition

from [examples/er_reviews.ipynb](https://github.com/closedloop-technologies/PromptedGraphs/blob/main/examples/er_reviews.ipynb)

```python
from spacy import displacy
from promptedgraphs.config import Config
from promptedgraphs.entity_recognition import extract_entities

labels = {
    "POSITIVE": "A postive review of a product or service.",
    "NEGATIVE": "A negative review of a product or service.",
    "NEUTRAL": "A neutral review of a product or service.",
}

text_of_reviews = """
1. "I absolutely love this product. It's been a game changer!"
2. "The service was quite poor and the staff was rude."
3. "The item is okay. Nothing special, but it gets the job done."
""".strip()


# Label Sentiment
ents = []
async for msg in extract_entities(
    name="sentiment",
    description="Sentiment Analysis of Customer Reviews",
    text=text_of_reviews,
    labels=labels,
    config=Config(),  # Reads `OPENAI_API_KEY` from .env file or environment
):
    ents.append(msg)

# Show Results using spacy.displacy
displacy.render(
    {
        "text": text_of_reviews,
        "ents": [e.to_dict() for e in ents],
    },
    style="ent",
    jupyter=True,
    manual=True,
    options={
        "colors": {"POSITIVE": "#7aecec", "NEGATIVE": "#f44336", "NEUTRAL": "#f4f442"}
    },
)
```
![displacy-sentiment-example](./assets/displacy-sentiment-example.png?raw=true)


### Structured Data Extraction

from [examples/de_chatintents.ipynb](https://github.com/closedloop-technologies/PromptedGraphs/blob/main/examples/de_chatintents.ipynb)

```python
from pydantic import BaseModel, Field

from promptedgraphs.config import Config
from promptedgraphs.data_extraction import extract_data


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


msg = """It's a busy day, I need to send an email and to buy groceries"""

async for intent in extract_data(
    text=msg, output_type=list[UserIntent], config=Config()
):
    print(intent)
```
```bash
intent_name='task' description='User wants to complete a task'
intent_name='communication' description='User wants to send an email'
intent_name='shopping' description='User wants to buy groceries'
```

## 📚 Resources

  * [Awesome-LLM-KG](https://github.com/RManLuo/Awesome-LLM-KG)
  * [KG-LLM-Papers](https://github.com/zjukg/KG-LLM-Papers)

### Related Libraries
  * [instructor](https://jxnl.github.io/instructor/)
  * [marvin](https://github.com/PrefectHQ/marvin)

## Contributing

We welcome contributions! Please DM me [@seankruzel](https://twitter.com/seankruzel) or create issues or pull requests.

## 📝 License

This project is licensed under the terms of the [MIT license](/LICENSE).

Built using [quantready](https://github.com/closedloop-technologies/quantready) using template [https://github.com/closedloop-technologies/quantready-api](https://github.com/closedloop-technologies/quantready-api)
