import seaborn as sns
from pydantic import BaseModel
from spacy import displacy

from promptedgraphs.models import EntityReference


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(
        int(rgb[0] * 256), int(rgb[1] * 256), int(rgb[2] * 256)
    )


def get_fields(ents: list[EntityReference] | dict | BaseModel):
    if hasattr(ents, "model_dump"):
        data = ents.model_dump()
        return sorted(data.keys())
    elif isinstance(ents, dict):
        return sorted(ents.keys())
    elif isinstance(ents[0], EntityReference):
        return sorted({e.label for e in ents})
    else:
        raise ValueError("ents must be a list of EntityReference, BaseModel or dict")


def get_colors(fields: list[str], color_palette: list[float] = None):
    palette = color_palette or sns.color_palette("Set2", 8)
    return {f: rgb_to_hex(color) for f, color in zip(list(fields), palette)}


def ensure_entities(
    ents: list[EntityReference] | dict | BaseModel, text: str
) -> list[EntityReference]:
    if ents is None:
        return None
    elif hasattr(ents, "model_dump"):
        data = ents.model_dump()
        return [
            EntityReference(
                start=text.find(v), end=text.find(v) + len(v), label=k, text=v
            )
            for k, v in data.items()
            if v in text
        ]
    elif isinstance(ents, dict):
        data = ents
        return [
            EntityReference(
                start=text.find(v), end=text.find(v) + len(v), label=k, text=v
            )
            for k, v in data.items()
            if v in text
        ]
    return [e for e in ents if isinstance(e, EntityReference)]


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

    ents = ensure_entities(ents, text)
    fields = get_fields(ents)
    color_dict = color_dict or get_colors(fields, color_palette)

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
