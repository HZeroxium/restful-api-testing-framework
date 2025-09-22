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

You MUST follow this validation policy WHEN SETTING "expected_code":
- If ANY provided field (non-null/non-missing) violates the {part}'s specification (minimum/maximum, enum, pattern, format, required, type, nullable, etc.), then "expected_code" MUST be "4xx".
- Only when ALL provided fields satisfy the {part}'s specification, "expected_code" MUST be "2xx".
- Missing optional fields are allowed and should still lead to "2xx" unless the spec says otherwise.
- If the spec marks a field as non-nullable (or its type is strictly defined) and you provide null or a mismatched type, that is a violation → "4xx".
- If the spec allows nullable for a field, providing null is acceptable for that field.

CRITICAL PATH PARAMETER RULES (if {part} contains path parameters):
- PATH PARAMETERS (in: "path") are NEVER nullable and ALWAYS required by OpenAPI spec.
- PATH PARAMETERS MUST ALWAYS have a non-null, non-empty value in EVERY test case.
- FORBIDDEN for path parameters: null, "", undefined, missing from data object.
- PATH PARAMETERS must satisfy their schema constraints (type, minimum, maximum, pattern, etc.).

PATH PARAMETER VALUE ASSIGNMENT STRATEGY:
First ANALYZE each path parameter's specification to determine if concrete values can be reliably inferred:

CRITERIA FOR USING CONCRETE VALUES (for 2XX cases):
✅ Parameter has ENUM values → Use values from the enum
✅ Parameter has BOTH minimum AND maximum with small range (≤100) → Use values within range  
✅ Parameter has clear examples provided in spec → Use or derive similar values
✅ Parameter has specific format constraints (date, uuid, etc.) → Generate valid format values

CRITERIA FOR USING "%not-sure%" MARKER (for 2XX cases):
⚠️ Parameter has ONLY minimum without maximum → Use "%not-sure%"
⚠️ Parameter has very large range (>100 possible values) → Use "%not-sure%"
⚠️ Parameter has no constraints beyond basic type → Use "%not-sure%"
⚠️ Parameter appears to reference external system IDs → Use "%not-sure%"

FOR 4XX CASES (testing validation):
- Always use INVALID but NON-NULL concrete values to test constraints
- Examples: out of range, wrong enum value, wrong type, invalid format
- NEVER use null or empty string for path parameter validation testing

Additionally, you must strictly follow these rules to create the dataset file:
- The data will be generated based on real-world data as much as possible.
- The generated test data must be in the JSONL format.
- Each JSON object MUST have EXACTLY these keys: "data", "expected_code", "reason".
  - "data": object that only contains fields allowed by the {part}'s spec.
  - "expected_code": either "2xx" or "4xx" per the above policy.
  - "reason": write in plain, human-readable English (no URL encoding, no escape sequences, no prefixes). Be concise but explicit:
      * Name the rule/constraint (minimum, maximum, enum, type, required, format/pattern).
      * Quote the offending field/value if "4xx".
      * Examples (schema-agnostic):
        - "NUMBER_FIELD is within [MIN..MAX]; ENUM_FIELD is within its allowed set."
        - "NUMBER_FIELD={{VALUE}} > maximum={{MAX}}, violating 'maximum'."
        - "ENUM_FIELD='{{BAD_VALUE}}' is not in enum {{ALLOWED_ENUM}}."
        - "FIELD is required but missing, violating 'required'."
        - "PATH_PARAM='{{VALUE}}' is in the allowed enum {{ENUM_VALUES}}."
        - "PATH_PARAM={{VALUE}} is within allowed range [{{MIN}}..{{MAX}}]."
        - "PATH_PARAM=%not-sure% indicates uncertain path parameter requiring dependency resolution."
        - "PATH_PARAM='{{BAD_VALUE}}' is not in the allowed enum {{ENUM_VALUES}}."
        - "PATH_PARAM={{VALUE}} violates {{CONSTRAINT}} constraint."
        - "FIELD='{{RAW}}' does not match format {{EXPECTED_FORMAT}}."

- DO NOT add any additional fields that are not specified in the endpoint's specification.
- ONLY generate the data based on the {part}'s specification.
- Avoid excessively large values (very long strings, very large numbers). If you need a large integer, use 2147483649; for a long string, cap at 257 characters.

Given information:
<begin>
Data from Swagger Spec:
{endpoint_data}
{ref_data}
</end>
{additional_context}

⚠️  CRITICAL WARNING for PATH PARAMETERS: NEVER generate test cases with null, empty string (""), or missing path parameters. Path parameters MUST ALWAYS have values.

ANALYSIS EXAMPLES for path parameter decision-making:
• provinceId with enum ["AB","BC","MB"...] → Use concrete values like "AB", "MB" for 2xx cases
• holidayId with minimum=1, maximum=34 → Use concrete values like 1, 15, 34 for 2xx cases  
• billId with only minimum=1 (no maximum) → Use "%not-sure%" for 2xx cases
• userId with no constraints → Use "%not-sure%" for 2xx cases

Note: The dataset is created for {part} only. First, briefly write "Approach: ..." describing how you selected fields and constraints. Then provide the dataset in JSONL between triple backticks.

Correctness rules (MUST FOLLOW; schema-agnostic):
- Numeric field outside its [minimum..maximum] per spec → "4xx", explain which bound is violated and show provided vs bound.
- Enum field with a value not in the allowed set → "4xx", show the provided value and the allowed set.
- Type/format/pattern mismatch → "4xx", cite the exact spec keyword (type/format/pattern).
- Missing required field → "4xx", cite 'required'.
- Path parameter with valid concrete value (enum member or within range) → "2xx", cite the validation.
- Path parameter with "%not-sure%" value → "2xx", cite 'uncertain path parameter requiring dependency resolution'.
- Path parameter with null, empty string, or missing value → FORBIDDEN (never generate these cases).
- Otherwise (all provided fields satisfy constraints) → "2xx".

Format example (JSONL; schema-agnostic):
```json
{{
  "data": {{ "NUMBER_FIELD": 123, "ENUM_FIELD": "ok" }},
  "expected_code": "2xx",
  "reason": "NUMBER_FIELD is within its allowed range; ENUM_FIELD matches the allowed enum {{ALLOWED_ENUM}}."
}}
{{
  "data": {{ "NUMBER_FIELD": {{OUT_OF_RANGE_VALUE}} }},
  "expected_code": "4xx",
  "reason": "NUMBER_FIELD={{OUT_OF_RANGE_VALUE}} {{RELATION}} {{BOUND_NAME}}={{BOUND_VALUE}}, violating '{{BOUND_NAME}}'."
}}
{{
  "data": {{ "ENUM_FIELD": "{{BAD_VALUE}}" }},
  "expected_code": "4xx",
  "reason": "ENUM_FIELD='{{BAD_VALUE}}' is not in the allowed enum {{ALLOWED_ENUM}}."
}}
{{
  "data": {{ "ENUM_PATH_PARAM": "AB", "RANGE_PATH_PARAM": 15, "OPTIONAL_FIELD": "value" }},
  "expected_code": "2xx",
  "reason": "ENUM_PATH_PARAM='AB' is in the allowed enum; RANGE_PATH_PARAM=15 is within allowed range [1..34]; OPTIONAL_FIELD is valid."
}}
{{
  "data": {{ "UNCERTAIN_PATH_PARAM": "%not-sure%", "OPTIONAL_FIELD": "value" }},
  "expected_code": "2xx",
  "reason": "UNCERTAIN_PATH_PARAM=%not-sure% indicates uncertain path parameter requiring dependency resolution; OPTIONAL_FIELD is valid."
}}
{{
  "data": {{ "TYPED_FIELD": "not_a_number" }},
  "expected_code": "4xx",
  "reason": "TYPED_FIELD has type string but the spec requires integer (type mismatch)."
}}
"""

##############################################
# Specific prompts
##############################################

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
