# config/prompts/parameter_mapping.py

"""
Prompts used for parameter mapping in the RBCTest framework.
"""

PARAMETER_OBSERVATION = """Given the specification of an input parameter for a REST API, your responsibility is to provide a brief observation of that parameter.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"
"""

SCHEMA_OBSERVATION = """\
Given a schema in an OpenAPI Specification for a RESTful API service, your responsibility is to briefly explain the meaning of each attribute specified in the provided schema.

Below is the schema's specification:
- Schema name: "{schema}"
- Specification: {specification}
"""

PARAMETER_SCHEMA_MAPPING_PROMPT = """Given an input parameter and an API response schema, your responsibility is to check whether there is a corresponding attribute in the API response schema.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"

Follow these step to find the coresponding attribute of the input parameter:
STEP 1: Let's give a brief observation about the input parameter.

{parameter_observation}

STEP 2: Identify the corresponding attribute in the API response's schema.

Some cases can help determine a corresponding attribute:
- The input parameter is used for filtering, and there is a corresponding attribute that reflects the real value (result of the filter); but this attribute must be in the same object as the input parameter.
- The input parameter and the corresponding attribute maintain the same semantic meaning regarding their values.

Below is the specification of the schema "{schema}":
{schema_observation}

If there is a corresponding attribute in the response schema, let's explain the identified attribute. Follow the format of triple backticks below:
```explanation
explain...
```

Let's give your confirmation: Does the input parameter have any corresponding attribute in the response schema? Follow the format of triple backticks below:
```answer
just respond: yes/no (without any explanation)
```

Let's identify all corresponding attributes name of the provided input parameter in {attributes}. Format of triple backticks below:
```corresponding attribute
just respond corresponding attribute's name here (without any explanation)
```
"""

NAIVE_PARAMETER_SCHEMA_MAPPING_PROMPT = """Given an input parameter and an API response schema, your responsibility is to check whether there is a corresponding attribute in the API response schema.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"

Follow these step to find the coresponding attribute of the input parameter:


Identify the corresponding attribute in the API response's schema.

Some cases can help determine a corresponding attribute:
- The input parameter is used for filtering, and there is a corresponding attribute that reflects the real value (result of the filter); but this attribute must be in the same object as the input parameter.
- The input parameter and the corresponding attribute maintain the same semantic meaning regarding their values.

Below is the specification of the schema "{schema}":
{schema_specification}

If there is a corresponding attribute in the response schema, let's explain the identified attribute. Follow the format of triple backticks below:
```explanation
explain...
```

Let's give your confirmation: Does the input parameter have any corresponding attribute in the response schema? Follow the format of triple backticks below:
```answer
just respond: yes/no (without any explanation)
```

Let's identify all corresponding attributes name of the provided input parameter in {attributes}. Format of triple backticks below:
```corresponding attribute
just respond corresponding attribute's name here (without any explanation)
```
"""

MAPPING_CONFIRMATION = """Given an input parameter of a REST API and an identified equivalent attribute in an API response schema, your responsibility is to check that the mapping is correct.

The input parameter's information:
- Operation: {method} {endpoint}
- Parameter: "{parameter_name}"
- Description: "{description}"

The corresponding attribute's information:
- Resource: {schema}
- Corresponding attribute: "{corresponding_attribute}"

STEP 1, determine the equivalence of resources based on the operation, the description of the input parameter. Explain about the resource of the input parameter, follow the format of triple backticks below:
```explanation
your explanation...
```

STEP 2, based on your explanation about the provided input parameter's resource, help to check the mapping of the input parameter as "{parameter_name}" with the equivalent attribute as "{corresponding_attribute}" specified in the {schema} resource.

Note that: The mapping is correct if their values are related to a specific attribute of a resource or their semantics are equivalent.

The last response should follow the format of triple backticks below:
```answer
just respond: correct/incorrect
```
"""
