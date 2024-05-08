from pprint import pformat

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import FancyBboxPatch


def graph_to_mermaid(g: nx.DiGraph | nx.MultiDiGraph, kind="graph"):
    """Converts a NetworkX graph to a Mermaid markdown string."""
    if kind == "graph":
        md = "graph TD\n"
    elif kind == "entity_relationship":
        md = "erDiagram\n"
    else:
        raise ValueError(f"kind must be 'graph' or 'entity_relationship', not {kind}")

    for node in g.nodes:
        node_data = g.nodes[node]
        node_id = str(node)
        node_label = node_data.get("name", node_id)
        md += f"    {node_id}[{node_label}]\n"

    for edge in g.edges:
        edge_data = g.edges[edge]
        source, target = edge
        md += f"    {source} --> {target}\n"
    return md


def visualize_data_graph(g):
    # Prepare a color map only for nodes where 'kind' == 'object'
    color_map = []
    unique_types = {g.nodes[n]["kind"] for n in g.nodes if g.nodes[n].get("kind")}
    unique_types.add("_unknown")
    # matplotlib.colormaps.get_cmap(obj)
    cm = plt.colormaps.get_cmap("viridis")
    type_colors = {
        node_type: cm(float(i) / len(unique_types))
        for i, node_type in enumerate(unique_types)
    }

    # Apply colors to nodes
    for node in g.nodes:
        node_data = g.nodes[node]
        color_map.append(type_colors[node_data.get("kind") or "_unknown"])

    # Draw the graph
    fig, ax = plt.subplots()
    pos = nx.nx_agraph.graphviz_layout(g, prog="dot")
    nx.draw(g, pos, node_color=color_map, ax=ax)

    # Define base node size and scaling factor for width
    base_width = 75
    height = 25

    for node in g.nodes:
        node_data = g.nodes[node]
        x, y = pos[node]
        if node_data.get("kind") == "object":
            num_children = len(list(g.successors(node)))
            width = base_width * num_children  # Width scaled by number of children
            color = type_colors[node_data["kind"]]
            box = FancyBboxPatch(
                (x - width / 2, y - height / 2),
                width,
                height,
                boxstyle="round,pad=0.1",
                color=color,
                ec="black",
                zorder=100,
            )
            ax.add_patch(box)
            plt.text(
                x,
                y,
                str(node).split("_")[0],
                ha="center",
                va="center",
                color="black",
                zorder=101,
                fontsize=10,
            )
    # Set limits and draw edges as normal
    ax.set_xlim(
        np.min([x for x, y in pos.values()]) - 50,
        np.max([x for x, y in pos.values()]) + 50,
    )
    ax.set_ylim(
        np.min([y for x, y in pos.values()]) - 50,
        np.max([y for x, y in pos.values()]) + 50,
    )

    plt.axis("off")
    return fig, ax

    # Now visualize the graph in markdown


def _tree_as_markdown(g, node, level=0):
    node_data = g.nodes[node]
    node_id = str(node)
    data_type = node_data.get("kind", "object")
    label = f"ID[{node_id}]: {node_data.get('name', '')}({data_type})".strip()
    if description := node_data.get("description"):
        label += f" - {description}"
    md = [f"{'  ' * level} * {label}"]

    if other_data := {
        k: v
        for k, v in dict(node_data).items()
        if k not in ("kind", "description", "schema_id", "parents", "name")
    }:
        prefix = f"{'  ' * (level+1)} * properties: "
        md.append(prefix + pformat(other_data, indent=len(prefix)))
    md.extend(
        _tree_as_markdown(g, child, level=level + 1) for child in g.successors(node)
    )
    return "\n".join(md)


def data_graph_as_markdown(g):
    root_candidates = [node for node, indegree in g.in_degree() if indegree == 0]
    md = ["## Data Graph"]
    md.extend(_tree_as_markdown(g, root) for root in root_candidates)
    return "\n".join(md)
