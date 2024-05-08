from pydantic import BaseModel, RootModel

def extract_references(schema: dict, references: set = None, max_depth=4) -> set:
    """Extracts all $ref references from a JSON schema."""
    if max_depth <= 0:
        return references if references is not None else set()
    
    if references is None:
        references = set()

    if "$ref" in schema:
        references.add(schema["$ref"])

    if "properties" in schema:
        for prop in schema["properties"].values():
            extract_references(prop, references, max_depth-1)

    if "items" in schema:
        extract_references(schema["items"], references, max_depth-1)

    return references

def resolve_references(schema: dict, schema_defs:dict=None, max_depth=4) -> dict:
    """Resolves $ref references from $def definitions in a JSONschema."""
    if max_depth <= 0:
        return schema
    if schema_defs is None:
        schema_defs = schema.get('$defs')
    if "$ref" in schema:
        ref = schema["$ref"]
        if resolved_ref := find_ref(ref, schema_defs):
            schema = resolved_ref
        else:
            raise ValueError(f"Reference not found: {ref}")
    if "properties" in schema:
        schema["properties"] = {
            k: resolve_references(v, schema_defs=schema_defs, max_depth=max_depth-1) for k, v in schema["properties"].items()
        }
    if "items" in schema:
        schema["items"] = resolve_references(schema["items"], schema_defs=schema_defs, max_depth=max_depth-1)
    return schema

def find_ref(ref_path: str, schema_defs:dict) -> dict:
    ref_path = ref_path.split('/')
    definition_name = ref_path[-1]  # Extract the last element as definition name
    if definition_name in schema_defs:
        return schema_defs[definition_name]
    raise ValueError(f"Definition not found: {definition_name}")


def schema_from_model(data_model: list[BaseModel] | BaseModel, resolve_refs=False) -> dict:
    """Generates a schema from a Pydantic DataModel.

    Args:
        model (BaseModel): The Pydantic BaseModel instance to generate a schema for.

    Returns:
        dict: The generated schema as a dictionary.
    """
    if isinstance(data_model, list) or str(data_model).startswith("list["):
        x = data_model.__args__[0]
        schema = RootModel[list[x]].model_json_schema()
    else:
        schema = data_model.model_json_schema()
    return resolve_references(schema) if resolve_refs else schema
