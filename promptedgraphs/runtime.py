"""Lightweight self-improving callable/DAG runtime for PromptedGraphs."""
from __future__ import annotations

import inspect, json, sqlite3, time
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, get_type_hints
from uuid import uuid4

from pydantic import BaseModel, Field, TypeAdapter

JsonDict = dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResourceRef(BaseModel):
    """Declared local resource, such as a knowledge graph or SQLite database."""
    name: str
    kind: str = "knowledge_graph"
    version: str | None = None


class GraphOperation(BaseModel):
    """Proposed mutation against a declared local resource."""
    op: Literal["add_entity", "update_entity", "add_edge", "add_alias", "add_evidence", "deprecate", "custom"]
    target: str
    data: JsonDict = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: JsonDict = Field(default_factory=dict)


class ResourceDelta(BaseModel):
    """Replayable proposed resource update; do not mutate resources directly."""
    resource_name: str
    operations: list[GraphOperation] = Field(default_factory=list)


class PromptedNodeSpec(BaseModel):
    name: str
    description: str
    input_schema: JsonDict
    output_schema: JsonDict | None = None
    resources: list[ResourceRef] = Field(default_factory=list)
    strict: bool = True
    implementation_version: str = "python@v1"


class PromptedLabel(BaseModel):
    label_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    label_type: Literal["accept", "reject", "correct_output", "correct_resource_delta", "score", "comment"]
    value: Any = None
    comment: str | None = None
    created_by: str = "human"
    created_at: datetime = Field(default_factory=utc_now)


class PromptedRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    node_name: str
    input: JsonDict
    output: Any = None
    resource_refs: list[ResourceRef] = Field(default_factory=list)
    proposed_deltas: list[ResourceDelta] = Field(default_factory=list)
    implementation_version: str = "python@v1"
    status: Literal["ok", "error"] = "ok"
    error: str | None = None
    labels: list[PromptedLabel] = Field(default_factory=list)
    latency_ms: float | None = None
    cost_estimate: float | None = None
    created_at: datetime = Field(default_factory=utc_now)

    def add_label(self, label_type: str, value: Any = None, comment: str | None = None, created_by: str = "human") -> PromptedLabel:
        label = PromptedLabel(run_id=self.run_id, label_type=label_type, value=value, comment=comment, created_by=created_by)
        self.labels.append(label)
        return label

    def accept(self, comment: str | None = None) -> PromptedLabel:
        return self.add_label("accept", True, comment)

    def reject(self, comment: str | None = None) -> PromptedLabel:
        return self.add_label("reject", False, comment)

    def correct(self, corrected_output: Any, comment: str | None = None) -> PromptedLabel:
        return self.add_label("correct_output", corrected_output, comment)


class SQLitePromptedStore:
    """Tiny local store. Use ':memory:' for red/green tests and demos."""
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        create table if not exists prompted_runs (
            run_id text primary key, node_name text not null, payload text not null, created_at text not null
        );
        create table if not exists prompted_labels (
            label_id text primary key, run_id text not null, label_type text not null, payload text not null, created_at text not null
        );
        """)
        self.conn.commit()

    @classmethod
    def in_memory(cls) -> "SQLitePromptedStore":
        return cls(":memory:")

    def put_run(self, run: PromptedRun) -> None:
        self.conn.execute(
            "insert or replace into prompted_runs(run_id, node_name, payload, created_at) values (?, ?, ?, ?)",
            (run.run_id, run.node_name, run.model_dump_json(), run.created_at.isoformat()),
        )
        self.conn.commit()

    def get_run(self, run_id: str) -> PromptedRun | None:
        row = self.conn.execute("select payload from prompted_runs where run_id = ?", (run_id,)).fetchone()
        return PromptedRun.model_validate_json(row["payload"]) if row else None

    def put_label(self, label: PromptedLabel) -> None:
        self.conn.execute(
            "insert or replace into prompted_labels(label_id, run_id, label_type, payload, created_at) values (?, ?, ?, ?, ?)",
            (label.label_id, label.run_id, label.label_type, label.model_dump_json(), label.created_at.isoformat()),
        )
        self.conn.commit()

    def list_runs(self, node_name: str | None = None) -> list[PromptedRun]:
        if node_name:
            rows = self.conn.execute("select payload from prompted_runs where node_name = ? order by created_at", (node_name,)).fetchall()
        else:
            rows = self.conn.execute("select payload from prompted_runs order by created_at").fetchall()
        return [PromptedRun.model_validate_json(row["payload"]) for row in rows]

    def list_labels(self, run_id: str | None = None) -> list[PromptedLabel]:
        if run_id:
            rows = self.conn.execute("select payload from prompted_labels where run_id = ? order by created_at", (run_id,)).fetchall()
        else:
            rows = self.conn.execute("select payload from prompted_labels order by created_at").fetchall()
        return [PromptedLabel.model_validate_json(row["payload"]) for row in rows]

    def export_jsonl(self) -> Iterable[str]:
        for run in self.list_runs():
            yield json.dumps({"type": "run", "payload": run.model_dump(mode="json")})
        for label in self.list_labels():
            yield json.dumps({"type": "label", "payload": label.model_dump(mode="json")})


class PromptedNode:
    """Typed callable that records runs, accepts labels, and exports as an agent tool."""
    def __init__(self, fn: Callable[..., Any], *, description: str | None = None, resources: list[ResourceRef] | None = None, store: SQLitePromptedStore | None = None, strict: bool = True, implementation_version: str = "python@v1") -> None:
        self.fn, self.name = fn, fn.__name__
        self.description = description or inspect.getdoc(fn) or self.name
        self.resources = resources or []
        self.store = store or SQLitePromptedStore.in_memory()
        self.strict = strict
        self.implementation_version = implementation_version
        self.signature = inspect.signature(fn)
        self.type_hints = get_type_hints(fn)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.run(*args, **kwargs).output

    @property
    def spec(self) -> PromptedNodeSpec:
        return PromptedNodeSpec(
            name=self.name, description=self.description, input_schema=self._input_schema(), output_schema=self._output_schema(),
            resources=self.resources, strict=self.strict, implementation_version=self.implementation_version,
        )

    def to_openai_tool(self, *, format: Literal["responses", "chat_completions"] = "responses") -> dict[str, Any]:
        function = {"name": self.name, "description": self.description, "strict": self.strict, "parameters": self._input_schema()}
        return {"type": "function", "function": function} if format == "chat_completions" else {"type": "function", **function}

    def run(self, *args: Any, **kwargs: Any) -> PromptedRun:
        input_payload = self._bound_input(*args, **kwargs)
        started = time.perf_counter()
        try:
            output = self._validate_output(self.fn(*args, **kwargs))
            run = PromptedRun(
                node_name=self.name, input=input_payload, output=_jsonable(output), resource_refs=self.resources,
                proposed_deltas=_extract_deltas(output), implementation_version=self.implementation_version,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as exc:  # pragma: no cover
            run = PromptedRun(
                node_name=self.name, input=input_payload, resource_refs=self.resources, implementation_version=self.implementation_version,
                status="error", error=repr(exc), latency_ms=(time.perf_counter() - started) * 1000,
            )
        self.store.put_run(run)
        return run

    def add_label(self, run: PromptedRun, label_type: str, value: Any = None, comment: str | None = None) -> PromptedLabel:
        label = run.add_label(label_type, value=value, comment=comment)
        self.store.put_label(label)
        return label

    def _bound_input(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        bound = self.signature.bind(*args, **kwargs)
        bound.apply_defaults()
        return {k: _jsonable(v) for k, v in bound.arguments.items()}

    def _input_schema(self) -> dict[str, Any]:
        properties, required = {}, []
        for name, parameter in self.signature.parameters.items():
            if name == "self":
                continue
            properties[name] = _schema_for(self.type_hints.get(name, Any))
            if parameter.default is inspect.Parameter.empty:
                required.append(name)
        schema: dict[str, Any] = {"type": "object", "properties": properties, "required": required}
        if self.strict:
            schema["additionalProperties"] = False
        return schema

    def _output_schema(self) -> dict[str, Any] | None:
        annotation = self.type_hints.get("return")
        return None if annotation is None or annotation is inspect.Signature.empty else _schema_for(annotation)

    def _validate_output(self, output: Any) -> Any:
        annotation = self.type_hints.get("return")
        return output if annotation is None or annotation is inspect.Signature.empty else TypeAdapter(annotation).validate_python(output)


def prompted_node(_fn: Callable[..., Any] | None = None, **options: Any):
    """Decorate a typed pure function as a self-improving prompted node."""
    def decorate(fn: Callable[..., Any]) -> PromptedNode:
        return PromptedNode(fn, **options)
    return decorate(_fn) if _fn is not None else decorate


@dataclass(frozen=True)
class PromptedEdge:
    source: str
    target: str
    target_arg: str | None = None


class PromptedGraph:
    """Lightweight acyclic graph of PromptedNode objects."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.nodes: dict[str, PromptedNode] = {}
        self.edges: list[PromptedEdge] = []

    def add_node(self, node: PromptedNode) -> PromptedNode:
        self.nodes[node.name] = node
        return node

    def edge(self, source: PromptedNode | str, target: PromptedNode | str, target_arg: str | None = None) -> None:
        self.edges.append(PromptedEdge(source if isinstance(source, str) else source.name, target if isinstance(target, str) else target.name, target_arg))

    def topological_order(self) -> list[str]:
        indegree = {name: 0 for name in self.nodes}
        children: dict[str, list[str]] = defaultdict(list)
        for edge in self.edges:
            children[edge.source].append(edge.target)
            indegree[edge.target] += 1
        queue, order = deque([name for name, degree in indegree.items() if degree == 0]), []
        while queue:
            node = queue.popleft(); order.append(node)
            for child in children[node]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if len(order) != len(self.nodes):
            raise ValueError("PromptedGraph only supports DAGs; cycle detected.")
        return order

    def run(self, inputs: dict[str, dict[str, Any]]) -> dict[str, PromptedRun]:
        runs, outputs = {}, {}
        incoming: dict[str, list[PromptedEdge]] = defaultdict(list)
        for edge in self.edges:
            incoming[edge.target].append(edge)
        for name in self.topological_order():
            kwargs = dict(inputs.get(name, {}))
            for edge in incoming[name]:
                kwargs[edge.target_arg or edge.source] = outputs[edge.source]
            runs[name] = self.nodes[name].run(**kwargs)
            outputs[name] = runs[name].output
        return runs


def _schema_for(annotation: Any) -> dict[str, Any]:
    if annotation is Any:
        return {}
    try:
        return TypeAdapter(annotation).json_schema()
    except Exception:
        return {}


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _extract_deltas(output: Any) -> list[ResourceDelta]:
    if isinstance(output, BaseModel):
        maybe_delta = getattr(output, "graph_delta", None) or getattr(output, "resource_delta", None)
        if isinstance(maybe_delta, ResourceDelta):
            return [maybe_delta]
        if isinstance(maybe_delta, list):
            return [d for d in maybe_delta if isinstance(d, ResourceDelta)]
    return []


__all__ = [
    "GraphOperation", "JsonDict", "PromptedEdge", "PromptedGraph", "PromptedLabel", "PromptedNode", "PromptedNodeSpec",
    "PromptedRun", "ResourceDelta", "ResourceRef", "SQLitePromptedStore", "prompted_node",
]
