"""The goal of this is to construct a data graph from an openapi spec.

1. Ensure all outputs of API call are typed using pydantic
2. Ensure all inputs of API call are typed using pydantic
3. Ensure all endpoints are typed using pydantic and contain all inputs and outputs
4. Map common fields between inputs and outputs to create a SourceGraph of (object -> property) pairs
5. Label property nodes of SourceGraph into as {'auth', 'query', 'data', 'is_unique_id', ...}
6. Create DataGraph by normalizing the objecst and properties of the SourceGraph
   1. what are unique ids?
   2. core properties
7. Create a DataGraph from the SourceGraph
"""
