# API Constraint Miner & Verifier

This project is designed to **automatically mine and verify constraints** from API specifications. It primarily operates in two phases:

1. **Constraint Mining** (via the `miner/` folder)
2. **Constraint Verification** (via the `verifier/` folder)

The overall pipeline extracts request-response and response-property constraints from an API, saves them into an Excel file, and performs semantic verification of those constraints.

---

## Folder Structure

```
.
├── miner/
│   ├── __init__.py
│   ├── constraint_extractor.py
│   ├── parameter_mapper.py
│   ├── request_response_miner.py
│   └── response_property_miner.py
└── verifier/
    ├── script_executor.py
    └── sematic_verifier.py
```

---

## miner/

This folder handles **constraint mining** from the provided API Specification.

### Main Files

#### `request_response_miner.py`

- **Purpose**: Mines **request-response constraints**.
- **How it works**:
  - Makes actual **API calls** to collect real responses.
  - Extracts constraints that connect request parameters to response values.
  - Appends this data into a resulting Excel file.

#### `response_property_miner.py`

- **Purpose**: Mines **response-property constraints**.
- **How it works**:
  - Analyzes the **structure and properties** of response data.
  - Identifies possible constraints (e.g., type, format, value ranges).
  - Saves findings into the same Excel report.

### Helper Files

#### `constraint_extractor.py`

- Contains logic to **extract and define constraint rules** based on given data or heuristics.
- Used by both `request_response_miner.py` and `response_property_miner.py`.

#### `parameter_mapper.py`

- Maps API **spec-defined parameters** to real data used in request/response mining.
- Assists in interpreting the specification format and populating API requests accordingly.

---

## Output Format

Both miners generate an **Excel file** (.xlsx) which includes:

- API Endpoint
- Method
- Constraint Type (request-response / response-property)
- Details of the constraint
- Request and response samples (for request-response)

---

## verifier/

This folder performs **verification** of constraints mined in the previous step.

### `script_executor.py`

- Runs API requests based on constraint data.
- Provides inputs to the verifier and collects outputs.
- Can be used to automate multiple verification runs.

### `sematic_verifier.py`

- The core **semantic verifier** that evaluates constraints.
- Returns:
  - `1` if constraint is satisfied,
  - `0` if constraint is violated,
  - `-1` if the result is inconclusive (e.g., missing or incompatible data).

---

## Usage Guide

1. **Mine Constraints**:

   ```bash
   python request_response_miner.py
   python response_property_miner.py
   ```

   These will output an Excel file (e.g., `constraints.xlsx`) with extracted constraint data.

2. **Verify Constraints**:

   ```bash
   python script_executor.py
   ```

   This will read from the Excel file, perform necessary API requests, and use `sematic_verifier.py` to produce validation results.
