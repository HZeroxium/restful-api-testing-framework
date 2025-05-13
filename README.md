# RESTful API Testing Framework

A comprehensive framework for automated testing of RESTful APIs, supporting OpenAPI specification validation, contract testing, and scenario-based testing.

## Features

- **OpenAPI Specification Testing**: Validate API implementations against their OpenAPI specifications
- **Automated Test Generation**: Create test cases directly from OpenAPI specs
- **Scenario-Based Testing**: Define and run complex test scenarios with dependencies
- **Response Validation**: Automatically validate response formats and content
- **Extensible Architecture**: Add custom validators and test helpers

## Installation

```bash
# Clone the repository
git clone https://github.com/HZeroxium/restful-api-testing-framework.git

# Navigate to project directory
cd restful-api-testing-framework

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```bash
restful-api-testing-framework/
├── docs/                       # Documentation
├── example/                    # Example implementations
│   └── google-adk/             # Google ADK examples
├── data/                       # Test data and OpenAPI specifications
│   └── RBCTest_dataset/        # Sample API specifications
├── src/                        # Source code
├── tests/                      # Framework tests
├── README.md                   # This file
└── requirements.txt            # Dependencies
```

## Example Code

```python
python -m src.examples.openapi_parser_tool
python -m src.examples.python_executor_tool
```
