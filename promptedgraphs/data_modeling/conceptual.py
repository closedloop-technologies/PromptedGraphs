"""There are many ways to represent a data model and to rationalize the space
in which the data and the model exist.

We can apply the following frameworks to help us understand the data model:

1. Domain-Driven Design: A design approach that focuses on the domain model and the language used to describe it.
2. Taxonomy: A hierarchical structure that organizes data into categories.
3. Ontology: A formal representation of the knowledge in a domain.
4. Entity-Relationship Graph: A graph that represents the relationships between entities.
"""
import json

from typing import List, Optional, Union

import networkx as nx
from pydantic import BaseModel, Field

from promptedgraphs.config import Config
from promptedgraphs.extraction.data_from_text import extraction_chat
from promptedgraphs.generation.schema_from_model import schema_from_model
from promptedgraphs.llms.chat import Chat
from promptedgraphs.llms.openai_chat import LanguageModel
from promptedgraphs.llms.usage import Usage
from promptedgraphs.models import ChatMessage
from promptedgraphs.normalization.object_to_data import object_to_data
from promptedgraphs.normalization.vis_graphs import data_graph_as_markdown


domain_model_system_message = """
You are a data modeler, ontologist and database expert.  
Given the following data model, construct a Domain-Driven Design (DDD) 
to describe the Domain, Subdomains and Bounded Context and Ubiquitous Language which surround the provided Data Model

Note a great DDD must:
* Include all of the entities directly referenced in the data model.
* Include any entities indirectly referenced or implied by the data model and the domain.
* Can be easily translated into a third form normalized database schema (3FN)
* The domain must be clearly defined and broad enough to encompass all of the data model and it's related use cases.
* Entities must represent not just data but the business objects and concepts that the data represents.

## Schema of the Domain-Driven Design model to build from the provided Data Model
```json
{schema}
```

Return a JSON object with the following properties.  Preserve the order of the properties:
 * bounded_context_name
 * domain
 * subdomains
 * ubiquitous_language
 * entities

"""


class Domain(BaseModel):
    name: str = Field(
        ...,
        title="Domain Name",
        description="The domain is the sphere of knowledge and activity around which the application logic revolves. It is the subject area to which the user applies a program or system. The domain is the context in which the application is used.",
    )
    description: str = Field(
        ...,
        title="Domain Description",
        description="A description of the domain.  The domain is the sphere of knowledge and activity around which the application logic revolves. It is the subject area to which the user applies a program or system. The domain is the context in which the data or application is used.",
    )


class DomainDrivenDesignModel(BaseModel):
    bounded_context_name: str = Field(
        ...,
        title="Bounded Context",
        description="This is a central pattern in DDD. It defines the boundaries within which a particular domain model is defined and applicable. It includes the explicitly defined boundaries in which domain terms and logic apply unambiguously. Bounded Contexts help to manage complexity by limiting the scope of concepts and terms to specific areas of the domain.",
    )
    domain: Domain = Field(
        ...,
        title="Domain",
        description="The parent domain of the data model as conceived by the Domain-Driven-Design paradigm.",
    )
    subdomains: list[Domain] = Field(
        ...,
        title="Subdomains",
        description="The distinct subdomains of the data model",
    )
    ubiquitous_language: dict[str, str] = Field(
        default={},
        title="Key Terms and Definitions",
        description="A language structured around the domain model and used by all team members and users in the domain and subdomains.",
    )
    entities: dict[str, str] = Field(
        default={},
        title="Domain Relevant Entities",
        description="Objects that are not merely defined by their attributes, but by a thread of continuity and identity. Entities have an identity that runs consistently through time and different states.",
    )


taxonomy_system_message = """
You are a data modeler, ontologist and database expert.  
A great taxonomy is foundational in organizing knowledge and data in a structured, meaningful way, facilitating effective communication, retrieval, and understanding across various systems and stakeholders.
Here's what defines each and makes them effective:

# Great Taxonomy
A taxonomy is a hierarchical classification or categorization of entities on the basis of shared characteristics. It is typically used to organize knowledge into groups and subgroups. Here are the key features of a great taxonomy:

 * **Clarity** and Conciseness: Each category and subcategory should be clearly and concisely defined to avoid ambiguity.
 * **Comprehensiveness**: It should cover all possible categories and subcategories relevant to the domain without significant gaps.
 * **Consistency**: Categories should be consistently applied across the same level of hierarchy; they should be mutually exclusive and collectively exhaustive wherever possible.
 * **Scalability**: The taxonomy should be designed to accommodate future expansion or modification as new knowledge or needs arise.
 * **Usability**: It should be easy to use and navigate, allowing users to find information efficiently and intuitively.
 * **Interoperability**: Should be designed to work well within existing systems or frameworks and align with any relevant standards to ensure it can be used across different platforms and applications.

## Schema of a Taxonomy to generate from the provided Data Model
```json
{schema}
```

Return a JSON object.  It is hierarchical in nature and should include include several depths of categories and subcategories and entitites.
"""


class Category(BaseModel):
    """example: EntityTypes like Person, Place, etc..."""

    name: str
    description: Optional[str] = None
    subcategories: List["Category"] = []  # Recursive model definition


class Taxonomy(BaseModel):
    domain: str
    categories: List[Category]


ontology_system_message = """
You are an expert in data modeling, ontology, and databases.

Here are the key qualities of an effective Ontology:
- **Accuracy**: Precisely mirrors real-world domain concepts and their relationships.
- **Consistency**: Free from contradictions; maintains logical coherence.
- **Formality**: Clearly defined for accurate machine interpretation.
- **Reusability**: Adaptable for use across various contexts.
- **Extensibility**: Flexible enough to evolve with domain knowledge.
- **Interoperability**: Integrates well with other systems for seamless data exchange.
- **Documentation**: Well-documented to clarify structure, terms, and design intentions.

## Schema of an Ontology to generate from the provided Data Model, Domain Model and Taxonomy
```json
{schema}
```

### Key Points
 * Use concepts and relationship types from common ontologies like OWL, RDF, etc...
 * Prefer fewer Concepts and more relationships and properties.
 * Prefer Concepts in their cannonical and sigular form over plural.

Return a JSON format and DO NOT include $def references.  Include all concepts, relationships and properties as nested objects.
"""


class Concept(BaseModel):
    name: str
    description: Optional[str] = None


class Relationship(BaseModel):
    subject: str
    predicate: str
    object: str


class Property(BaseModel):
    name: str
    range: str | List[str] = Field(
        ...,
        description="The range of the property.  Can be a primitive data type or a concept",
    )


class Ontology(BaseModel):
    name: str
    concepts: List[Concept]
    relationships: List[Relationship]
    properties: List[Property]


erp_system_message = """
You are an expert in data modeling, ontology, and databases.  
You are building an Entity Relationship Diagram from the provided Data Model, Domain Model, Taxonomy and Ontology.

An effective Entity Relationship Diagram (ERD) for a normalized schema should possess the following key qualities:

 * **Clarity**: Clear depiction of entities, attributes, and relationships using consistent and familiar symbols.
 * **Completeness**: Inclusion of all necessary entities, relationships, and key attributes relevant to the domain.
 * **Correctness**: Accurate representation of business rules and data relationships, including correct cardinality and participation.
 * **Normalization**: Adherence to normalization principles to minimize redundancy and avoid data anomalies.
 * **Minimal Redundancy**: Avoidance of unnecessary data duplication.
 * **Scalability**: Capability to accommodate future growth and changes in data requirements.
 * **Consistency**: Uniform application of naming conventions, symbols, and notations.
 * **Integration Readiness**: Design supports easy integration with other data models or systems.
 * **Documentation**: Comprehensive documentation of entities, relationships, and constraints.
 * **Visual Organization**: Logical and readable layout to enhance understanding and usability.


## Schema of an Entity Relationship Diagram
Generate this from the provided Data Model, Domain Model and Taxonomy
```json
{schema}
```

### Key Points
 * The ERD should be normalized to 3rd normal form.
 * Use standard ERD symbols and notation.
 * Should be easily translated into a database schema.

Return a JSON format
"""

class Attribute(BaseModel):
    name: str
    data_type: str
    description: Optional[str] = None

class Entity(BaseModel):
    name: str
    attributes: List[Attribute]

class Relationship(BaseModel):
    from_entity: str
    to_entity: str
    relationship_type: str = Field(..., description="Could be 'one-to-one', 'one-to-many', 'many-to-many'")
    description: Optional[str] = None

class EntityRelationshipDiagram(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
    diagram_name: Optional[str] = None
    description: Optional[str] = None

async def data_graph_to_domain_model(
    g: nx.DiGraph | nx.MultiDiGraph,
    model=LanguageModel.GPT35_turbo,
    chat: Chat = None,
    usage: Usage = None,
    temperature=0.0,
    reflect=True,
) -> DomainDrivenDesignModel:
    usage = usage or Usage(model=model)
    chat = chat or Chat()
    usage.start()
    schema = schema_from_model(DomainDrivenDesignModel)
    md = data_graph_as_markdown(g)
    system_message = domain_model_system_message.format(
        schema=json.dumps(schema, indent=4),
    )
    domain_models = await extraction_chat(
        md,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=[],
        temperature=temperature,
    )
    domain_models = list(domain_models)
    if not domain_models and not reflect:
        usage.end()
        return None

    if len(domain_models):
        domain_model = await object_to_data(
            domain_models[0],
            data_model=DomainDrivenDesignModel
        )
    else:
        domain_model = None

    if not reflect:
        usage.end()
        return domain_model

    message_history: list[ChatMessage] = [
        {"role": "user", "content": md},
        {
            "role": "assistant",
            "content": domain_model.model_dump_json(indent=4),
        },
    ]

    new_msg = """
Please reflect on the output above and correct any errors or omissions.
In particular are there any missing entities that would help when structuring the data model?
First provide an explanation, than the corrected JSON object.""".strip()

    new_domain_models = await extraction_chat(
        new_msg,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=message_history,
        temperature=temperature,
        force_json=False,
    )
    new_domain_models = list(new_domain_models)

    if len(domain_models):
        domain_model = await object_to_data(
            new_domain_models[0],
            data_model=DomainDrivenDesignModel
        )
    else:
        domain_model = None
    
    usage.end()
    return domain_model


async def data_graph_to_taxonomy(
    data_graph: nx.DiGraph | nx.MultiDiGraph,
    model=LanguageModel.GPT35_turbo,
    chat: Chat = None,
    usage: Usage = None,
    temperature=0.0,
    reflect=True,
) -> Taxonomy:
    usage = usage or Usage(model=model)
    chat = chat or Chat()
    usage.start()
    schema = schema_from_model(Taxonomy)
    md = data_graph_as_markdown(data_graph)
    system_message = taxonomy_system_message.format(
        schema=json.dumps(schema, indent=4),
    )
    taxonomies = await extraction_chat(
        md,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=[],
        temperature=temperature,
    )
    taxonomies = list(taxonomies)
    if not taxonomies and not reflect:
        usage.end()
        return None

    if len(taxonomies):
        taxonomy = await object_to_data(
            taxonomies[0],
            data_model=Taxonomy
        )
    else:
        taxonomy = None

    if not reflect:
        usage.end()
        return taxonomy

    message_history: list[ChatMessage] = [
        {"role": "user", "content": md},
        {
            "role": "assistant",
            "content": taxonomy.model_dump_json(indent=4) if taxonomy else '{}',
        },
    ]

    new_msg = """
Please reflect on the output above and correct any errors or omissions.
In particular are there any missing categories, sub-categories or entities that would help when structuring the data model?
First provide an explanation, than the corrected JSON object.""".strip()

    new_taxonomies = await extraction_chat(
        new_msg,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=message_history,
        temperature=temperature,
        force_json=False,
    )
    new_taxonomies = list(new_taxonomies)
    if len(taxonomies):
        new_taxonomy = await object_to_data(
            new_taxonomies[0],
            data_model=Taxonomy
        )
    else:
        new_taxonomy = None
    usage.end()
    return new_taxonomy


async def build_ontology(
    data_graph: nx.DiGraph | nx.MultiDiGraph,
    domain_model: DomainDrivenDesignModel = None,
    taxonomy: Taxonomy = None,
    model=LanguageModel.GPT35_turbo,
    chat: Chat = None,
    usage: Usage = None,
    temperature=0.0,
    reflect=True,
) -> Ontology:
    usage = usage or Usage(model=model)
    chat = chat or Chat()
    usage.start()

    schema = schema_from_model(Ontology)

    message_text = f"""{data_graph_as_markdown(data_graph)}\n\n
## Domain-Driven Design Model\n```json\n{domain_model.model_dump_json(indent=4)}\n```\n\n
## Taxonomy\n```json\n{taxonomy.model_dump_json(indent=4)}\n```
    """.strip()

    system_message = ontology_system_message.format(
        schema=json.dumps(schema, indent=4),
    )
    ontologies = await extraction_chat(
        message_text,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=[],
        temperature=temperature,
    )
    ontologies = list(ontologies)
    if not ontologies and not reflect:
        usage.end()
        return None

    # object_to_data
    if ontologies is None or not ontologies:
        usage.end()
        ontology = None
    else:
        ontology = await object_to_data(
            ontologies[0],
            data_model=Ontology
        )
    if not reflect:
        usage.end()
        return ontology

    message_history: list[ChatMessage] = [
        {"role": "user", "content": message_text},
        {
            "role": "assistant",
            "content": ontology.model_dump_json(indent=4) if ontology else '{}',
        },
    ]

    new_msg = """
Please reflect on the output above and correct any errors or omissions.
In particular are there any missing categories, sub-categories or entities that would help when structuring the data model?
First provide an explanation, than the corrected JSON object.""".strip()

    new_ontologies = await extraction_chat(
        new_msg,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=message_history,
        temperature=temperature,
        force_json=False,
    )
    new_ontologies = list(new_ontologies)

    if len(new_ontologies):
        new_ontology = await object_to_data(
            new_ontologies[0],
            data_model=Ontology
        )
    else:
        new_ontology = None
    usage.end()
    return new_ontology


async def build_entity_relationship_graph(
    data_graph: nx.DiGraph | nx.MultiDiGraph,
    domain_model: DomainDrivenDesignModel = None,
    taxonomy: Taxonomy = None,
    ontology: Ontology = None,
    model=LanguageModel.GPT35_turbo,
    chat: Chat = None,
    usage: Usage = None,
    temperature=0.0,
    reflect=True,
) -> EntityRelationshipDiagram:
    usage = usage or Usage(model=model)
    chat = chat or Chat()
    usage.start()

    schema = schema_from_model(EntityRelationshipDiagram)

    message_text = f"""{data_graph_as_markdown(data_graph)}\n\n
## Domain-Driven Design Model\n```json\n{domain_model.model_dump_json(indent=4)}\n```\n\n
## Taxonomy\n```json\n{taxonomy.model_dump_json(indent=4)}\n```\n\n
## Ontology\n```json\n{ontology.model_dump_json(indent=4)}\n```
    """.strip()

    system_message = erp_system_message.format(
        schema=json.dumps(schema, indent=4),
    )
    ergs = await extraction_chat(
        message_text,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=[],
        temperature=temperature,
    )
    ergs = list(ergs)
    if not ergs and not reflect:
        usage.end()
        return None

    if len(ergs):
        erg = await object_to_data(
            ergs[0],
            data_model=EntityRelationshipDiagram
        )
    else:
        erg = None

    if not reflect:
        usage.end()
        return erg

    message_history: list[ChatMessage] = [
        {"role": "user", "content": message_text},
        {
            "role": "assistant",
            "content": erg.model_dump_json(indent=4) if erg else '{}',
        },
    ]

    new_msg = """
Please reflect on the output above and correct any errors or omissions.
In particular are there any missing categories, sub-categories or entities that would help when structuring the data model?
First provide an explanation, than the corrected JSON object.""".strip()

    new_ergs = await extraction_chat(
        new_msg,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=message_history,
        temperature=temperature,
        force_json=False,
    )
    new_ergs = list(new_ergs)
    if len(new_ergs):
        new_erg = await object_to_data(
            new_ergs[0],
            data_model=EntityRelationshipDiagram
        )
    else:
        new_erg = None
    usage.end()
    return new_erg

async def main():
    g = nx.MultiDiGraph()
    dm = await data_graph_to_domain_model(g)
    tx = data_graph_to_taxonomy(g)


if __name__ == "__main__":
    asyncio.run(main())
