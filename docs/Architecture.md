# Architecture

## RBCTest

### High-level

---

#### System-Level I/O

```json
{
  "system": {
    "inputs": [
      "OpenAPI/Swagger specification (YAML/JSON)",
      "(Optional) API execution data / logs"
    ],
    "outputs": [
      "Generated constraint test cases (Python scripts)",
      "Test run results (matched / mismatched / unknown)",
      "Mismatch reports for spec vs. implementation"
    ]
  }
}
```

---

#### Core Components

| Component                               | Input                                   | Output                                                        |
| --------------------------------------- | --------------------------------------- | ------------------------------------------------------------- |
| **1. Spec Loader**                      | Raw OpenAPI spec file                   | Parsed specification object model                             |
| **2. Static Constraint Miner**          | Parsed spec                             | _Static constraints_ (from request params & response schemas) |
| • Description Extractor                 | Spec object                             | Parameter/property descriptions                               |
| • Observation Phase                     | Descriptions, schema fragments          | Candidate constraints (LLM “observation”)                     |
| • Confirmation Phase                    | Candidate constraints                   | Validated static constraints                                  |
| • Syntactic Filter                      | Validated constraints                   | Filtered static constraints                                   |
| **3. Dynamic Constraint Miner (AGORA)** | API execution traces / responses        | _Dynamic invariants_ (Daikon-derived)                         |
| **4. Constraint Combiner**              | Static constraints ⊕ Dynamic invariants | Unified constraint set (choosing stricter or merging unique)  |
| **5. Test Case Generator**              | Unified constraints, spec               | Test‐generation instructions (LLM prompts)                    |
| • LLM‐Based Generation                  | Prompts with constraint & schema        | Raw Python test code                                          |
| **6. Semantic Verifier**                | Generated test code, spec examples      | Verified/pruned test code                                     |
| **7. Test Executor**                    | Verified test code                      | Test results (matched / mismatched / unknown)                 |
| **8. Reporter**                         | Test results                            | Human‐readable mismatch reports, dashboards                   |

---

#### End-to-End Workflow

1. **Load & Parse Spec**

   Spec Loader reads the OpenAPI document into a structured object.

2. **Static Mining**
   - **Extract** request-parameter and response-schema descriptions.
   - **Observation**: LLMs identify candidate constraints (e.g., value ranges, format rules).
   - **Confirmation**: LLMs re-validate to reduce hallucinations (Observation-Confirmation scheme) .
   - **Filter** out syntactically invalid or unverifiable constraints .
3. **Dynamic Mining**
   - Feed actual API responses into AGORA (Daikon), deriving invariants missed by static analysis .
4. **Combine Constraints**
   - Merge static constraints & dynamic invariants.
   - When both cover the same variable, choose the stricter condition via LLM reasoning .
5. **Generate Test Code**
   - For each unified constraint, construct an LLM prompt (Figure 7) and generate a Python test function .
6. **Semantic Verification**
   - Cross-check generated tests against “example” values in the spec.
   - Discard any test that fails to validate its own correct example .
7. **Execute & Report**
   - Run each test against the live SUT, collecting outcomes:
     - **matched** (constraint holds),
     - **mismatched** (constraint violated),
     - **unknown** (property absent).
   - Aggregate mismatches into a report for developers.

---

#### JSON-Style Component Schema

```json
{
  "SpecLoader": {
    "in": ["openapi_spec_file"],
    "out": ["parsed_spec"]
  },
  "StaticConstraintMiner": {
    "in": ["parsed_spec"],
    "steps": {
      "describe": { "in": ["parsed_spec"], "out": ["descriptions"] },
      "observe": { "in": ["descriptions"], "out": ["candidates"] },
      "confirm": { "in": ["candidates"], "out": ["static_constraints"] },
      "filter": {
        "in": ["static_constraints"],
        "out": ["filtered_constraints"]
      }
    }
  },
  "DynamicConstraintMiner": {
    "in": ["api_responses"],
    "out": ["dynamic_invariants"]
  },
  "ConstraintCombiner": {
    "in": ["filtered_constraints", "dynamic_invariants"],
    "out": ["unified_constraints"]
  },
  "TestGenerator": {
    "in": ["unified_constraints", "parsed_spec"],
    "out": ["raw_test_code"]
  },
  "SemanticVerifier": {
    "in": ["raw_test_code", "parsed_spec.examples"],
    "out": ["verified_test_code"]
  },
  "TestExecutor": {
    "in": ["verified_test_code"],
    "out": ["test_results"]
  },
  "Reporter": {
    "in": ["test_results"],
    "out": ["mismatch_report"]
  }
}
```

### Detailed

---

#### 1. System-Level I/O

```json
{
  "system": {
    "inputs": [
      {
        "name": "OpenAPI/Swagger specification",
        "type": "YAML or JSON file",
        "description": "Full API contract including paths, parameters, schemas, examples"
      },
      {
        "name": "API execution data",
        "type": "List<HTTPResponse>",
        "description": "Recorded responses (bodies, headers, status codes) from live or previous SUT runs",
        "optional": true
      }
    ],
    "outputs": [
      {
        "name": "Generated test cases",
        "type": "List<PythonScript>",
        "description": "Self-contained pytest functions verifying each mined constraint"
      },
      {
        "name": "Test results",
        "type": "List<TestOutcome>",
        "description": "For each test: { test_name, status: matched|mismatched|unknown, details }"
      },
      {
        "name": "Mismatch report",
        "type": "JSON",
        "description": "Aggregated list of spec vs. response inconsistencies per endpoint"
      }
    ]
  }
}
```

---

#### 2. Component Breakdown

| Component                               | Input                                              | Output                                                                                       | Notes & Schema Details                                                              |
| --------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **1. Spec Loader**                      | • OpenAPI/Swagger file                             | • `parsed_spec` (dict)                                                                       | Parses into a dict with keys `paths`, `components`, etc.                            |
| **2. Static Constraint Miner**          | • `parsed_spec`                                    | • `static_constraints`:<br>– Request-Response constraints<br>– Response-Property constraints | Uses LLM with Observation-Confirmation to extract logical rules from descriptions . |
| • Description Extractor                 | • `parsed_spec`                                    | • `descriptions` (param/property → text)                                                     |                                                                                     |
| • Observation Phase                     | • `descriptions`                                   | • `candidates` (textual constraint hypotheses)                                               |                                                                                     |
| • Confirmation Phase                    | • `candidates`                                     | • `validated_static_constraints`                                                             |                                                                                     |
| • Syntactic Filter                      | • `validated_static_constraints`                   | • `filtered_constraints`                                                                     | Removes invalid or unmatchable rules.                                               |
| **3. Dynamic Constraint Miner (AGORA)** | • `api_responses`                                  | • `dynamic_invariants` (List<Invariant>)                                                     | Leverages Daikon to infer invariants from runtime data .                            |
| **4. Constraint Combiner**              | • `filtered_constraints`<br>• `dynamic_invariants` | • `unified_constraints`                                                                      | Merges both sets, choosing stricter when overlapping .                              |
| **5. Test Case Generator**              | • `unified_constraints`<br>• `parsed_spec`         | • `raw_test_code` (List<str>)                                                                | Builds LLM prompts (Figure 7) and generates Python code .                           |
| **6. Semantic Verifier**                | • `raw_test_code`<br>• `parsed_spec.examples`      | • `verified_test_code` (List<str>)                                                           | Runs each test against spec “examples,” discards failures .                         |
| **7. Test Executor**                    | • `verified_test_code`<br>• live API endpoint      | • `test_results` (List<TestOutcome>)                                                         | Executes tests, labels each as matched/mismatched/unknown .                         |
| **8. Reporter**                         | • `test_results`                                   | • `mismatch_report` (JSON)                                                                   | Aggregates all mismatches into developer-friendly report.                           |

---

#### 3. Detailed JSON-Style Schema for Key Artifacts

```json
{
  "parsed_spec": {
    "paths": {
      "/v1/charges": {
        "get": {
          "parameters": [
            { "name": "created[gt]", "type": "integer", "description": "…", "example": 1679090500 },
            …
          ],
          "responses": {
            "200": {
              "schema": { "$ref": "#/components/schemas/ChargeList" },
              "examples": { "default": { "data": [ /* … */ ] } }
            }
          }
        },
        …
      }
    },
    "components": {
      "schemas": {
        "Charge": {
          "type": "object",
          "properties": {
            "amount": { "type": "integer", "description": "positive integer ≤ 8 digits", "example": 99999999 },
            …
          }
        }
      }
    }
  },
  "Constraint": {
    "type": "request-response" | "response-property",
    "endpoint": "/v1/charges",
    "method": "GET",
    "parameter": "created[gt]",           // for request-response
    "property": "created",                // mapped property
    "condition": "response.created > created_gt",
    "description": "Response timestamp must be > created[gt]"
  },
  "Invariant": {
    "variables": ["size(response.data)"],
    "relation": "input.limit >= size(response.data)"
  },
  "TestCase": {
    "name": "test_charge_created_interval",
    "script": "def test_charge_created_interval(response, created_gt):\\n    …",
    "type": "request-response" | "response-property"
  },
  "TestOutcome": {
    "test_name": "test_charge_amount_positive",
    "status": "matched" | "mismatched" | "unknown",
    "details": {
      "expected": "> 0",
      "actual": -100
    }
  },
  "MismatchReport": {
    "/v1/charges": [
      {
        "property": "amount",
        "constraint": "amount > 0",
        "observed": -100,
        "status": "mismatched"
      }
    ],
    …
  }
}

```

---

#### 4. End-to-End Workflow Narrative

1. **Spec Loading**
   Load and parse the OAS file into `parsed_spec`.
2. **Static Mining**
   a. Extract all natural-language descriptions.
   b. **Observation**: LLM proposes candidate constraints from each description.
   c. **Confirmation**: LLM re-validates each candidate to reduce hallucination.
   d. Filter out any rules that don’t map to actual response properties.
3. **Dynamic Mining**
   If `api_responses` are provided, feed them into AGORA/Daikon to infer runtime invariants.
4. **Constraint Combining**
   Merge static constraints and dynamic invariants into one unified set, resolving overlaps by picking the stricter rule.
5. **Test Generation**
   For each unified constraint: - Formulate a prompt (per Figure 7) including the constraint, parameter/property names, and response schema. - Invoke LLM to emit a pytest-style function verifying the rule.
6. **Semantic Verification**
   Run each generated test against the spec’s example values. Discard tests that fail on their own correct examples.
7. **Execution**
   Deploy the verified tests against the live API, collecting pass/fail/unknown for each.
8. **Reporting**
   Collate mismatches into a structured JSON report for developers, highlighting spec vs. implementation inconsistencies.

---

## KAT

### High-level

---

#### System-Level I/O

```json
{
  "system": {
    "inputs": [
      {
        "name": "OpenAPI/Swagger spec",
        "type": "YAML/JSON",
        "description": "Full API contract including operations, parameters, schemas, and descriptions"
      }
    ],
    "outputs": [
      {
        "name": "Test scripts",
        "type": "Groovy or Python code",
        "description": "Executable sequences covering inter-operation and inter-parameter dependencies"
      },
      {
        "name": "Test data",
        "type": "JSONL files",
        "description": "Valid and invalid payloads per operation"
      },
      {
        "name": "Coverage & result report",
        "type": "JSON/HTML",
        "description": "Status-code coverage metrics, undocumented codes, false-positive reduction"
      }
    ]
  }
}
```

_KAT takes only the OAS spec as input and emits both code and coverage artifacts._

---

#### Core Components

| Component                       | Input                                                                                    | Output                                                                                | Source                                                                      |
| ------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **1. ODG Constructor**          | • OAS spec                                                                               | • Operation Dependency Graph (ODG)<br>• OS (Operation→Schema)<br>• SS (Schema→Schema) | Builds ODG via heuristic + GPTgenOperationSchemaDep + GPTgenSchemaSchemaDep |
| **2. Operation Sequencer**      | • ODG                                                                                    | • List of operation sequences (chains of dependent calls)                             | Traverses ODG to produce ordered sequences                                  |
| **3. Test Data Generator**      | • Single operation metadata<br>• Referenced schema(s)<br>• Inter-parameter deps from GPT | • Valid data JSONL<br>• Invalid data JSONL<br>• Python validation scripts             | Prompts GPT to emit 10 valid/invalid items per operation (Fig. 9)           |
| **4. Test Script Generator**    | • Operation sequences<br>• Test data files                                               | • Groovy/Python test scripts                                                          | Uses ODG sequences and test data to synthesize exec code (Fig. 11)          |
| **5. Experience Reinforcement** | • Past test outcomes (success/failure)                                                   | • Updated prompt templates or ODG weights                                             | Stores and learns from test runs to refine future generations               |

---

#### End-to-End Workflow

1. **Load Spec**
   Parse the OpenAPI document into a structured model (`paths`, `components`, `schemas`).
2. **Construct ODG**
   - **Heuristic pass**: match input/output names.
   - **GPT-based pass**: infer Operation-Schema (OS) and Schema-Schema (SS) deps, then gather new edges via Algorithm 1.
3. **Generate Sequences**
   Topologically sort ODG to form ordered call chains (e.g. `GET /flights → POST /booking`).
4. **Generate Test Data**
   For each operation: - Prompt GPT for 10 valid and 10 invalid JSONL cases. - Produce accompanying Python scripts that assert inter-parameter constraints.
5. **Generate Test Scripts**
   Embed data references into Groovy/Python templates, chaining operations per sequence and asserting status codes (2xx/4xx).
6. **Execute & Report**
   Run generated scripts against the live API; collect coverage metrics, undocumented codes, and false-positive rates into a final report.

---

#### JSON-Style Component Schema

```json
{
  "ODGConstructor": {
    "in": ["oas_spec"],
    "out": ["odg_graph", "os_dict", "ss_dict"]
  },
  "OperationSequencer": {
    "in": ["odg_graph"],
    "out": ["operation_sequences"]
  },
  "TestDataGenerator": {
    "in": ["operation_meta", "referenced_schema", "param_deps"],
    "out": ["valid_data.jsonl", "invalid_data.jsonl", "validation_script.py"]
  },
  "TestScriptGenerator": {
    "in": ["operation_sequences", "data_files"],
    "out": ["test_script.groovy", "pytest_suite.py"]
  },
  "ExperienceReinforcement": {
    "in": ["test_results"],
    "out": ["refined_prompts", "updated_dep_weights"]
  }
}
```

### Detailed

---

#### System-Level I/O

```json
{
  "system": {
    "inputs": [
      {
        "name": "OpenAPI/Swagger specification",
        "type": "YAML or JSON file",
        "description": "Complete OAS including operations, parameters, schemas, descriptions"
      }
    ],
    "outputs": [
      {
        "name": "Test scripts",
        "type": "Groovy or Python code files",
        "description": "Executable sequences covering inter-operation and inter-parameter dependencies"
      },
      {
        "name": "Test data sets",
        "type": "JSONL files",
        "description": "Valid and invalid payloads per operation"
      },
      {
        "name": "Coverage & result report",
        "type": "JSON or HTML",
        "description": "Status-code coverage metrics, undocumented codes, false-positive counts"
      }
    ]
  }
}
```

KAT uses only the OAS spec as input and produces both code artifacts and coverage reports .

---

#### Core Components

| Component                       | Input                                                                              | Output                                                                                               | Details & Schema Snippets                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **1. ODG Constructor**          | • OAS spec                                                                         | • `odg_graph` (Operation Dependency Graph)<br>• `OS` dict (Op→Schema)<br>• `SS` dict (Schema→Schema) | Builds graph via heuristic + GPT-based passes (Alg. 1) .                         |
| **2. Operation Sequencer**      | • `odg_graph`                                                                      | • `operation_sequences` (ordered lists of operations)                                                | Topological sort of ODG to form call chains .                                    |
| **3. Test Data Generator**      | • Single operation metadata<br>• Referenced schemas<br>• Inter-param deps from GPT | • `valid_data.jsonl`<br>• `invalid_data.jsonl`<br>• `validation_script.py`                           | Prompts GPT for 10 valid/invalid items; emits Python validators .                |
| **4. Test Script Generator**    | • `operation_sequences`<br>• Data files                                            | • `test_suite.groovy` or `pytest_suite.py`                                                           | Embeds data into templates, chains calls with `makeRequest`/`assertStatusCode` . |
| **5. Experience Reinforcement** | • Past test outcomes (success/failure)                                             | • Updated prompt templates<br>• Adjusted ODG weights                                                 | Stores results to refine GPT prompts and dependency inference .                  |

---

#### Artifact Schemas

```json
{
  "OS": {
    "post-/booking": {
      "Flight": { "flightId": "id" },
      "Booking": { "flightId": "flight" }
    }
  },
  "SS": {
    "Flight": [],
    "Booking": ["Flight"]
  },
  "DataItem": {
    "data": { /* operation-specific fields */ },
    "expected_code": 200
  },
  "TestScript": {
    "language": "Groovy" | "Python",
    "content": "string of code"
  },
  "CoverageReport": {
    "operation": "/booking",
    "documented_codes": [200,400],
    "covered_codes": [200],
    "undocumented_codes": [422]
  }
}

```

OS and SS dictionaries model operation-schema and schema-schema deps (Fig. 5 & 7) .

---

#### End-to-End Workflow

1. **Load & Parse Spec**
   Read the OAS file into in-memory structures (`paths`, `components`, `schemas`).
2. **Construct ODG**
   - **Heuristic pass**: match output fields to input params.
   - **GPT-based passes**:
     - **Operation→Schema**: invoke GPT to map each operation’s parameters to prerequisite schemas.
     - **Schema→Schema**: invoke GPT to find hierarchical schema deps.
   - Merge heuristic and GPT edges into `odg_graph` via Algorithm 1 .
3. **Generate Operation Sequences**
   Topologically sort `odg_graph` to produce ordered sequences of API calls (e.g. `GET /flights → POST /booking`) .
4. **Generate Test Data**
   For each operation in each sequence: - Prompt GPT (Fig. 9) to emit 10 valid and 10 invalid JSONL data items. - Generate a Python validation script capturing inter-parameter constraints (e.g., `arrivalDate > departureDate`). - Output `valid_data.jsonl`, `invalid_data.jsonl`, and `validation_script.py` .
5. **Generate Test Scripts**
   - For each sequence, embed data file paths into Groovy/Python templates.
   - Use custom helpers (`makeRequest`, `assertStatusCode`) to chain calls and assert status codes.
   - Produce executable test suites (`test_suite.groovy` or `pytest_suite.py`) .
6. **Execute & Collect**
   - Run generated scripts against the live API.
   - Collect outcomes per test: `matched` (2xx as expected), `mismatched` (violation), or `unknown` (absent field).
7. **Experience Reinforcement**
   - Store test outcomes in Postgres/Redis.
   - Retrain prompt templates and adjust ODG edge weights to improve future runs.
   - Log metrics (coverage deltas, false positives) for LangSmith RLHF evaluations .
8. **Reporting**
   - Aggregate coverage metrics and undocumented status codes into a JSON/HTML dashboard.
   - Highlight reductions in false positives and increases in coverage (e.g., +15.7% overall) .

---

## Combine

---

#### System-Level I/O

```json
{
  "system": {
    "inputs": [
      {
        "name": "OpenAPI/Swagger specification",
        "type": "YAML/JSON file",
        "description": "Complete API contract: operations, parameters, schemas, descriptions"
      },
      {
        "name": "API execution logs",
        "type": "List<HTTPResponse>",
        "description": "(Optional) Recorded responses for dynamic analysis"
      }
    ],
    "outputs": [
      {
        "name": "Test suites",
        "type": "Groovy/Python code files",
        "description": "Executable scripts covering dependency chains, constraints, and data scenarios"
      },
      {
        "name": "Test data sets",
        "type": "JSONL files",
        "description": "Valid & invalid payloads per operation, with inter-param exceptions"
      },
      {
        "name": "Coverage & mismatch report",
        "type": "JSON/HTML dashboard",
        "description": "Status-code coverage, undocumented codes, constraint mismatches, false-positive rates"
      }
    ]
  }
}
```

---

#### Core Component Matrix

| Component                        | Input                                                      | Output                                                             | Source                |
| -------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ | --------------------- |
| **1. Spec Loader**               | • OAS spec file                                            | • `parsed_spec` (dict model)                                       | RBCTest               |
| **2. ODG Constructor**           | • `parsed_spec`                                            | • `odg_graph` (Op→Op), `OS` (Op→Schema), `SS` (Schema→Schema)      | KAT                   |
| **3. Static Constraint Miner**   | • `parsed_spec`                                            | • `static_constraints` (request-response + property rules)         | RBCTest               |
| **4. Dynamic Constraint Miner**  | • API execution logs                                       | • `dynamic_invariants` (Daikon-derived invariants)                 | RBCTest               |
| **5. Operation Sequencer**       | • `odg_graph`                                              | • `operation_sequences` (ordered op chains)                        | KAT                   |
| **6. Constraint Combiner**       | • `static_constraints`• `dynamic_invariants`               | • `unified_constraints` (strictest merge)                          | RBCTest               |
| **7. Test Data Generator**       | • Single-op metadata• `OS`, `SS` deps• `parsed_spec`       | • `valid_data.jsonl`• `invalid_data.jsonl`• `validation_script.py` | KAT                   |
| **8. Test Script Generator**     | • `operation_sequences`• `unified_constraints`• data files | • `test_suite.groovy` / `pytest_suite.py`                          | RBCTest + KAT amalgam |
| **9. Semantic Verifier**         | • Generated test code• `parsed_spec.examples`              | • `verified_test_code` (pruned scripts)                            | RBCTest               |
| **10. Test Executor**            | • `verified_test_code`• live API endpoints                 | • `test_results` (matched/mismatched/unknown)                      | common                |
| **11. Experience Reinforcement** | • `test_results`                                           | • `refined_prompts`• adjusted `odg_graph` weights                  | KAT                   |
| **12. Reporter**                 | • `test_results`                                           | • `coverage_report.json`• interactive HTML dashboard               | common                |

---

#### JSON-Style Component Schema

```json
{
  "SpecLoader": {
    "in": ["oas_spec_file"],
    "out": ["parsed_spec"]
  },
  "ODGConstructor": {
    "in": ["parsed_spec"],
    "out": ["odg_graph", "OS", "SS"]
  },
  "StaticConstraintMiner": {
    "in": ["parsed_spec"],
    "out": ["static_constraints"]
  },
  "DynamicConstraintMiner": {
    "in": ["api_execution_logs"],
    "out": ["dynamic_invariants"]
  },
  "OperationSequencer": {
    "in": ["odg_graph"],
    "out": ["operation_sequences"]
  },
  "ConstraintCombiner": {
    "in": ["static_constraints", "dynamic_invariants"],
    "out": ["unified_constraints"]
  },
  "TestDataGenerator": {
    "in": ["operation_meta", "OS", "SS", "parsed_spec"],
    "out": ["valid_data.jsonl", "invalid_data.jsonl", "validation_script.py"]
  },
  "TestScriptGenerator": {
    "in": ["operation_sequences", "unified_constraints", "data_files"],
    "out": ["test_suite.groovy", "pytest_suite.py"]
  },
  "SemanticVerifier": {
    "in": ["generated_test_code", "parsed_spec.examples"],
    "out": ["verified_test_code"]
  },
  "TestExecutor": {
    "in": ["verified_test_code", "live_api_endpoints"],
    "out": ["test_results"]
  },
  "ExperienceReinforcement": {
    "in": ["test_results"],
    "out": ["refined_prompts", "updated_odg_weights"]
  },
  "Reporter": {
    "in": ["test_results"],
    "out": ["coverage_report.json", "dashboard.html"]
  }
}
```

---

#### End-to-End Workflow

1. **Spec Loading**

   Parse OAS into `parsed_spec`.

2. **Dependency & Constraint Mining**
   - **Static**: extract logical constraints from parameter & schema descriptions via LLM (Observation-Confirmation) .
   - **Dynamic**: ingest `api_execution_logs` into Daikon to infer invariants .
3. **ODG Construction**
   - Heuristic + GPT pass to build `odg_graph`, `OS`, `SS` .
4. **Sequence Generation**

   Topologically sort `odg_graph` → `operation_sequences` .

5. **Constraint Combining**

   Merge static & dynamic findings → `unified_constraints` .

6. **Data Generation**

   For each operation: GPT → `valid_data.jsonl`/`invalid_data.jsonl`; gen Python “validation_script.py” .

7. **Script Generation**

   Stitch `operation_sequences`, `unified_constraints`, data files → test suites (`.groovy`/`.py`).

8. **Semantic Verification**

   Run scripts against spec examples → prune invalid tests .

9. **Execution**

   Execute verified tests against live API → `test_results`.

10. **Reinforcement**

    Feed `test_results` into RLHF pipeline → refine LLM prompts & adjust `odg_graph` weights .

11. **Reporting**

    Aggregate coverage, undocumented codes, false-positives → JSON/HTML dashboard.

---
