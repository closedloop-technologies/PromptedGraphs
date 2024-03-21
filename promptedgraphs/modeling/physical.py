def physical(entity_relationship_graph: dict, schema: dict) -> str:
    """Generates a physical database schema in third-normal form from an ER graph and logical schema.

    Args:
        entity_relationship_graph (dict): The entity-relationship graph.
        schema (dict): The logical schema.

    Returns:
        str: The physical database schema in third-normal form.
    """
