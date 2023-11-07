import asyncio
import json
import logging
import re
import traceback
from pathlib import Path
from typing import Any

import black
import isort
import networkx as nx
import tqdm
from pydantic import BaseModel, Field

from promptedgraphs.llms.coding import fix_code

logger = logging.getLogger(__name__)

# Restrictive environment
allowed_globals = {
    "__import__": __import__,
    "BaseModel": BaseModel,
    "Field": Field,
    "bytes": bytes,
}


def kindofsafe_exec(code, dependencies: dict = None):
    variables = {}
    dependencies = dependencies or allowed_globals

    for snippet in code.split(
        "\n\n"
    ):  # Loading in code by chunks helps with dependency resolution
        dependencies.update(variables)
        exec(snippet, dependencies, variables)
    return variables


def is_pydantic_base_model(cls: Any) -> bool:
    return isinstance(cls, type) and issubclass(cls, BaseModel)


def extract_fields_and_type(cls: type[BaseModel]) -> list[tuple[str, type, str]]:
    results = []
    if type(cls) == type(BaseModel):
        return []
    schema = cls.model_json_schema()
    properties = schema.get("properties", {})
    for field_name, field_info in properties.items():
        if field_info["type"] == "array":
            results.append((field_name, cls, "item"))
        else:
            results.append((field_name, cls, "object"))
    return results


def process_file(file_path):
    with open(file_path) as file:
        file_content = file.read()

    # Things can throw weird errors if multiple definitions of the same name are in the same file

    import networkx as nx

    g = nx.MultiDiGraph()
    local_vars = kindofsafe_exec(file_content)
    for name, cls in local_vars.items():
        if (
            isinstance(cls, type)
            and name != "BaseModel"
            and issubclass(cls, BaseModel)
            and hasattr(cls, "model_json_schema")
        ):
            schema = cls.model_json_schema()
            if schema.get("type") == "object":
                target = schema.get("title", cls.__name__)
                target_type = "entity"
                if target.endswith("Request"):
                    target = f"fn({target[:-7]})"
                    target_type = "fn"
                elif target.endswith("Response"):
                    target = f"fn({target[:-8]})"
                    target_type = "fn"
                if target not in g.nodes:
                    g.add_node(target, kind=target_type)
                for p_name, p_field in schema.get("properties", {}).items():
                    src = p_name
                    if src not in g.nodes:
                        g.add_node(src, kind="field")
                    g.add_edge(src, target, kind="property", data=json.dumps(p_field))

    for n, d in g.nodes(data=True):
        if d["kind"] == "fn" and n.startswith("fn("):
            target = n[3:-1]
            if target in g.nodes:
                g.add_edge(target, n, kind="reference")

    updates = add_entity_is_subset_edges(g)
    print("Added edges:", updates)

    nx.write_graphml(g, file_path.parent / "schema.graphml")

    sorted(g.degree, key=lambda x: x[1], reverse=True)
    entities = [
        n
        for n in sorted(g.degree, key=lambda x: x[1], reverse=True)
        if g.nodes[n[0]]["kind"] == "entity"
    ]

    # Give me shortest path count between entities and fields (those are their properties)
    entities = [
        n
        for n in sorted(g.degree, key=lambda x: x[1], reverse=True)
        if g.nodes[n[0]]["kind"] == "entity"
    ]
    print(schema)
    print(entities)


def add_entity_is_subset_edges(g: nx.DiGraph):
    # Extract node attributes for 'kind'
    node_kinds = nx.get_node_attributes(g, "kind")

    # Filter out nodes with kind 'fn' and 'field'
    field_nodes = [node for node, kind in node_kinds.items() if kind == "field"]
    entity_nodes = [node for node, kind in node_kinds.items() if kind == "entity"]

    # Create the adjacency matrix using pandas
    adjacency_matrix = nx.to_pandas_adjacency(g, nodelist=field_nodes + entity_nodes)
    # Extract relevant columns
    adjacency_matrix = adjacency_matrix.loc[field_nodes, entity_nodes]

    # Check for column subsets and record parent columns
    transpose_matrix = adjacency_matrix.transpose()
    found = {
        "is_equal": 0,
        "is_subset": 0,
    }
    # There is a vectorized version of this but not necessary for now
    for i, col1 in transpose_matrix.iterrows():
        if col1.sum() == 0:  # Skip empty columns
            continue
        for j, col2 in transpose_matrix.iterrows():
            if i != j and col2.sum() > 0:
                if all(col1 == col2):
                    g.add_edge(j, i, kind="is_equal")
                    found["is_equal"] += 1
                elif all(col1 <= col2) and any(col1 < col2):
                    g.add_edge(j, i, kind="is_subset")
                    found["is_subset"] += 1
    return found


def get_mappings_of_functions_to_objects(fname, code):
    requests = []
    responses = []
    other = []
    fn_name = fname.name.split(".")[0]

    obj = kindofsafe_exec(code)

    for k, v in obj.items():
        if k.endswith("Response"):
            responses.append(k)
        elif k.endswith("Request"):
            requests.append(k)
        elif is_pydantic_base_model(v) and k != "BaseModel":
            other.append(k)
    return {
        "name": fn_name,
        "requests": requests,
        "responses": responses,
        "other": other,
    }


def aggregate_fn_to_object_mappings(fdir):
    g = nx.MultiDiGraph()
    fdir = Path(fdir)
    for fname in fdir.glob("*.py"):
        if fname.name.startswith("_"):
            continue
        with open(fname) as f:
            m = get_mappings_of_functions_to_objects(fname, f.read())
            g.add_node(m["name"], kind="fn")
            for r in m["requests"]:
                g.add_node(r, kind="request")
                g.add_edge(m["name"], r, kind="request")
            for r in m["responses"]:
                g.add_node(r, kind="response")
                g.add_edge(m["name"], r, kind="response")
            for r in m["other"]:
                g.add_node(r, kind="other")
                g.add_edge(m["name"], r, kind="other")
    return g


def aggregate_python_files(fdir):
    fdir = Path(fdir)
    code = []
    for fname in fdir.glob("*.py"):
        with open(fname) as f:
            c = black.format_str(f.read(), mode=black.FileMode())
            code.append(c)
            try:
                black.format_str("\n\n".join(code), mode=black.FileMode())
            except Exception:
                logger.error(f"Static code error in: {fname}")
                return

    # move all imports to the top
    code = move_imports_to_top("\n\n".join(code))
    config = isort.Config(profile="black")
    code = isort.code(code, config=config)

    # reformat one more time
    code = black.format_str(code, mode=black.FileMode())

    with open(fdir / "_all.py", "w") as f:
        f.write(code)

    return fdir / "_all.py"


def move_imports_to_top(code):
    lines = code.split("\n")

    # Separating import lines and other lines
    import_lines = [
        line for line in lines if re.match(r"^(import |from .+ import)", line)
    ]
    other_lines = [
        line for line in lines if not re.match(r"^(import |from .+ import)", line)
    ]

    # Combining the lines and writing back to the file
    return "\n".join(import_lines + other_lines)


async def validate_python_files(fdir):
    fnames = sorted(fdir.glob("*.py"))
    for fname in tqdm.tqdm(fnames):
        if fname.name == "_all.py":
            continue
        code = Path(fname).read_text()

        history = []
        i = 0
        while i < 4:
            code = black.format_str(code, mode=black.FileMode())
            kindofsafe_exec(code)
            # break
            try:
                code = black.format_str(code, mode=black.FileMode())
                kindofsafe_exec(code)
                break
            except Exception as e:
                i += 1
                if i >= 4:
                    logger.error(f"Code error in: {fname}")
                    return

                logger.warning(f"fixing code error in: {fname} - take {i} - {e}")
                code, history = await fix_code(
                    code, error=e, tb=traceback.format_exc(), history=history
                )
        if i > 0:
            logger.warning(f"Fixed code error in: {fname}")
            with open(fname, "w") as f:
                f.write(code)


async def python_files_pipeline(fdir):
    await validate_python_files(fdir)
    graph_of_functions_and_objects = aggregate_fn_to_object_mappings(fdir)
    with open(fdir / "_function_graph.json", "w") as f:
        f.write(json.dumps(nx.node_link_data(graph_of_functions_and_objects)))
    nx.write_graphml(graph_of_functions_and_objects, fdir / "_function_graph.graphml")

    file_path = aggregate_python_files(fdir)
    results = process_file(file_path)
    print(results)
    return results


if __name__ == "__main__":
    fdir = Path("data_models/googlemaps.client.Client")
    asyncio.run(python_files_pipeline(fdir))

    # for r in results:
