##############################################
# DATA_GENERATOR_SYSTEM_PROMPT = "You are acting as a data generator for the user. The user will provide the API endpoint Swagger Specification and referenced schemas for your better understanding of the endpoint that they will have to test. The data will be generated based on real-world data as much as possible following the referenced schemas."
DATA_GENERATOR_SYSTEM_PROMPT = ""
##############################################
GET_EXPLANATION_PROMPT = """The below is the endpoint's definition in the Swagger Specification:
{endpoint_data}

Relevant referenced schemas:
{ref_data}

Based on the above information, please indicate the detailed contraints of the parameters and/or request body (if any) that should be considered before sending to the endpoint to get a response. This would be useful in case of understanding the endpoint's functionality and/or testing it, as well as know which conditions that the value of the fields should meet in order not to violate/or deliberately violate to create high-coverage-rate dataset. 

Below format is recommended to generated a typical response:
<begin>
Some constraints:
- <constraint 1>
- ...
</end>

For each <constraint> above, you have to give explanation about how the value should be created to variate different levels of complexity and potential adjustments to yield errors. This Constraints section plays a crucial role in the quality of the response.

An example of a nicely written and detailed constraint is as follows:
- To create a difficult password, you can use a mix of lowercase and uppercase letters, numbers, and special characters, and make sure the password is not too short."""
##############################################
GET_DATASET_PROMPT = """Given below information about the endpoint, you will create a dataset {amount_instruction} about the {part} of the endpoint, to be used for testing the endpoint. 

{additional_instruction}

Additionally, you must strictly follow these rules to create the dataset file:
- The data will be generated based on real-world data as much as possible.
- The generated test data must be in the JSONL format.
- DO NOT add any additional fields that are not specified in the endpoint's specification.
- ONLY generate the data based on the {part}'s specification.
- Important to note that do not giving too large values for the data items, such as a very long string, a very large number, etc. to avoid the response being too large. For example, if you want to use a large integer, just use the value of INT_MAX + 1, which is 2147483649. Or, if you want to use a very long string, put on a limitation at 257 characters. This is to avoid the response being too large and causing the system to crash. Again, avoid using too large values for the data items.

Given information:
<begin>
Data from Swagger Spec:
{endpoint_data}
{ref_data}
<end>
{additional_context}
Note that the dataset is created for {part} only, so it would be only one dataset for this section. Also, your response will have a brief explanation about your approach to identify which field to create data, and create the dataset with the awareness of the above rules and instructions. Then, you dataset will be written down in JSONL format below it, between two sets of ``` marks in for better view in markdown.

A format below is recommended for a response:
Approach: ...

Dataset in the JSONL format (with each line representing a data item. If only one data item is required, it should also be written in one line):
```json
{{ "data": {{ "field1": "value1", "field2": "value2", ... }}, "expected_code": <When requesting by this data item, what is the expected response code?> // "2xx" or "4xx" }}
{{ "data": {{ ... }}, "expected_code": <When requesting by this data item, what is the expected response code?> // "2xx" or "4xx" }} }}, 
...
```
"""
####################### Specific prompts ######################
INSTRUCT_SUCCESS = """Your responsibility is to generate a data set containing valid data items that satisfy the following conditions:

Conditions for valid data:
1. Include all required fields: Ensure that all mandatory fields are present in the generated data items (refer to the API endpoint specification, required fields are marked with the key "required" with the value "true" or exist in the "required" array).
2. Use correct data types: Generate data items with fields that satisfy their data type as specified by the API endpoint's specification.
3. Satisfy constraints: Ensure that the generated data items have fields adhering to their constraints or limitations as specified in the API endpoint's specification.
4. Take into account example values specified in the API endpoint's specification: Generate data items with fields that are similar to the example values specified in the API endpoint's specification."""

INSTRUCT_MISSING_REQUIRED_FIELD = """Your task is to create a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically lack a mandatory field. If the API endpoint doesn't have any mandatory fields, you can disregard this requirement, following the stategy outlined below:

1. Generate data items containing one missing required field, if the specification exists at least one required field: Generate all data items with each missing a different required field.
2. Generate data items containing two missing required fields if the specification exists at least two required fields: Let's randomly choose two required fields to be missing.
3. ... and so on, until all required fields are missing: Generate data items with all required fields missing."""

INSTRUCT_WRONG_DTYPE = """Your task is to create a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field with wrong data type. If the API endpoint doesn't have any fields with specified data types, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field with wrong data type, if the specification exists at least one field with specified data type: Generate all data items with each having a different field with wrong data type.
2. Generate data items containing two fields with wrong data type if the specification exists at least two fields with specified data type: Let's randomly choose two fields to have wrong data type.
3. ... and so on, until all fields with specified data type have wrong data type: Generate data items with all fields with specified data type having wrong data type.

Some rules to follow:
1. If the field's data type is string, you can use a number, a boolean, or an array instead.
2. If the field's data type is integer, you can use a string, a number, a boolean, or an array instead.
3. If the field's data type is boolean, you can use a string, a number, or an array instead.
4. If the field's data type is array, you can use a string, a number, or a boolean instead.
5. If the field's data type is object, you can use a string, a number, a boolean, or an array instead."""

INSTRUCTION_CONSTRAINT_VIOLATION = """Your responsibility is to generate a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field that violates its constraint. The constraints will be specified in the key 'description'. If the API endpoint doesn't have any fields with specified constraints, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field that violates its constraint, if the specification exists at least one field with specified constraint: Generate all data items with each having a different field that violates its constraint.
2. Generate data items containing two fields that violate their constraints if the specification exists at least two fields with specified constraints: Let's randomly choose two fields to violate their constraints.
3. ... and so on, until all fields with specified constraints violate their constraints: Generate data items with all fields with specified constraints violating their constraints.

Some rules to follow:
1. Constraints may be specified in the key 'description', 'pattern', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',...
2. If the field's constraint specifed by a regular expression, you can use a string that does not match the regular expression instead.
3. If the field's constraint specified by a number (minimum, maximum, minLength, maxLength, minItems, maxItems, minProperties, maxProperties), you can generate a value that is out of the range instead, some mutated values for your try: 0, 1, -1, random positive number, random negative number, data type maximum + 1, data type minimum - 1, specified maximum + 1, specified minimum - 1, parameter domain maximum + 1, parameter domain minimum - 1,...
4. If the field's constraint specified by a format, you can generate a value that does not match the format instead. For instance, if the format is 'date-time', you can generate a value that is not a date-time or invalid date-time: '2021-02-30T07:60:15Z', '2021-13-01T04:03:60Z', '2021-01-32T10:73:02Z',...
"""

INSTRUCT_WRONG_DTYPE_MUTATION = """Your task is to create a dataset with data items intentionally set to incorrect values to test how the API endpoint handles errors. Specifically, these data items should include fields with the wrong data type. Below is the actual successful response from the API endpoint, which you can use as a reference to mutate for producing incorrect data type data items:

{actual_success_response}

If the API endpoint doesn't have any fields with specified data types, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field with wrong data type, if the specification exists at least one field with specified data type: Generate all data items with each having a different field with wrong data type.
2. Generate data items containing two fields with wrong data type if the specification exists at least two fields with specified data type: Let's randomly choose two fields to have wrong data type.
3. ... and so on, until all fields with specified data type have wrong data type: Generate data items with all fields with specified data type having wrong data type.

Some rules to follow:
1. If the field's data type is string, you can use a number, a boolean, or an array instead.
2. If the field's data type is integer, you can use a string, a number, a boolean, or an array instead.
3. If the field's data type is boolean, you can use a string, a number, or an array instead.
4. If the field's data type is array, you can use a string, a number, or a boolean instead.
5. If the field's data type is object, you can use a string, a number, a boolean, or an array instead."""

INSTRUCTION_CONSTRAINT_VIOLATION_MUTATION = """Your responsibility is to generate a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field that violates its constraint. The constraints will be specified in the key 'description'. Below is the actual successful response from the API endpoint, which you can use as a reference to mutate for producing data items violated constraints:

{actual_success_response}

If the API endpoint doesn't have any fields with specified constraints, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field that violates its constraint, if the specification exists at least one field with specified constraint: Generate all data items with each having a different field that violates its constraint.
2. Generate data items containing two fields that violate their constraints if the specification exists at least two fields with specified constraints: Let's randomly choose two fields to violate their constraints.
3. ... and so on, until all fields with specified constraints violate their constraints: Generate data items with all fields with specified constraints violating their constraints.

Some rules to follow:
1. Constraints may be specified in the key 'description', 'pattern', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',...
2. If the field's constraint specifed by a regular expression, you can use a string that does not match the regular expression instead.
3. If the field's constraint specified by a number (minimum, maximum, minLength, maxLength, minItems, maxItems, minProperties, maxProperties), you can generate a value that is out of the range instead, some mutated values for your try: 0, 1, -1, random positive number, random negative number, data type maximum + 1, data type minimum - 1, specified maximum + 1, specified minimum - 1, parameter domain maximum + 1, parameter domain minimum - 1,...
4. If the field's constraint specified by a format, you can generate a value that does not match the format instead. For instance, if the format is 'date-time', you can generate a value that is not a date-time or invalid date-time: '2021-02-30T07:60:15Z', '2021-13-01T04:03:60Z', '2021-01-32T10:73:02Z',...
"""

##############################################

##############################################
# DATA_GENERATOR_SYSTEM_PROMPT = "You are acting as a data generator for the user. The user will provide the API endpoint Swagger Specification and referenced schemas for your better understanding of the endpoint that they will have to test. The data will be generated based on real-world data as much as possible following the referenced schemas."
DATA_GENERATOR_SYSTEM_PROMPT = ""
##############################################
GET_EXPLANATION_PROMPT = """The below is the endpoint's definition in the Swagger Specification:
{endpoint_data}

Relevant referenced schemas:
{ref_data}

Based on the above information, please indicate the detailed contraints of the parameters and/or request body (if any) that should be considered before sending to the endpoint to get a response. This would be useful in case of understanding the endpoint's functionality and/or testing it, as well as know which conditions that the value of the fields should meet in order not to violate/or deliberately violate to create high-coverage-rate dataset. 

Below format is recommended to generated a typical response:
<begin>
Some constraints:
- <constraint 1>
- ...
</end>

For each <constraint> above, you have to give explanation about how the value should be created to variate different levels of complexity and potential adjustments to yield errors. This Constraints section plays a crucial role in the quality of the response.

An example of a nicely written and detailed constraint is as follows:
- To create a difficult password, you can use a mix of lowercase and uppercase letters, numbers, and special characters, and make sure the password is not too short."""
##############################################
GET_DATASET_PROMPT = """Given below information about the endpoint, you will create a dataset {amount_instruction} about the {part} of the endpoint, to be used for testing the endpoint. 

{additional_instruction}

Additionally, you must strictly follow these rules to create the dataset file:
- The data will be generated based on real-world data as much as possible.
- The generated test data must be in the JSONL format.
- DO NOT add any additional fields that are not specified in the endpoint's specification.
- ONLY generate the data based on the {part}'s specification.
- Important to note that do not giving too large values for the data items, such as a very long string, a very large number, etc. to avoid the response being too large. For example, if you want to use a large integer, just use the value of INT_MAX + 1, which is 2147483649. Or, if you want to use a very long string, put on a limitation at 257 characters. This is to avoid the response being too large and causing the system to crash. Again, avoid using too large values for the data items.

Given information:
<begin>
Data from Swagger Spec:
{endpoint_data}
{ref_data}
<end>
{additional_context}
Note that the dataset is created for {part} only, so it would be only one dataset for this section. Also, your response will have a brief explanation about your approach to identify which field to create data, and create the dataset with the awareness of the above rules and instructions. Then, you dataset will be written down in JSONL format below it, between two sets of ``` marks in for better view in markdown.

A format below is recommended for a response:
Approach: ...

Dataset in the JSONL format (with each line representing a data item. If only one data item is required, it should also be written in one line):
```json
{{ "data": {{ "field1": "value1", "field2": "value2", ... }}, "expected_code": <When requesting by this data item, what is the expected response code?> // "2xx" or "4xx" }}
{{ "data": {{ ... }}, "expected_code": <When requesting by this data item, what is the expected response code?> // "2xx" or "4xx" }} }}, 
...
```
"""
####################### Specific prompts ######################
INSTRUCT_SUCCESS = """Your responsibility is to generate a data set containing valid data items that satisfy the following conditions:

Conditions for valid data:
1. Include all required fields: Ensure that all mandatory fields are present in the generated data items (refer to the API endpoint specification, required fields are marked with the key "required" with the value "true" or exist in the "required" array).
2. Use correct data types: Generate data items with fields that satisfy their data type as specified by the API endpoint's specification.
3. Satisfy constraints: Ensure that the generated data items have fields adhering to their constraints or limitations as specified in the API endpoint's specification.
4. Take into account example values specified in the API endpoint's specification: Generate data items with fields that are similar to the example values specified in the API endpoint's specification."""

INSTRUCT_MISSING_REQUIRED_FIELD = """Your task is to create a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically lack a mandatory field. If the API endpoint doesn't have any mandatory fields, you can disregard this requirement, following the stategy outlined below:

1. Generate data items containing one missing required field, if the specification exists at least one required field: Generate all data items with each missing a different required field.
2. Generate data items containing two missing required fields if the specification exists at least two required fields: Let's randomly choose two required fields to be missing.
3. ... and so on, until all required fields are missing: Generate data items with all required fields missing."""

INSTRUCT_WRONG_DTYPE = """Your task is to create a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field with wrong data type. If the API endpoint doesn't have any fields with specified data types, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field with wrong data type, if the specification exists at least one field with specified data type: Generate all data items with each having a different field with wrong data type.
2. Generate data items containing two fields with wrong data type if the specification exists at least two fields with specified data type: Let's randomly choose two fields to have wrong data type.
3. ... and so on, until all fields with specified data type have wrong data type: Generate data items with all fields with specified data type having wrong data type.

Some rules to follow:
1. If the field's data type is string, you can use a number, a boolean, or an array instead.
2. If the field's data type is integer, you can use a string, a number, a boolean, or an array instead.
3. If the field's data type is boolean, you can use a string, a number, or an array instead.
4. If the field's data type is array, you can use a string, a number, or a boolean instead.
5. If the field's data type is object, you can use a string, a number, a boolean, or an array instead."""

INSTRUCTION_CONSTRAINT_VIOLATION = """Your responsibility is to generate a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field that violates its constraint. The constraints will be specified in the key 'description'. If the API endpoint doesn't have any fields with specified constraints, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field that violates its constraint, if the specification exists at least one field with specified constraint: Generate all data items with each having a different field that violates its constraint.
2. Generate data items containing two fields that violate their constraints if the specification exists at least two fields with specified constraints: Let's randomly choose two fields to violate their constraints.
3. ... and so on, until all fields with specified constraints violate their constraints: Generate data items with all fields with specified constraints violating their constraints.

Some rules to follow:
1. Constraints may be specified in the key 'description', 'pattern', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',...
2. If the field's constraint specifed by a regular expression, you can use a string that does not match the regular expression instead.
3. If the field's constraint specified by a number (minimum, maximum, minLength, maxLength, minItems, maxItems, minProperties, maxProperties), you can generate a value that is out of the range instead, some mutated values for your try: 0, 1, -1, random positive number, random negative number, data type maximum + 1, data type minimum - 1, specified maximum + 1, specified minimum - 1, parameter domain maximum + 1, parameter domain minimum - 1,...
4. If the field's constraint specified by a format, you can generate a value that does not match the format instead. For instance, if the format is 'date-time', you can generate a value that is not a date-time or invalid date-time: '2021-02-30T07:60:15Z', '2021-13-01T04:03:60Z', '2021-01-32T10:73:02Z',...
"""

INSTRUCT_WRONG_DTYPE_MUTATION = """Your task is to create a dataset with data items intentionally set to incorrect values to test how the API endpoint handles errors. Specifically, these data items should include fields with the wrong data type. Below is the actual successful response from the API endpoint, which you can use as a reference to mutate for producing incorrect data type data items:

{actual_success_response}

If the API endpoint doesn't have any fields with specified data types, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field with wrong data type, if the specification exists at least one field with specified data type: Generate all data items with each having a different field with wrong data type.
2. Generate data items containing two fields with wrong data type if the specification exists at least two fields with specified data type: Let's randomly choose two fields to have wrong data type.
3. ... and so on, until all fields with specified data type have wrong data type: Generate data items with all fields with specified data type having wrong data type.

Some rules to follow:
1. If the field's data type is string, you can use a number, a boolean, or an array instead.
2. If the field's data type is integer, you can use a string, a number, a boolean, or an array instead.
3. If the field's data type is boolean, you can use a string, a number, or an array instead.
4. If the field's data type is array, you can use a string, a number, or a boolean instead.
5. If the field's data type is object, you can use a string, a number, a boolean, or an array instead."""

INSTRUCTION_CONSTRAINT_VIOLATION_MUTATION = """Your responsibility is to generate a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field that violates its constraint. The constraints will be specified in the key 'description'. Below is the actual successful response from the API endpoint, which you can use as a reference to mutate for producing data items violated constraints:

{actual_success_response}

If the API endpoint doesn't have any fields with specified constraints, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field that violates its constraint, if the specification exists at least one field with specified constraint: Generate all data items with each having a different field that violates its constraint.
2. Generate data items containing two fields that violate their constraints if the specification exists at least two fields with specified constraints: Let's randomly choose two fields to violate their constraints.
3. ... and so on, until all fields with specified constraints violate their constraints: Generate data items with all fields with specified constraints violating their constraints.

Some rules to follow:
1. Constraints may be specified in the key 'description', 'pattern', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',...
2. If the field's constraint specifed by a regular expression, you can use a string that does not match the regular expression instead.
3. If the field's constraint specified by a number (minimum, maximum, minLength, maxLength, minItems, maxItems, minProperties, maxProperties), you can generate a value that is out of the range instead, some mutated values for your try: 0, 1, -1, random positive number, random negative number, data type maximum + 1, data type minimum - 1, specified maximum + 1, specified minimum - 1, parameter domain maximum + 1, parameter domain minimum - 1,...
4. If the field's constraint specified by a format, you can generate a value that does not match the format instead. For instance, if the format is 'date-time', you can generate a value that is not a date-time or invalid date-time: '2021-02-30T07:60:15Z', '2021-13-01T04:03:60Z', '2021-01-32T10:73:02Z',...
"""

##############################################

##############################################
# DATA_GENERATOR_SYSTEM_PROMPT = "You are acting as a data generator for the user. The user will provide the API endpoint Swagger Specification and referenced schemas for your better understanding of the endpoint that they will have to test. The data will be generated based on real-world data as much as possible following the referenced schemas."
DATA_GENERATOR_SYSTEM_PROMPT = ""
##############################################
GET_EXPLANATION_PROMPT = """The below is the endpoint's definition in the Swagger Specification:
{endpoint_data}

Relevant referenced schemas:
{ref_data}

Based on the above information, please indicate the detailed contraints of the parameters and/or request body (if any) that should be considered before sending to the endpoint to get a response. This would be useful in case of understanding the endpoint's functionality and/or testing it, as well as know which conditions that the value of the fields should meet in order not to violate/or deliberately violate to create high-coverage-rate dataset. 

Below format is recommended to generated a typical response:
<begin>
Some constraints:
- <constraint 1>
- ...
</end>

For each <constraint> above, you have to give explanation about how the value should be created to variate different levels of complexity and potential adjustments to yield errors. This Constraints section plays a crucial role in the quality of the response.

An example of a nicely written and detailed constraint is as follows:
- To create a difficult password, you can use a mix of lowercase and uppercase letters, numbers, and special characters, and make sure the password is not too short."""
##############################################
GET_DATASET_PROMPT = """Given below information about the endpoint, you will create a dataset {amount_instruction} about the {part} of the endpoint, to be used for testing the endpoint. 

{additional_instruction}

Additionally, you must strictly follow these rules to create the dataset file:
- The data will be generated based on real-world data as much as possible.
- The generated test data must be in the JSONL format.
- DO NOT add any additional fields that are not specified in the endpoint's specification.
- ONLY generate the data based on the {part}'s specification.
- Important to note that do not giving too large values for the data items, such as a very long string, a very large number, etc. to avoid the response being too large. For example, if you want to use a large integer, just use the value of INT_MAX + 1, which is 2147483649. Or, if you want to use a very long string, put on a limitation at 257 characters. This is to avoid the response being too large and causing the system to crash. Again, avoid using too large values for the data items.

Given information:
<begin>
Data from Swagger Spec:
{endpoint_data}
{ref_data}
<end>
{additional_context}
Note that the dataset is created for {part} only, so it would be only one dataset for this section. Also, your response will have a brief explanation about your approach to identify which field to create data, and create the dataset with the awareness of the above rules and instructions. Then, you dataset will be written down in JSONL format below it, between two sets of ``` marks in for better view in markdown.

A format below is recommended for a response:
Approach: ...

Dataset in the JSONL format (with each line representing a data item. If only one data item is required, it should also be written in one line):
```json
{{ "data": {{ "field1": "value1", "field2": "value2", ... }}, "expected_code": <When requesting by this data item, what is the expected response code?> // "2xx" or "4xx" }}
{{ "data": {{ ... }}, "expected_code": <When requesting by this data item, what is the expected response code?> // "2xx" or "4xx" }} }}, 
...
```
"""
####################### Specific prompts ######################
INSTRUCT_SUCCESS = """Your responsibility is to generate a data set containing valid data items that satisfy the following conditions:

Conditions for valid data:
1. Include all required fields: Ensure that all mandatory fields are present in the generated data items (refer to the API endpoint specification, required fields are marked with the key "required" with the value "true" or exist in the "required" array).
2. Use correct data types: Generate data items with fields that satisfy their data type as specified by the API endpoint's specification.
3. Satisfy constraints: Ensure that the generated data items have fields adhering to their constraints or limitations as specified in the API endpoint's specification.
4. Take into account example values specified in the API endpoint's specification: Generate data items with fields that are similar to the example values specified in the API endpoint's specification."""

INSTRUCT_MISSING_REQUIRED_FIELD = """Your task is to create a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically lack a mandatory field. If the API endpoint doesn't have any mandatory fields, you can disregard this requirement, following the stategy outlined below:

1. Generate data items containing one missing required field, if the specification exists at least one required field: Generate all data items with each missing a different required field.
2. Generate data items containing two missing required fields if the specification exists at least two required fields: Let's randomly choose two required fields to be missing.
3. ... and so on, until all required fields are missing: Generate data items with all required fields missing."""

INSTRUCT_WRONG_DTYPE = """Your task is to create a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field with wrong data type. If the API endpoint doesn't have any fields with specified data types, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field with wrong data type, if the specification exists at least one field with specified data type: Generate all data items with each having a different field with wrong data type.
2. Generate data items containing two fields with wrong data type if the specification exists at least two fields with specified data type: Let's randomly choose two fields to have wrong data type.
3. ... and so on, until all fields with specified data type have wrong data type: Generate data items with all fields with specified data type having wrong data type.

Some rules to follow:
1. If the field's data type is string, you can use a number, a boolean, or an array instead.
2. If the field's data type is integer, you can use a string, a number, a boolean, or an array instead.
3. If the field's data type is boolean, you can use a string, a number, or an array instead.
4. If the field's data type is array, you can use a string, a number, or a boolean instead.
5. If the field's data type is object, you can use a string, a number, a boolean, or an array instead."""

INSTRUCTION_CONSTRAINT_VIOLATION = """Your responsibility is to generate a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field that violates its constraint. The constraints will be specified in the key 'description'. If the API endpoint doesn't have any fields with specified constraints, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field that violates its constraint, if the specification exists at least one field with specified constraint: Generate all data items with each having a different field that violates its constraint.
2. Generate data items containing two fields that violate their constraints if the specification exists at least two fields with specified constraints: Let's randomly choose two fields to violate their constraints.
3. ... and so on, until all fields with specified constraints violate their constraints: Generate data items with all fields with specified constraints violating their constraints.

Some rules to follow:
1. Constraints may be specified in the key 'description', 'pattern', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',...
2. If the field's constraint specifed by a regular expression, you can use a string that does not match the regular expression instead.
3. If the field's constraint specified by a number (minimum, maximum, minLength, maxLength, minItems, maxItems, minProperties, maxProperties), you can generate a value that is out of the range instead, some mutated values for your try: 0, 1, -1, random positive number, random negative number, data type maximum + 1, data type minimum - 1, specified maximum + 1, specified minimum - 1, parameter domain maximum + 1, parameter domain minimum - 1,...
4. If the field's constraint specified by a format, you can generate a value that does not match the format instead. For instance, if the format is 'date-time', you can generate a value that is not a date-time or invalid date-time: '2021-02-30T07:60:15Z', '2021-13-01T04:03:60Z', '2021-01-32T10:73:02Z',...
"""

INSTRUCT_WRONG_DTYPE_MUTATION = """Your task is to create a dataset with data items intentionally set to incorrect values to test how the API endpoint handles errors. Specifically, these data items should include fields with the wrong data type. Below is the actual successful response from the API endpoint, which you can use as a reference to mutate for producing incorrect data type data items:

{actual_success_response}

If the API endpoint doesn't have any fields with specified data types, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field with wrong data type, if the specification exists at least one field with specified data type: Generate all data items with each having a different field with wrong data type.
2. Generate data items containing two fields with wrong data type if the specification exists at least two fields with specified data type: Let's randomly choose two fields to have wrong data type.
3. ... and so on, until all fields with specified data type have wrong data type: Generate data items with all fields with specified data type having wrong data type.

Some rules to follow:
1. If the field's data type is string, you can use a number, a boolean, or an array instead.
2. If the field's data type is integer, you can use a string, a number, a boolean, or an array instead.
3. If the field's data type is boolean, you can use a string, a number, or an array instead.
4. If the field's data type is array, you can use a string, a number, or a boolean instead.
5. If the field's data type is object, you can use a string, a number, a boolean, or an array instead."""

INSTRUCTION_CONSTRAINT_VIOLATION_MUTATION = """Your responsibility is to generate a dataset with data items that are intentionally incorrect in order to test how the API endpoint handles errors. These data items should specifically have a field that violates its constraint. The constraints will be specified in the key 'description'. Below is the actual successful response from the API endpoint, which you can use as a reference to mutate for producing data items violated constraints:

{actual_success_response}

If the API endpoint doesn't have any fields with specified constraints, you can disregard this requirement, following the conditions outlined below:

1. Generate data items containing one field that violates its constraint, if the specification exists at least one field with specified constraint: Generate all data items with each having a different field that violates its constraint.
2. Generate data items containing two fields that violate their constraints if the specification exists at least two fields with specified constraints: Let's randomly choose two fields to violate their constraints.
3. ... and so on, until all fields with specified constraints violate their constraints: Generate data items with all fields with specified constraints violating their constraints.

Some rules to follow:
1. Constraints may be specified in the key 'description', 'pattern', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',...
2. If the field's constraint specifed by a regular expression, you can use a string that does not match the regular expression instead.
3. If the field's constraint specified by a number (minimum, maximum, minLength, maxLength, minItems, maxItems, minProperties, maxProperties), you can generate a value that is out of the range instead, some mutated values for your try: 0, 1, -1, random positive number, random negative number, data type maximum + 1, data type minimum - 1, specified maximum + 1, specified minimum - 1, parameter domain maximum + 1, parameter domain minimum - 1,...
4. If the field's constraint specified by a format, you can generate a value that does not match the format instead. For instance, if the format is 'date-time', you can generate a value that is not a date-time or invalid date-time: '2021-02-30T07:60:15Z', '2021-13-01T04:03:60Z', '2021-01-32T10:73:02Z',...
"""