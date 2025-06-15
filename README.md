# RESTful API Testing Framework

A comprehensive, enterprise-grade framework for automated testing of RESTful APIs with AI-powered constraint mining, multi-agent architecture, advanced caching, and sophisticated UI components. Built with modern Python practices and designed for scalability, maintainability, and extensibility.

## 🚀 Key Features

### Core Testing Capabilities

- **OpenAPI/Swagger Specification Parser**: Deep analysis of API specifications with schema extraction and validation
- **Multi-Agent Architecture**: Modular agent-based system for distributed API testing and analysis
- **Constraint Mining**: AI-powered extraction of implicit and explicit API constraints using LLM integration
- **Contract Testing**: Automated validation against OpenAPI specifications
- **Schema Validation**: Comprehensive request/response schema validation with detailed error reporting
- **Test Collection Management**: Create, save, execute, and manage collections of API tests
- **Advanced Reporting**: Detailed test execution reports with metrics, visualizations, and export capabilities

### Advanced Infrastructure

- **Extensible Caching System**: Multi-tier caching with Memory, File, and Redis support
- **Sophisticated Logging**: Contextual logging with separate console/file levels and colored output
- **Type-Safe Design**: Comprehensive Pydantic models with full type safety throughout
- **Asynchronous Processing**: High-performance async/await patterns for concurrent operations
- **Factory Patterns**: Flexible component instantiation with dependency injection

### User Interfaces

- **Streamlit GUI**: Interactive web-based interface for API exploration and testing
- **CLI Tools**: Command-line utilities for automation and CI/CD integration
- **Component Library**: Reusable UI components for custom dashboard creation

### AI-Powered Features

- **LLM Integration**: OpenAI/Google AI integration for intelligent constraint analysis
- **Dynamic Test Generation**: AI-driven test case creation based on API specifications
- **Intelligent Validation**: Smart response validation using machine learning patterns

## 🏗️ Architecture Overview

The framework follows a sophisticated multi-layered architecture:

### Core Architecture Layers

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ Streamlit   │  │ CLI Tools   │  │ Component       │    │
│  │ GUI         │  │             │  │ Library         │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ Services    │  │ Agents      │  │ Tools           │    │
│  │             │  │             │  │                 │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ Caching     │  │ Logging     │  │ Utilities       │    │
│  │ System      │  │ System      │  │                 │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Component Overview

#### 🛠️ Tools (Self-Contained Components)

- **OpenAPIParserTool**: Parse and analyze OpenAPI/Swagger specifications
- **RestApiCallerTool**: Execute HTTP requests with authentication and validation
- **CodeExecutorTool**: Safe Python code execution with sandboxing
- **StaticConstraintMinerTool**: Extract constraints from API specifications
- **TestCaseGeneratorTool**: Generate test cases from specifications
- **TestCollectionGeneratorTool**: Create comprehensive test collections
- **TestSuiteGeneratorTool**: Build complete test suites
- **TestExecutionReporterTool**: Generate detailed execution reports
- **TestDataGeneratorTool**: Create test data based on schemas
- **OperationSequencerTool**: Sequence API operations for dependency testing

#### 🤖 Agents (Intelligent Coordinators)

- **RestApiAgent**: Coordinate API testing workflows
- **SpecLoaderAgent**: Manage specification loading and parsing

#### ⚙️ Services (Business Logic Management)

- **TestExecutionService**: Orchestrate test execution workflows
- **TestCollectionService**: Manage test collection lifecycle
- **RestApiCallerFactory**: Create endpoint-specific API callers

#### 🎨 UI Components

- **Explorer**: Interactive API specification browser
- **Tester**: Test execution and validation interface
- **Collections**: Test collection management
- **Common Components**: Reusable UI elements (cards, badges, metrics, etc.)

## 📁 Project Structure

```plaintext
restful-api-testing-framework/
├── src/                                    # Source code
│   ├── agents/                             # Multi-agent system
│   │   ├── rest_api_agent.py              # Main API testing agent
│   │   └── spec_loader/                    # Specification loading agents
│   ├── tools/                              # Core tool implementations
│   │   ├── openapi_parser.py              # OpenAPI specification parser
│   │   ├── rest_api_caller.py             # HTTP request executor
│   │   ├── code_executor.py               # Safe code execution
│   │   ├── static_constraint_miner.py     # Constraint extraction
│   │   ├── test_case_generator.py         # Test case creation
│   │   ├── test_collection_generator.py   # Collection management
│   │   ├── test_suite_generator.py        # Suite generation
│   │   ├── test_execution_reporter.py     # Report generation
│   │   ├── test_data_generator.py         # Test data creation
│   │   ├── operation_sequencer.py         # Operation sequencing
│   │   └── constraint_miner/              # Advanced constraint mining
│   ├── schemas/                            # Type-safe data models
│   │   ├── core/                          # Base schemas
│   │   ├── tools/                         # Tool-specific schemas
│   │   └── test_collection.py             # Test collection models
│   ├── core/                              # Core abstractions
│   │   ├── base_tool.py                   # Tool base class
│   │   ├── base_agent.py                  # Agent base class
│   │   ├── services/                      # Business services
│   │   └── repositories/                  # Data access layer
│   ├── utils/                             # Utility functions
│   │   ├── api_utils.py                   # API helpers
│   │   ├── schema_utils.py                # Schema utilities
│   │   ├── report_utils.py                # Reporting helpers
│   │   ├── llm_utils.py                   # LLM integration
│   │   └── rest_api_caller_factory.py     # Factory patterns
│   ├── ui/                                # User interface components
│   │   ├── components/                    # Reusable UI components
│   │   │   ├── common/                    # Common components
│   │   │   ├── explorer/                  # API explorer components
│   │   │   ├── tester/                    # Testing components
│   │   │   └── collections/               # Collection components
│   │   ├── explorer.py                    # API exploration interface
│   │   ├── tester.py                      # Testing interface
│   │   ├── collections.py                 # Collection management
│   │   └── styles.py                      # UI styling
│   ├── common/                            # Common infrastructure
│   │   ├── cache/                         # Caching system
│   │   │   ├── cache_interface.py         # Cache contracts
│   │   │   ├── in_memory_cache.py         # Memory cache
│   │   │   ├── file_cache.py              # File-based cache
│   │   │   ├── redis_cache.py             # Redis cache
│   │   │   ├── cache_factory.py           # Cache factory
│   │   │   └── decorators.py              # Caching decorators
│   │   └── logger/                        # Logging system
│   │       ├── logger_interface.py        # Logger contracts
│   │       ├── standard_logger.py         # Standard logger
│   │       ├── print_logger.py            # Simple logger
│   │       └── logger_factory.py          # Logger factory
│   ├── config/                            # Configuration
│   │   ├── settings.py                    # Application settings
│   │   ├── constants.py                   # Constants
│   │   └── prompts/                       # AI prompt templates
│   ├── main.py                            # Main application entry
│   ├── api_test_gui.py                    # Streamlit GUI application
│   └── demo scripts/                      # Demonstration tools
│       ├── openapi_parser_tool.py         # Parser demo
│       ├── rest_api_caller_tool.py        # API caller demo
│       ├── code_executor_tool.py          # Code execution demo
│       ├── constraint_miner_tool.py       # Constraint mining demo
│       ├── test_case_generator_tool.py    # Test generation demo
│       ├── api_test_runner.py             # Test runner demo
│       ├── cache_demo.py                  # Caching system demo
│       └── logger_demo.py                 # Logging system demo
├── data/                                   # Sample data and specifications
│   ├── RBCTest_dataset/                   # Research datasets
│   ├── toolshop/                          # Toolshop API examples
│   ├── example/                           # Example specifications
│   └── scripts/                           # Test scripts
├── output/                                # Generated outputs
├── docs/                                  # Documentation
│   └── Architecture.md                    # Architecture documentation
├── requirements.txt                       # Python dependencies
└── README.md                             # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- pip package manager
- Git

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/your-username/restful-api-testing-framework.git
cd restful-api-testing-framework

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

#### Core Dependencies

- **requests**: HTTP library for API calls
- **pydantic**: Data validation and settings management
- **asyncio**: Asynchronous programming support
- **pathlib**: Modern path handling

#### UI Dependencies

- **streamlit**: Web-based GUI framework
- **plotly**: Interactive visualizations
- **pandas**: Data manipulation and analysis

#### AI/ML Dependencies

- **google-adk**: Google AI integration
- **openai**: OpenAI API integration (optional)

#### Caching Dependencies

- **redis**: Redis cache support (optional)

#### Testing Dependencies

- **pytest**: Testing framework
- **httpx**: Async HTTP client for testing

## 📖 Usage

### 1. OpenAPI Specification Parser

Parse and analyze OpenAPI/Swagger specifications:

```python
from tools.openapi_parser import OpenAPIParserTool
from schemas.tools.openapi_parser import OpenAPIParserRequest

# Initialize parser
parser = OpenAPIParserTool()

# Parse specification
request = OpenAPIParserRequest(
    spec_source="data/toolshop/openapi.json",
    source_type="file"
)

result = await parser.execute(request)
print(f"Found {len(result.endpoints)} endpoints")
print(f"API Info: {result.api_info.title} v{result.api_info.version}")
```

**CLI Usage:**

```bash
python src/openapi_parser_tool.py
```

### 2. REST API Caller

Execute HTTP requests with advanced features:

```python
from tools.rest_api_caller import RestApiCallerTool
from schemas.tools.rest_api_caller import RestApiCallerRequest

# Initialize caller
caller = RestApiCallerTool()

# Make API call
request = RestApiCallerRequest(
    method="GET",
    url="https://api.example.com/users",
    headers={"Authorization": "Bearer token"},
    params={"page": 1, "limit": 10}
)

result = await caller.execute(request)
print(f"Status: {result.status_code}")
print(f"Response: {result.response_data}")
```

**CLI Usage:**

```bash
python src/rest_api_caller_tool.py
```

### 3. Constraint Mining

Extract constraints from API specifications using AI:

```python
from tools.static_constraint_miner import StaticConstraintMinerTool
from schemas.tools.constraint_miner import ConstraintMinerRequest

# Initialize constraint miner
miner = StaticConstraintMinerTool()

# Mine constraints
request = ConstraintMinerRequest(
    spec_source="data/toolshop/openapi.json",
    source_type="file",
    enable_llm=True
)

result = await miner.execute(request)
print(f"Found {len(result.constraints)} constraints")

for constraint in result.constraints:
    print(f"- {constraint.type}: {constraint.description}")
```

**CLI Usage:**

```bash
python src/constraint_miner_tool.py --spec data/toolshop/openapi.json
```

### 4. Test Collection Generation

Generate comprehensive test collections:

```python
from tools.test_collection_generator import TestCollectionGeneratorTool
from schemas.tools.test_collection_generator import TestCollectionGeneratorRequest

# Initialize generator
generator = TestCollectionGeneratorTool()

# Generate test collection
request = TestCollectionGeneratorRequest(
    spec_source="data/toolshop/openapi.json",
    source_type="file",
    collection_name="Toolshop API Tests",
    include_positive_tests=True,
    include_negative_tests=True,
    include_edge_cases=True
)

result = await generator.execute(request)
print(f"Generated collection with {len(result.test_collection.test_cases)} test cases")
```

### 5. Code Execution

Execute Python code safely with context:

```python
from tools.code_executor import CodeExecutorTool
from schemas.tools.code_executor import CodeExecutorRequest

# Initialize executor
executor = CodeExecutorTool()

# Execute validation code
request = CodeExecutorRequest(
    code="""
# Validate API response
assert response.status_code == 200
assert 'users' in response.json()
assert len(response.json()['users']) > 0
result = {'validation': 'passed', 'user_count': len(response.json()['users'])}
""",
    context={"response": api_response},
    timeout=10
)

result = await executor.execute(request)
print(f"Execution result: {result.result}")
```

### 6. Caching System

Utilize the advanced caching system:

```python
from common.cache import CacheFactory, CacheType, cache_result

# Get cache instance
cache = CacheFactory.get_cache("api-cache", CacheType.MEMORY)

# Basic cache operations
cache.set("user:123", {"name": "John", "email": "john@example.com"}, ttl=300)
user_data = cache.get("user:123")

# Use caching decorators
@cache_result(ttl=300, cache_type=CacheType.MEMORY)
def expensive_api_call(endpoint: str):
    # Expensive operation
    return make_api_call(endpoint)

# Function result will be cached
result = expensive_api_call("/api/v1/users")
```

**Cache Demo:**

```bash
python src/cache_demo.py
```

### 7. Logging System

Implement sophisticated logging:

```python
from common.logger import LoggerFactory, LoggerType, LogLevel

# Get logger instance
logger = LoggerFactory.get_logger(
    name="api-testing",
    logger_type=LoggerType.STANDARD,
    console_level=LogLevel.INFO,
    file_level=LogLevel.DEBUG,
    log_file="logs/api_tests.log"
)

# Add context
logger.add_context(test_suite="user_management", endpoint="/api/v1/users")

# Log with context
logger.info("Starting API test execution")
logger.debug("Request headers prepared")
logger.warning("Rate limit approaching")
logger.error("API call failed with 500 status")
```

**Logging Demo:**

```bash
python src/logger_demo.py
```

### 8. Streamlit GUI Application

Launch the interactive web interface:

```bash
streamlit run src/api_test_gui.py
```

**Features:**

- **API Explorer**: Browse and analyze OpenAPI specifications
- **Test Builder**: Create and configure test cases
- **Test Execution**: Run tests and view real-time results
- **Collection Management**: Organize and manage test collections
- **Reporting Dashboard**: View detailed test reports and metrics

### 9. Multi-Agent Architecture

Coordinate complex testing workflows:

```python
from agents.rest_api_agent import RestApiAgent
from agents.spec_loader.agent import SpecLoaderAgent

# Initialize agents
spec_agent = SpecLoaderAgent()
api_agent = RestApiAgent()

# Load specification
spec_result = await spec_agent.load_specification("data/toolshop/openapi.json")

# Coordinate API testing
test_result = await api_agent.execute_test_suite(
    specification=spec_result.specification,
    test_configuration=test_config
)
```

### 10. Advanced Test Scenarios

Execute complex testing scenarios:

```python
from core.services.test_execution_service import TestExecutionService
from schemas.test_collection import TestCollection

# Initialize service
test_service = TestExecutionService()

# Load test collection
collection = TestCollection.load_from_file("collections/user_management.json")

# Execute with advanced options
execution_result = await test_service.execute_collection(
    collection=collection,
    parallel_execution=True,
    max_workers=5,
    retry_failed_tests=True,
    generate_report=True
)

print(f"Execution Summary:")
print(f"- Total Tests: {execution_result.total_tests}")
print(f"- Passed: {execution_result.passed_tests}")
print(f"- Failed: {execution_result.failed_tests}")
print(f"- Execution Time: {execution_result.execution_time}s")
```

## 🎯 Demo Scripts

The framework includes comprehensive demonstration scripts:

### API Testing Demos

```bash
# OpenAPI parser demonstration
python src/openapi_parser_tool.py

# API caller with authentication
python src/rest_api_caller_tool.py

# Constraint mining with AI
python src/constraint_miner_tool.py

# Test case generation
python src/test_case_generator_tool.py

# Complete test runner workflow
python src/api_test_runner.py
```

### Infrastructure Demos

```bash
# Caching system capabilities
python src/cache_demo.py

# Logging system features
python src/logger_demo.py
```

## 🔧 Configuration

### Application Settings

```python
# config/settings.py
class Settings:
    # API Configuration
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3

    # Cache Configuration
    CACHE_TYPE = "memory"
    CACHE_TTL = 300

    # Logging Configuration
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/app.log"

    # AI Configuration
    OPENAI_API_KEY = "your-api-key"
    ENABLE_LLM_FEATURES = True
```

### Environment Variables

```bash
# .env file
OPENAI_API_KEY=your-openai-api-key
GOOGLE_AI_API_KEY=your-google-ai-key
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG
CACHE_TYPE=redis
```

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_tools.py
pytest tests/test_caching.py
pytest tests/test_logging.py

# Run with coverage
pytest --cov=src tests/
```

## 📊 Performance Considerations

### Caching Strategy

- **Memory Cache**: Ultra-fast for frequently accessed data
- **File Cache**: Persistent storage for large datasets
- **Redis Cache**: Distributed caching for multi-instance deployments

### Asynchronous Processing

- Non-blocking API calls with `asyncio`
- Concurrent test execution with worker pools
- Streaming responses for large datasets

### Resource Management

- Automatic cleanup of temporary files
- Memory usage monitoring and optimization
- Connection pooling for HTTP requests

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install

# Run linting
flake8 src/
black src/
mypy src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with modern Python best practices
- Inspired by enterprise testing frameworks
- Powered by OpenAI and Google AI technologies
- Streamlit for beautiful web interfaces

## 📞 Support

For questions, issues, or contributions:

- 📧 Email: support@api-testing-framework.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/restful-api-testing-framework/issues)
- 📖 Documentation: [Wiki](https://github.com/your-username/restful-api-testing-framework/wiki)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-username/restful-api-testing-framework/discussions)

---

**Happy API Testing! 🚀**
