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
from promptedgraphs.normalization.vis_graphs import data_graph_as_markdown


class EntityRelationshipGraph(BaseModel):
    pass


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

Return a JSON format
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


Ontology.model_rebuild()


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
    domain_model = await extraction_chat(
        md,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=[],
        temperature=temperature,
    )
    domain_model = list(domain_model)
    if not domain_model and not reflect:
        usage.end()
        return None

    domain_model = DomainDrivenDesignModel(**domain_model[0]) if domain_model else None
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

    new_domain_model = await extraction_chat(
        new_msg,
        chat=chat,
        system_message=system_message,
        message_template="""{text}""",
        usage=usage,
        message_history=message_history,
        temperature=temperature,
        force_json=False,
    )
    dms = list(new_domain_model)
    domain_model = DomainDrivenDesignModel(**dms[0]) if len(dms) else None
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

    taxonomy = Taxonomy(**taxonomies[0]) if taxonomies else None
    if not reflect:
        usage.end()
        return taxonomy

    message_history: list[ChatMessage] = [
        {"role": "user", "content": md},
        {
            "role": "assistant",
            "content": taxonomy.model_dump_json(indent=4),
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
    new_taxonomy = Taxonomy(**new_taxonomies[0]) if len(new_taxonomies) else None
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
##Domain-Driven Design Model\n```json\n{domain_model.model_dump_json(indent=4)}\n```\n\n
##Taxonomy\n```json\n{taxonomy.model_dump_json(indent=4)}\n```
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

    ontology = Ontology(**ontologies[0]) if ontologies else None
    if not reflect:
        usage.end()
        return ontology

    message_history: list[ChatMessage] = [
        {"role": "user", "content": message_text},
        {
            "role": "assistant",
            "content": ontology.model_dump_json(indent=4),
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
    new_ontology = Ontology(**new_ontologies[0]) if len(new_ontologies) else None
    usage.end()
    return new_ontology


def create_entity_relationship_graph(
    data_model: nx.DiGraph | nx.MultiDiGraph, taxonomy: Taxonomy, reflect=True
) -> EntityRelationshipGraph:
    raise NotImplementedError("create_entity_relationsip_graph")


async def main():
    g = nx.MultiDiGraph()
    dm = await data_graph_to_domain_model(g)
    tx = data_graph_to_taxonomy(g)


if __name__ == "__main__":
    asyncio.run(main())
