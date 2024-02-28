import os

import networkx as nx
import psycopg2

# Use environment variables for database connection details for better security


def db_connect():
    dbname = os.getenv("DB_NAME", "chattcl_webapp")
    user = os.getenv("DB_USER", "chattcl_webapp")
    password = os.getenv("DB_PASSWORD", "61Y1bYvz8IqB8V0")
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5433"))

    return psycopg2.connect(
        dbname=dbname, user=user, password=password, host=host, port=port
    )


def execute_query(cursor, query, *params):
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return []


def add_tables_views_columns(G: nx.DiGraph, cursor):
    # Fetch all objects in all schemas, not just 'public'
    objects_query = """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_type IN ('BASE TABLE', 'VIEW')
    """
    for schema, name, type in execute_query(cursor, objects_query):
        qualified_name = f"{schema}.{name}"
        G.add_node(qualified_name, type=type.lower(), schema=schema)

    columns_query = """
        SELECT table_schema, table_name, column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
    """
    for (
        schema,
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default,
    ) in execute_query(cursor, columns_query):
        qualified_table_name = f"{schema}.{table_name}"
        column_id = f"{qualified_table_name}.{column_name}"
        G.add_node(
            column_id,
            type="column",
            data_type=data_type,
            is_nullable=is_nullable,
            default=column_default,
        )
        G.add_edge(qualified_table_name, column_id, relationship="contains")


def add_foreign_keys(G: nx.DiGraph, cursor):
    fk_query = """
        SELECT kcu.table_schema, kcu.table_name, kcu.column_name,
               ccu.table_schema AS foreign_table_schema,
               ccu.table_name AS foreign_table_name,
               ccu.column_name AS foreign_column_name
        FROM
            information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE constraint_type = 'FOREIGN KEY'
    """
    for (
        schema,
        table,
        column,
        foreign_schema,
        foreign_table,
        foreign_column,
    ) in execute_query(cursor, fk_query):
        column_id = f"{schema}.{table}.{column}"
        foreign_column_id = f"{foreign_schema}.{foreign_table}.{foreign_column}"
        G.add_edge(column_id, foreign_column_id, relationship="foreign_key")


def add_indexes(G: nx.DiGraph, cursor):
    indexes_query = """
        SELECT t.schemaname, t.tablename, i.indexname, a.attname
        FROM pg_indexes i
        JOIN pg_class c ON i.indexname = c.relname
        JOIN pg_index ix ON c.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = ANY(ix.indkey)
        JOIN pg_tables t ON t.tablename = i.tablename
        WHERE t.schemaname NOT IN ('pg_catalog', 'information_schema')
    """
    for schema, table_name, index_name, column_name in execute_query(
        cursor, indexes_query
    ):
        qualified_table_name = f"{schema}.{table_name}"
        index_id = f"{qualified_table_name}.{index_name}"
        column_id = f"{qualified_table_name}.{column_name}"
        G.add_node(index_id, type="index", schema=schema)
        G.add_edge(qualified_table_name, index_id, relationship="has_index")
        G.add_edge(index_id, column_id, relationship="indexes")


def generate_mermaid_diagram(G):  # sourcery skip: low-code-quality
    mermaid_str = "classDiagram\n"
    node_to_id = {}
    id_counter = 1

    # Generate class entries for tables and views
    for node, data in G.nodes(data=True):
        if data["type"] in ["base table", "view"]:
            node_id = f"class{str(id_counter)}"
            node_to_id[node] = node_id
            id_counter += 1
            mermaid_str += f"    {node_id} : {node}\n"

    # Generate class entries for columns
    for node, data in G.nodes(data=True):
        if data["type"] == "column":
            parent_tables = list(G.predecessors(node))
            if not parent_tables:
                continue
            table_node = parent_tables[0]  # Get the table/view the column belongs to
            if table_id := node_to_id.get(table_node):
                mermaid_str += f"    {table_id} : +{node}\n"

    # Generate relationships
    for src, dest, data in G.edges(data=True):
        src_type = G.nodes[src]["type"]
        dest_type = G.nodes[dest]["type"]
        if src_type in ["base table", "view"] and dest_type in ["base table", "view"]:
            src_id = node_to_id.get(src)
            dest_id = node_to_id.get(dest)
            if src_id and dest_id:
                relation = "--" if data["relationship"] == "foreign_key" else "-->"
                mermaid_str += f"    {src_id} {relation} {dest_id}\n"

    # Generate relationships for foreign keys
    for src, dest, data in G.edges(data=True):
        if data["relationship"] == "foreign_key":
            # Extract table names from column nodes
            src_table = src.rsplit(".", 1)[0]
            dest_table = dest.rsplit(".", 1)[0]
            src_id = node_to_id.get(src_table)
            dest_id = node_to_id.get(dest_table)
            if src_id and dest_id:
                # Add an arrow to denote the foreign key relationship
                mermaid_str += f"    {src_id} --> {dest_id} : FK\n"

    return mermaid_str


def generate_mermaid_diagram_with_fk(G):
    mermaid_str = "classDiagram\n"
    node_to_id = {}
    id_counter = 1

    # Generate class entries for tables and views
    for node, data in G.nodes(data=True):
        if data["type"] in ["base table", "view"]:
            node_id = f"Class{id_counter}"  # Use a more descriptive prefix
            node_to_id[node] = node_id
            id_counter += 1
            mermaid_str += f'    {node_id} "{node}"\n'

    # Generate attributes for columns and remember foreign keys for later
    for node, data in G.nodes(data=True):
        if data["type"] == "column":
            # Extract table name and column name
            table_node, column_name = node.rsplit(".", 1)
            if table_id := node_to_id.get(table_node):
                # If the node is a column, add it as an attribute to its table
                mermaid_str += f"    {table_id} : +{column_name}\n"

    # Generate relationships for foreign keys
    for src, dest, data in G.edges(data=True):
        if data["relationship"] == "foreign_key":
            # Extract table names from column nodes
            src_table = src.rsplit(".", 1)[0]
            dest_table = dest.rsplit(".", 1)[0]
            src_id = node_to_id.get(src_table)
            dest_id = node_to_id.get(dest_table)
            if src_id and dest_id:
                # Add an arrow to denote the foreign key relationship
                mermaid_str += f"    {src_id} --> {dest_id} : FK\n"

    return mermaid_str


def prune_graph(G, schema="public", exclude_nodes: set[str] = None):
    exclude_nodes = set(exclude_nodes or [])
    nodes_and_data = list(G.nodes(data=True))
    in_schema_nodes = set()
    for node, data in nodes_and_data:
        if node in exclude_nodes:
            continue
        if (schema is None or data.get("schema") == schema) and data.get("type") in [
            "base table",
            "view",
        ]:
            in_schema_nodes.add(node)

    for node, data in nodes_and_data:
        if node in in_schema_nodes:
            continue
        if {
            n
            for n in G.predecessors(node)
            if n in in_schema_nodes and n not in exclude_nodes
        }:
            continue
        if {
            n
            for n in G.successors(node)
            if n in in_schema_nodes and n not in exclude_nodes
        }:
            continue
        G.remove_node(node)
    return G


def load_schema_graph(conn, schema: str = None, exclude_nodes: set[str] = None):
    G = nx.DiGraph()
    with conn.cursor() as cur:
        add_tables_views_columns(G, cur)
        add_foreign_keys(G, cur)
        add_indexes(G, cur)
    return prune_graph(G, schema=schema, exclude_nodes=exclude_nodes)


if __name__ == "__main__":
    conn = db_connect()
    G = load_schema_graph(
        conn, schema="public", exclude_nodes=["public._prisma_migrations", "public.Otp"]
    )

    print(len(G.nodes), len(G.edges))
    # Assuming G is your networkx graph
    mermaid_diagram = generate_mermaid_diagram(G)
    with open("mermaid_diagram.mmd", "w") as f:
        f.write(mermaid_diagram)
