# Working full example for the Sports example

Data Sources
1. OddsAPI
2. Q4 Sports
3. Genius Sports


## Ingestion Workflow

1. Define each DataSource as a 'Tool'
   - properties such as name, url, openscheume_url, docs, pipy, npm repos ,etc..
2. Build DataSource DAG
   - endpoints, models
3. Generate OpenAPI schema
   - Similar to `python -m openapi_python_client.generate -i ./openapi.yaml -o ./generated`
   - Generate api.py and models.py for each endpoint and datasource so that each endpoint has typeing and validation
   - Might require building `class BaseAPI` to handle auth, retries, monitoring, etc..
4. Generator
   - Build query plan - a dry run that iterates through each endpoint and respects dependencies and internal links
   - build partial prisma.schema to save results with api_endpoint consistent linking
     - update prisma.schema with new models and deploy to server
6. Deploy
   - Build prisma client
   - Build prisma schema
   - Deploy prisma schema
7. Runner
   - Run query plan and save results to prisma
   - On inserting send new ids to queue for downstream processing

## Tool Linking

1. For a given set of tools and a target domain (and potentially other materials that the define the uses of the data).
2. Propose an ontology of core entities, properties, and relationships that look to unify the data, and provide a common language for the tools to communicate.
3. Map the Tool -> DB (Table,Column) -> DSO (Entity,Property)
   1. Can also have a mapping of DB:Table -> DSO:Entity
   2. Can also have a mapping of DB:Column -> DSO:Property or DSO:Relationship

What if the column's value specifies the type of relationship? or if the simple co-occurrence of entity references columns in a query specifies a relationship?


other issues:
 * two columns could represent (key, value) pairs such that the key is a property of the entity and the value is the value of the property.
