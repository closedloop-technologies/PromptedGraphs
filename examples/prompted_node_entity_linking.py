"""Motivated PromptedGraphs v1 example: entity linking with a managed KG delta.

Run with: python examples/prompted_node_entity_linking.py
"""

from pydantic import BaseModel, Field

from promptedgraphs.runtime import (
    GraphOperation,
    PromptedGraph,
    ResourceDelta,
    ResourceRef,
    prompted_node,
)


class Mention(BaseModel):
    text: str
    start: int | None = None
    end: int | None = None


class LinkedEntity(BaseModel):
    canonical_name: str
    entity_type: str
    mentions: list[Mention] = Field(default_factory=list)
    confidence: float = 1.0


class EntityLinkingResult(BaseModel):
    entities: list[LinkedEntity]
    graph_delta: ResourceDelta | None = None


@prompted_node(
    description="Extract and link organization/person mentions into a project knowledge graph.",
    resources=[ResourceRef(name="project_kg", kind="knowledge_graph")],
)
def extract_and_link_entities(document: str) -> EntityLinkingResult:
    """This deterministic stub represents a later generated implementation.

    Earlier versions of the same node could be a frontier LLM passthrough. Once
    enough accepted/corrected labels exist, generated code like this can be
    promoted if it passes regression cases generated from labels.
    """
    entities: list[LinkedEntity] = []
    operations: list[GraphOperation] = []

    for name, kind in [
        ("Astrocyte", "Company"),
        ("ExampleCo", "Company"),
        ("Jane Doe", "Person"),
    ]:
        if name in document:
            entities.append(
                LinkedEntity(
                    canonical_name=name,
                    entity_type=kind,
                    mentions=[Mention(text=name)],
                    confidence=0.95,
                )
            )
            operations.append(
                GraphOperation(
                    op="add_entity",
                    target=name,
                    data={"entity_type": kind},
                    confidence=0.95,
                    provenance={"source": "example deterministic implementation"},
                )
            )

    return EntityLinkingResult(
        entities=entities,
        graph_delta=ResourceDelta(resource_name="project_kg", operations=operations),
    )


@prompted_node(description="Summarize linked entities for a downstream agent step.")
def summarize_entities(linked: dict) -> str:
    names = [entity["canonical_name"] for entity in linked["entities"]]
    return ", ".join(names)


if __name__ == "__main__":
    print(extract_and_link_entities.to_openai_tool())

    graph = PromptedGraph("company_research_entity_linking")
    graph.add_node(extract_and_link_entities)
    graph.add_node(summarize_entities)
    graph.edge(extract_and_link_entities, summarize_entities, target_arg="linked")

    runs = graph.run(
        {
            "extract_and_link_entities": {
                "document": "Astrocyte acquired ExampleCo after working with Jane Doe."
            }
        }
    )
    runs["extract_and_link_entities"].accept("Looks correct for the demo document.")
    print(runs["summarize_entities"].output)
