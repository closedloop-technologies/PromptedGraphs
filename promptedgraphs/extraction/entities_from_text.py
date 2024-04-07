import asyncio
import enum

from pydantic import BaseModel, Field

from promptedgraphs.config import Config, load_config
from promptedgraphs.extraction.data_from_text import data_from_text
from promptedgraphs.llms.openai_chat import LanguageModel


async def entities_from_text(
    text: str,
    labels: dict[str, str],
    config: Config,
    name="entities",
    description: str | None = "",
    include_reason=True,
    model=LanguageModel.GPT35_turbo,
    temperature=0.2,
):
    label_list = sorted(labels.keys())

    LabelEnums = enum.Enum('LabelEnums', {l:i for i,l in enumerate(label_list)})

    class EntityReference(BaseModel):
        """The raw text and label for each entity occurrence"""
        text_span: str = Field(
            title="Text Span",
            description="The exact text of referenced entity.",
        )
        is_entity: bool = Field(
            title="Is Entity",
            description="A boolean indicating if the span is an entity label.",
        )
        label: str = Field(
            title="Label",
            description="The label of the entity.",
            examples=label_list + ["==NONE=="],
        )
        if include_reason:
            reason: str = Field(
                title="Reason",
                description="A short description of why that label was selected.",
            )
        else:
            reason: str | None = Field(
                title="Reason",
                description="A short description of why that label was selected.",
            )
    EntityReference.__doc__ += """\n
    Labels must be one of the following: {label_list}""".format(label_list=label_list + ["==NONE=="])

    EntityReference.__doc__ += """\n
    Label Definitions:\n""" + "\n".join([f" * {label}: {labels[label]}" for label in label_list])
    

    async for er in data_from_text(
        text=text,
        output_type=EntityReference,
        config=config or Config(),
        model=model,
        temperature=temperature,
    ):
        yield er



async def example():
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
    async for msg in entities_from_text(
        name="sentiment",
        description="Sentiment Analysis of Customer Reviews",
        text=text_of_reviews,
        labels=labels,
        config=Config(),
        include_reason=False,
    ):
        ents.append(msg)

    print(ents)

    # displacy.render(
    #     {
    #         "text": text_of_reviews,
    #         "ents": ents,
    #     },
    #     style="ent",
    #     jupyter=True,
    #     manual=True,
    # )


if __name__ == "__main__":
    asyncio.run(example())
