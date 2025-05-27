# RESTful API Testing Framework

A comprehensive framework for automated testing of RESTful APIs, supporting OpenAPI specification validation, contract testing, and scenario-based testing.

## Features

- **OpenAPI Specification Parser**: Analyze API specifications to extract endpoints, parameters, schemas, and authentication requirements
- **Schema Validation**: Automatically validate request and response schemas against OpenAPI definitions
- **API Testing**: Test RESTful APIs with built-in request building and response validation
- **Code Execution**: Run Python code for test setup and validation
- **Type-Safe Design**: Strongly typed interfaces for all components using Python type hints
- **Constraint Mining**: Automatically identify constraints and generate validation scripts
- **Validation Framework**: Execute validation scripts against API responses

## Architecture

The framework follows a modular architecture with the following key components:

### Core Components

- **BaseTool**: Abstract base class for all tools with standardized execution flow
- **BaseAgent**: Foundation for agents that can coordinate multiple tools to perform complex tasks

### Tools

- **OpenAPIParserTool**: Parses OpenAPI/Swagger specifications to extract API details
- **RESTAPICallerTool**: Performs HTTP requests to API endpoints with authentication support
- **CodeExecutorTool**: Executes Python code snippets for test setup and validation
- **StaticConstraintMinerTool**: Analyzes API specs to identify constraints
- **TestScriptGeneratorTool**: Generates validation scripts from constraints
- **TestExecutionReporterTool**: Collects and formats test execution results

### Agents

- **RESTAPIAgent**: Coordinates API testing using results from OpenAPI parsing

## Project Structure

```plaintext
restful-api-testing-framework/
├── src/                        # Source code
│   ├── agents/                 # Agent implementations
│   ├── core/                   # Core abstractions (BaseTool, BaseAgent)
│   ├── schemas/                # Pydantic schema definitions
│   │   ├── core/               # Core schema definitions
│   │   └── tools/              # Tool-specific schemas
│   ├── tools/                  # Tool implementations
│   └── utils/                  # Utility functions and helpers
├── data/                       # Sample API specifications and test data
│   ├── example/                # Example OpenAPI specs
│   └── RBCTest_dataset/        # Test datasets for various APIs
├── example/                    # Example code and usage patterns
└── docs/                       # Documentation
```

## Installation

```bash
# Clone the repository
git clone https://github.com/HZeroxium/restful-api-testing-framework.git

# Navigate to project directory
cd restful-api-testing-framework

# Install dependencies
pip install -r requirements.txt
```

## Usage

### OpenAPI Specification Parsing

```python
python ./src/openapi_parser_tool.py
```

### Code Execution

```python
python ./src/code_executor_tool.py
```

### REST API Caller

```python
python ./src/rest_api_caller_tool.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
