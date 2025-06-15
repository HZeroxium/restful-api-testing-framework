# config/prompts/constraint_extraction.py

"""
Prompts used for constraint extraction in the RBCTest framework.
"""

DESCRIPTION_OBSERVATION_PROMPT = """Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"
- schema: "{param_schema}"

If the description implies any constraints, rules, or limitations for legalizing the attribute itself, let's provide a brief description of these constraints.
"""

NAIVE_CONSTRAINT_DETECTION_PROMPT = """Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"

If the description implies any constraints, rules, or limitations for legalizing the attribute itself, return yes; otherwise, return no. follow the following format:
```answer
yes/no
```

"""

CONSTRAINT_CONFIRMATION = """Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself. Ensure that the description contains sufficient information to generate a script capable of verifying these constraints.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"
- schema: "{param_schema}"

Does the description imply any constraints, rules, or limitations?
- {description_observation}

Follow these rules to identify the capability of generating a constraint validation test script:
- If there is a constraint for the attribute itself, check if the description contains specific predefined values, ranges, formats, etc. Exception: Predefined values such as True/False for the attribute whose data type is boolean are not good constraints.
- If there is an inter-parameter constraint, ensure that the relevant attributes have been mentioned in the description.

Now, let's confirm: Is there sufficient information mentioned in the description to generate a script for verifying these identified constraints?
```answer
yes/no
```
"""

GROOVY_SCRIPT_VERIFICATION_GENERATION_PROMPT = """Given a description implying constraints, rules, or limitations of an attribute in a REST API, your responsibility is to generate a corresponding Python script to check whether these constraints are satisfied through the API response.

Below is the attribute's description:
- "{attribute}": "{description}"

{attribute_observation}

Below is the API response's schema:
"{schema}": "{specification}"

The correspond attribute of "{attribute}" in the API response's schema is: "{corresponding_attribute}"

Below is the request information to the API: 
{request_information}

Rules: 
- Ensure that the generated Python code can verify fully these identified constraints.
- The generated Python code does not include any example of usages.
- The Python script should be generalized, without specific example values embedded in the code.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- You'll generate a Python script using the response body variable named 'latest_response' (already defined) to verify the given constraint in the triple backticks as below: 
```python
def verify_latest_response(latest_response):
    // deploy verification flow...
    // return True if the constraint is satisfied and False otherwise.
```
- No explanation is needed."""

IDL_TRANSFORMATION_PROMPT = """You will be provided with a description specifying the constraint/rule/limitation of an attribute in natural language and a Python script to verify whether the attribute satisfies that constraint or not. Your responsibility is to specify that constraint using IDL. Follow these steps below to complete your task:

STEP 1: You will be guided to understand IDL keywords.

Below is the catalog of Inter/Inner-Parameter Dependency Language (IDL for short):

1. Conditional Dependency: This type of dependency is expressed as "IF <predicate> THEN <predicate>;", where the first predicate is the condition and the second is the consequence.
Syntax: IF <predicate> THEN <predicate>;
Example: IF custom.label THEN custom.amount; //This specification implies that if a value is provided for 'custom.label' then a value must also be provided for 'custom.amount' (or if custom.label is True, custom.amount must also be True).

2. Or: This type of dependency is expressed using the keyword "Or" followed by a list of two or more predicates placed inside parentheses: "Or(predicate, predicate [, ...]);". The dependency is satisfied if at least one of the predicates evaluates to true.
Syntax/Predicate: Or(<predicate>, <predicate>, ...);
Example: Or(header, upload_type); //This specification implies that the constraint will be satisfied if a value is provided for at least one of 'header' or 'upload_type' (or if at least one of them is True).

3. OnlyOne: These dependencies are specified using the keyword "OnlyOne" followed by a list of two or more predicates placed inside parentheses: "OnlyOne(predicate, predicate [, ...]);". The dependency is satisfied if one, and only one of the predicates evaluates to true.
Syntax/Predicate: OnlyOne(<predicate>, <predicate>, ...);
Example: OnlyOne(amount_off, percent_off); //This specification implies that the constraint will be satisfied if a value is provided for only one of 'header' or 'upload_type' (or if only one of them is set to True)

4. AllOrNone: This type of dependency is specified using the keyword "AllOrNone" followed by a list of two or more predicates placed inside parentheses: "AllOrNone(predicate, predicate [, ...]);". The dependency is satisfied if either all the predicates evaluate to true, or all of them evaluate to false.
Syntax/Predicate: AllOrNone(<predicate>, <predicate>, ...)
Example: AllOrNone(rights, filter=='track'|'album'); //This specification implies that the constraint will be satisfied under two conditions: 1. If a value is provided for 'rights,' then the value of 'filter' must also be provided, and it can only be 'track' or 'album'. 2. Alternatively, the constraint is satisfied if no value is provided for 'rights' and 'filter' (or if the value of 'filter' is not 'track' or 'album').

5. ZeroOrOne: These dependencies are specified using the keyword "ZeroOrOne" followed by a list of two or more predicates placed inside parentheses: "ZeroOrOne(predicate, predicate [, ...]);". The dependency is satisfied if none or at most one of the predicates evaluates to true.
Syntax/Predicate: ZeroOrOne(<predicate>, <predicate>, ...)
Example: ZeroOrOne(type, affiliation); // This specification implies that the constraint will be satisfied under two conditions: 1. If no value is provided for 'type' and 'affiliation' (or both are False). 2. If only one of 'type' and 'affiliation' is provided a value (or if only one of them is set to True).

6. Arithmetic/Relational: Relational dependencies are specified as pairs of parameters joined by any of the following relational operators: ==, !=, <=, <, >= or >. Arithmetic dependencies relate two or more parameters using the operators +, - , *, / followed by a final comparison using a relational operator.
Syntax: ==, !=, <=, <, >=, >, +, - , *, /
Example: created_at_min <= created_at_max; // the created_at_min is less than or equal to created_at_max

7. Boolean operators: 'AND', 'OR', 'NOT'

STEP 2: You will be provided with the attribute's description specifying a constraint in natural language and the corresponding generated Python script to verify the attribute's satisfaction for that constraint.

Below is the attribute's description:
- "{attribute}": "{description}"

Below is the specification for the {part}, where the attribute is specified:
{specification}

Below is the generated Python script to verify that constraint:
{generated_python_script}

Now, help to specify the constraint/limitation of the attribute using IDL by considering both the constraint in natural language and its verification script in Python, follow these rules below: 
- If the provided constraint description does not mention any types mentioned above, you do not need to respond with any IDL specification.
- You do not need to generate any data samples in the IDL specification sentence; instead, mention the related variables and data in the constraint description only.
- Only respond the IDL sentence and only use IDL keywords (already defined above).
- Only respond coresponding your IDL specification. 
- Respond IDL specification in the format below:
```IDL
IDL specification...
```
- No explanation is needed."""
