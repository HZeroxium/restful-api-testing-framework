SCHEMA_SCHEMA_DEPENDENCY_PROMPT = r'''
Given the schema and its properties in the OpenAPI specification of an API application, your task is to identify the prerequisite schemas, that need to be created before creating the mentioned schema.

Below is the schema and its properties needed to find prerequisite schemas:
{specific_schema}

Below is the list of all schemas and their properties specified in the OpenAPI specification:
{simplified_schemas}

Only respond the prerequisite schemas in separate lines, If no any prerequiste schemas is found, just respond "None". No explanation is needed.
'''

OPERATION_SCHEMA_DEPENDENCY = '''Your task is to analyze a specific endpoint within an API application, as defined in its Swagger Specification, and determine the necessary data schemas and matching keys required to obtain information pertinent to the endpoint's parameters.

Please review the following details for the endpoint and its associated parameters to identify the corresponding schemas needed for data retrieval:
{specific_endpoint_params}
{parameter_description}

Additionally, you are provided with a list of all data schemas and their attributes as described in the Swagger Specification of the API application:
{simplified_schemas}

Now, for each endpoint parameter, identify all possible matching keys within the given schemas that may used to retrieve the required information for the parameter.
The response is in the format below, no explanation is needed:
```
Retrieval schema's name: endpoint parameter -> matching schema key, another endpoint parameter -> matching schema key
Another retrieval schema's name: ...
```
Example: 
Pet: petId -> id, name -> name (the parameter 'petId' in the given endpoint corresponds to the 'id' field in the 'Pet' schema, and similarly, the parameter 'name' in the given endpoint corresponds to the 'name' field in the 'Pet' schema)
'''


GET_PARAM_DESCRIPTION_PROMPT = '''\
Based on the endpoint's specification provided below, your task is to create a brief description for each of its input parameters:

{specific_endpoint_params}

The response is in the format below:
- parameter name: your brief description...
'''

