# PromptedGraphs v1 Motivated Case Studies

PromptedGraphs turns typed Python function signatures into self-improving DAG nodes. The first implementation can be a frontier LLM passthrough; each call is traced; user feedback becomes labels; corrected labels become tests; and later implementations can be generated, evaluated, and promoted when they beat the current implementation on quality, cost, and latency.

## Case study 1: Entity linking into a project knowledge graph

**Function:** `extract_and_link_entities(document: str) -> EntityLinkingResult`

**Motivation:** The original PromptedGraphs use case was bootstrapping ontologies, entity resolution, and knowledge graph construction from semi-structured text.

**Initial behavior:** The node calls a frontier LLM with the input document, the current ontology, and a snapshot of the local knowledge graph.

**Feedback:** The user accepts, rejects, or corrects linked entities and graph deltas.

**Improvement path:**

1. Trace LLM outputs and user corrections.
2. Generate regression tests from corrected outputs and graph deltas.
3. Generate deterministic Python rules for common entities and aliases.
4. Add selective LLM fallback only for low-confidence entities.
5. Optionally train a smaller entity linker once enough labels exist.

**Resource side effect:** The node may propose `ResourceDelta` operations against `project_kg`, but the runtime records and commits those deltas explicitly instead of silently mutating the graph.

## Case study 2: Customer-intent classifier that becomes cheaper over time

**Function:** `classify_intent(message: str) -> IntentResult`

**Initial behavior:** A frontier model classifies messages into a Pydantic enum-like schema.

**Feedback:** Accept/correct labels become unit tests.

**Improvement path:**

1. Prompt-only implementation.
2. Generated keyword/rule implementation for obvious cases.
3. Hybrid implementation: cheap rules first, LLM fallback for ambiguous messages.
4. Fine-tuned small model or classical classifier if the label set becomes large enough.

**Why it matters:** The caller keeps the same function signature while quality calibrates to the domain and cost declines.

## Case study 3: Research extraction DAG

**DAG:**

```text
extract_sources -> extract_entities -> link_entities -> infer_relationships -> propose_graph_delta
```

**Motivation:** Agent loops often need multiple typed tools, not one monolithic prompt. A DAG makes the intermediate artifacts inspectable and labelable.

**Feedback:** Each node can be corrected independently, and the full graph output can be labeled as acceptable or not.

**Improvement path:** Bottleneck nodes with high correction rates get prioritized for prompt improvement, generated code, or model training.

## Case study 4: Schema/ontology bootstrapper

**Function:** `propose_ontology(samples: list[str]) -> OntologyProposal`

**Initial behavior:** LLM proposes concepts, relationships, and properties.

**Feedback:** Domain experts correct the ontology proposal.

**Improvement path:** Accepted ontology changes become graph/schema deltas and regression cases. Later calls can reuse the local ontology and only ask the LLM to reason over novel cases.

## Red-green-refactor loop

### Red

Write a failing test for the desired behavior:

- function exports an OpenAI-compatible tool schema
- run is recorded with input, output, resources, and proposed deltas
- feedback labels are persisted
- DAG execution passes outputs between nodes
- graph cycles are rejected

### Green

Implement the smallest runtime surface:

- `@prompted_node`
- `PromptedRun`
- `PromptedLabel`
- `ResourceDelta`
- `SQLitePromptedStore`
- `PromptedGraph`

### Refactor

Split the runtime into stable layers:

- models: typed serializable contracts
- node: decorator/call/tool-schema surface
- store: local persistence
- graph: DAG orchestration
- resources: future adapters for SQLite KG, files, Kùzu, Neo4j, or vector stores

The key invariant is that every improvement candidate must preserve the public function signature and pass the label-derived regression suite before promotion.
