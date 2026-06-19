from pydantic import BaseModel

from promptedgraphs.runtime import (
    GraphOperation,
    PromptedGraph,
    ResourceDelta,
    ResourceRef,
    SQLitePromptedStore,
    prompted_node,
)


class Entity(BaseModel):
    name: str
    kind: str
    confidence: float = 1.0


class EntityLinkingResult(BaseModel):
    entities: list[Entity]
    graph_delta: ResourceDelta | None = None


def test_prompted_node_exports_openai_tool_schema_and_records_run():
    store = SQLitePromptedStore.in_memory()

    @prompted_node(
        description="Extract canonical entities from text.",
        resources=[ResourceRef(name="project_kg")],
        store=store,
    )
    def extract_entities(document: str) -> EntityLinkingResult:
        return EntityLinkingResult(
            entities=[Entity(name="Astrocyte", kind="Company")],
            graph_delta=ResourceDelta(
                resource_name="project_kg",
                operations=[
                    GraphOperation(
                        op="add_entity",
                        target="Astrocyte",
                        data={"kind": "Company"},
                        confidence=0.95,
                    )
                ],
            ),
        )

    schema = extract_entities.to_openai_tool()
    assert schema["type"] == "function"
    assert schema["name"] == "extract_entities"
    assert schema["strict"] is True
    assert schema["parameters"]["required"] == ["document"]
    assert schema["parameters"]["additionalProperties"] is False

    run = extract_entities.run("Astrocyte acquired ExampleCo.")
    assert run.status == "ok"
    assert run.output["entities"][0]["name"] == "Astrocyte"
    assert run.proposed_deltas[0].resource_name == "project_kg"
    assert store.get_run(run.run_id).node_name == "extract_entities"

    label = extract_entities.add_label(run, "accept", value=True)
    assert label.run_id == run.run_id
    assert store.list_labels(run.run_id)[0].label_type == "accept"


def test_prompted_graph_runs_nodes_in_dag_order_and_passes_outputs():
    @prompted_node(description="Extract a normalized name from text.")
    def extract_name(document: str) -> str:
        return document.split()[0]

    @prompted_node(description="Build a greeting from a normalized name.")
    def greet(name: str) -> str:
        return f"hello {name}"

    graph = PromptedGraph("demo")
    graph.add_node(extract_name)
    graph.add_node(greet)
    graph.edge(extract_name, greet, target_arg="name")

    runs = graph.run({"extract_name": {"document": "Sean builds prompted graphs"}})

    assert list(runs.keys()) == ["extract_name", "greet"]
    assert runs["greet"].output == "hello Sean"


def test_prompted_graph_rejects_cycles():
    @prompted_node
    def a() -> str:
        return "a"

    @prompted_node
    def b(a_output: str) -> str:
        return a_output

    graph = PromptedGraph("cycle")
    graph.add_node(a)
    graph.add_node(b)
    graph.edge(a, b, target_arg="a_output")
    graph.edge(b, a)

    try:
        graph.topological_order()
        assert False, "cycles should be rejected"
    except ValueError as exc:
        assert "DAG" in str(exc)
