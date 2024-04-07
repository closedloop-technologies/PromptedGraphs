# PromptedGraphs

Do you have data coming in from multiple sources?  Do you need to extract structured data from unstructured text?  Do you need to update a database or knowledge graph with this data?  If so, PromptedGraphs is for you!

## Key Concepts

### Data Modeling Concepts
 * **Raw Data**: Any data coming from a source, such as text or arbitrary objects.
 * **DataModel**: A Pydantic DataModel is a schema for structured data. It is used to validate and serialize data.  This can be represented as a JSON Schema or a Pydantic DataModel.
 * **DataGraph**: This is a taxonomy-like structure used to organize multiple DataModels.  It connects properties from different DataModels via `same_as`, `part_of` and `is_in` relationships.  In this case we are using the term `graph` to refer to a network of nodes and edges where each node is a property of a DataModel and each edge is a relationship between two properties.

### Storage Concepts
Data can be stored in a Knowledge Graph (which follows an PropertyGraph-Schema) or in a Database (which follows a Database-Schema).

* **PropertyGraph-Schama**: This is a more formalized version of a DataGraph.  It is used to define the relationships between DataModels and their properties. Much like an Ontology, it typically includes a hierarchy of classes and properties and can merge or split DataModels as well as define new properties.  For Ontology-purists, this might feel a bit like a lightweight version of [OWL](https://www.w3.org/TR/owl-guide/).
 * **Database-Schema**: This represents a relational database schema.  It is used to define tables and columns and their relationships such as foreign keys and indexes.


## ETL-Related Tasks

 * **Extract** The purpose of this is to take raw data (such as text or arbitrary objects) and convert it into structured data. 

 * **Transform** We then transform this structured data into a format that can be used to update a database.

 * **Load** The transformed data is then used to update the database or knowledge graph.

## NLP-Related Tasks
Implementing the above ETL tasks for arbitrary data is easier said than done. This is where NLP comes in. We can use NLP to extract structured data from unstructured text. This can be done in a variety of ways:

* **Extraction**
  * `data_from_text`: Extract structured data from unstructured text.
  * `entities_from_text`: Extract entities from unstructured text.
  * **Relationship Extraction**: Either open ended labels or constrain to your domain

* **Transformation**
  * `schema_from_data`: Generate schemas from data samples.
    * We represent schemas as Pydantic DataModels and as JSON Schema.
  * `taxonomy`: 
  * `data_from_schema`: Generate data samples from schemas.
  * `normalize`: Convert data to fit schema specifications with light reformats.

* **Loading**
  * `update_database`: Update a database with structured data.
  * `update_graph`: Update a knowledge graph with structured data.
  * **Entity Linking**: Link references in text to entities in a graph
  * **Graph Construction**: Create or update knowledge graphs
  * **Entity Resolution**: Deduplication and normalization

* **Testing**
  * `generate`: Generate samples data from Pydantic DataModels.  This is the reverse direction from `schema_from_data`
  * **Validation**: Validate schemas and data against specifications or models.


## Installation

Install PromptedGraphs using pip:

```bash
pip install promptedgraphs
```

## Usage

Here's a quick example to get you started:

```python
from promptedgraphs.extraction import data_from_text
from myproject.models import MyDataModel

# Example text
text = "Your example text goes here."

# Extract data from text
data = data_from_text(text, model=MyDataModel)

print(data)
```

Replace `MyDataModel` with your Pydantic `DataModel` tailored to your specific needs.

## Documentation

For detailed documentation, visit [Link to Documentation].

## Contributing

Contributions are welcome! If you have ideas for new features or improvements, feel free to open an issue or submit a pull request.

## Support

If you need help or have any questions, please open an issue in the GitHub repository.

## License

PromptedGraphs is released under the [MIT License](LICENSE).
