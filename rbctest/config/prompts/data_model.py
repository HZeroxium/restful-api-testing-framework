# config/prompts/data_model.py

"""
Prompts used for data model building in the RBCTest framework.
"""

FIND_SCHEMA_KEYS = """Given a schema in an OpenAPI specification file, your responsibility is to identify one or some attributes in the schema that play the role of identifying the specific object (primary keys):

Below is the schema specification:
{schema_specification}

If the given schema does not reflect an object, you only need to respond with "None"; otherwise, respond with the primary keys you identified, separated by commas. No explanation is needed."""

DATA_MODEL_PROMPT = r"""Given two schemas specified in an OpenAPI Specification file, your responsibility is to find all pairs of two fields that have the same meaning.

Below are the two schemas needed to find pairs:
Schema 1: {schema_1}
Schema 2: {schema_2}

Rules:
1. The two fields in a pair must be of the same data type.
2. The two fields in a pair must share the same meaning; their values should represent the id of the same object or maintain an attribute value of the same object,...
3. A field in one schema only pairs with at most one field in another schema, and vice versa.

Please follow these rules in your response:
1. If there exist pairs of two fields that share the same meaning:
Follow the format below to indicate them:
<field at Schema 1> -> <field at Schema 2>
...
2. If there are no pairs of two fields with the same meaning found between the two schemas, you only need to respond with "None"."""
