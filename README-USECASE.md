

## Steps

1. Given data from an API endpoint
   * Description of the endpoint (url, method, parameters, etc.)
   * Example **Raw Data** from the endpoint
2. Generate a Pydantic **DataModel** from the example data
3. Repeat for two other endpoints
4. Construct a **DataGraph** from the **DataModels** to represent the relationships between the data
5. Generate a **PropertyGraph-Schema** from the **DataGraph** and represent as an ER-Diagram.
6. Create a schema alignment between the **PropertyGraph-Schema** and the properties of the **DataGraph**.     
    a. Indicate how the data models should be transformed to fit the schema.
    b. TODO handle cases where keys and values need to be 'pivoted' to fit the schema.
7. Generate a **Database-Schema** from the **PropertyGraph-Schema**.  The data should be third-form-normal as a default.
8. Create a **Database** from the **Database-Schema**
9. Implement ETL tasks to transform, and load data from the API endpoints into the database.
   1. Transform should get the example data and convert it to an in-memory tables reflecting the database schema.  These are the **staging** tables.
   2. Load should first `resolve` any existing data and update primary keys with the existing keys.
   3. Human in the loop for any ambiguous keys.
   4. Insert the data into the database.
   5. Optionally Update any existing data.

In this library, we should be able to manually chain together these functions and generate the necessary code.

The library **AutoETL** should be able to automatically chain these functions together and run them in a pipeline.  The library should also be able to generate the code for the pipeline.