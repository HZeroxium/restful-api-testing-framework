# RESTful API Testing Framework

A comprehensive framework for automated testing of RESTful APIs, supporting OpenAPI specification parsing, constraint mining, contract testing, and scenario-based testing with both programmatic and GUI interfaces.

## Features

- **OpenAPI Specification Parser**: Analyze API specifications to extract endpoints, parameters, schemas, and authentication requirements
- **Schema Validation**: Automatically validate request and response schemas against OpenAPI definitions
- **API Testing**: Test RESTful APIs with built-in request building and response validation
- **Code Execution**: Run Python code for test setup and validation
- **Constraint Mining**: Automatically identify constraints and generate validation scripts
- **Test Collection Generation**: Generate test cases based on API specifications
- **Test Execution**: Execute test collections against live APIs
- **Reporting**: Generate detailed test reports with pass/fail status and validation results
- **GUI Interface**: Streamlit-based user interface for interactive API exploration and testing
- **Type-Safe Design**: Strongly typed interfaces for all components using Python type hints
- **Test Collections**: Create, save, and reuse collections of API tests

## Architecture

The framework follows a modular architecture with the following key components:

### Core Components

- **Tools**: Self-contained components that perform specific operations
- **Schemas**: Pydantic models for type-safe data exchange between components
- **Utilities**: Helper functions and factories for common operations
- **Services**: Business logic management for test execution and data persistence

### Tools

- **OpenAPIParserTool**: Parses OpenAPI/Swagger specifications to extract API details
- **RestApiCallerTool**: Performs HTTP requests to API endpoints with authentication support
- **CodeExecutorTool**: Executes Python code snippets for test setup and validation
- **StaticConstraintMinerTool**: Analyzes API specs to identify constraints
- **TestCollectionGeneratorTool**: Generates tests based on API specifications
- **TestExecutionReporterTool**: Collects and formats test execution results

### Services

- **RestApiCallerFactory**: Creates endpoint-specific API caller tools
- **TestExecutionService**: Manages test execution and reporting
- **CollectionService**: Manages test collections

## Project Structure

```plaintext
restful-api-testing-framework/
├── src/                          # Source code
│   ├── tools/                    # Tool implementations
│   ├── schemas/                  # Pydantic schema definitions
│   │   └── tools/                # Tool-specific schemas
│   ├── utils/                    # Utility functions and helpers
│   ├── ui/                       # Streamlit UI components
│   ├── core/                     # Core services and abstractions
│   ├── openapi_parser_tool.py    # OpenAPI specification parser demo
│   ├── rest_api_caller_tool.py   # REST API caller tool demo
│   ├── code_executor_tool.py     # Code execution tool demo
│   ├── spec_to_rest_tools.py     # API test suite generator
│   ├── constraint_miner_demo.py  # Constraint mining demo
│   ├── api_test_runner_demo.py   # API test runner demo
│   └── api_test_gui.py           # Streamlit GUI application
├── data/                         # Sample API specifications and test data
│   ├── toolshop/                 # Toolshop API example
│   ├── example/                  # Example OpenAPI specs
│   └── scripts/                  # Test scripts for code execution
├── output/                       # Generated output (reports, test results)
└── docs/                         # Documentation
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/restful-api-testing-framework.git

# Navigate to project directory
cd restful-api-testing-framework

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

- Python 3.8+
- requests
- pydantic
- streamlit (for GUI)
- google-adk (for constraint mining)
- asyncio
- json

## Usage

### OpenAPI Specification Parser

Parse OpenAPI specifications to extract API details:

```bash
python src/openapi_parser_tool.py
```

This tool analyzes OpenAPI/Swagger files to extract endpoints, methods, parameters, and schemas for API testing.

### REST API Caller

Make HTTP requests to API endpoints:

```bash
python src/rest_api_caller_tool.py
```

Demonstrates how to call REST APIs with various methods (GET, POST, PUT, DELETE), parameters, and authentication.

### Code Executor

Execute Python code for test validation:

```bash
python src/code_executor_tool.py
```

Shows how to run Python code snippets with context variables for testing purposes, with timeout and security restrictions.

### API Test Suite Generator

Generate API testing tools from OpenAPI specifications:

```bash
python src/spec_to_rest_tools.py
```

Creates a suite of API testing tools from OpenAPI specifications, bridging parser and caller tools.

### Constraint Miner

Mine constraints from API specifications:

```bash
python src/constraint_miner_demo.py --spec data/toolshop/openapi.json
```

Analyzes API specifications to identify implicit and explicit constraints for validation.

### API Test Runner

Generate and run test collections:

```bash
python src/api_test_runner_demo.py
```

Demonstrates the complete workflow of generating test collections, executing tests, and creating reports.

### GUI Application

Launch the Streamlit-based user interface:

```bash
streamlit run src/api_test_gui.py
```

Provides an interactive interface for exploring APIs, creating test collections, executing tests, and viewing reports.

## Workflow

1. **Parse API Specification**: Use `OpenAPIParserTool` to extract API details
2. **Generate Test Collection**: Use `TestCollectionGeneratorTool` to create test cases
3. **Execute Tests**: Run tests using `RestApiCallerTool` for API calls
4. **Validate Responses**: Use `CodeExecutorTool` to execute validation scripts
5. **Generate Reports**: Use `TestExecutionReporterTool` for test reporting

## Example

```python
# Create and initialize an API test suite
api_suite = ApiTestSuiteGenerator(
    spec_source="path/to/openapi.json",
    source_type=SpecSourceType.FILE,
    verbose=True
)
await api_suite.initialize()

# Get a tool for a specific endpoint
product_search_tool = api_suite.get_tool_by_name("get_products_search")

# Execute an API call with parameters
result = await product_search_tool.execute({"q": "hammer"})
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
