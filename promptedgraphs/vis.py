import seaborn as sns
from pydantic import BaseModel
from spacy import displacy

from promptedgraphs.models import EntityReference


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(
        int(rgb[0] * 256), int(rgb[1] * 256), int(rgb[2] * 256)
    )


def render_entities(
    text: str,
    ents: BaseModel | list[EntityReference] | dict = None,
    jupyter=True,
    color_dict: dict = None,
    color_palette: list[float] = None,
    **options
):
    """Renders entities using the displacy.render function"""

    if ents is None:
        return displacy.render(
            {"text": text}, style="ent", jupyter=jupyter, manual=True
        )
    elif hasattr(ents, "model_dump"):
        data = ents.model_dump()
        fields = sorted(data.keys())
        ents = [
            EntityReference(
                start=text.find(v), end=text.find(v) + len(v), label=k, text=v
            )
            for k, v in data.items()
            if v in text
        ]
    elif isinstance(ents, dict):
        data = ents
        fields = sorted(data.keys())
        ents = [
            EntityReference(
                start=text.find(v), end=text.find(v) + len(v), label=k, text=v
            )
            for k, v in data.items()
            if v in text
        ]
    elif isinstance(ents[0], EntityReference):
        fields = sorted({e.label for e in ents})
    else:
        raise ValueError("ents must be a list of EntityReference, BaseModel or dict")

    # Build colors
    if color_dict is None:
        palette = color_palette or sns.color_palette("Set2", 8)
        color_dict = {f: rgb_to_hex(color) for f, color in zip(list(fields), palette)}

    return displacy.render(
        {
            "text": text,
            "ents": [e.to_dict() for e in ents],
        },
        style="ent",
        jupyter=jupyter,
        manual=True,
        options={"colors": color_dict, **options},
    )
