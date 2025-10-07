# RESTful API Testing Framework Server

Unified API server for the RESTful API Testing Framework with KAT and SequenceRunner integration.

## Quick Start

1. **Install dependencies:**

   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. **Start server:**

   ```bash
   python start_server.py
   ```

3. **Access API:**
   - Server runs on: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/api/v1/healthz

## Unified Database Structure

All components (Server, KAT, SequenceRunner) now share a unified database structure:

```
/database/
├── server_metadata.json
├── {service_name}/
│   ├── specs/
│   │   └── openapi.json        # OpenAPI specification
│   ├── test_cases/             # Generated test cases
│   ├── test_data/              # Test data CSV files
│   ├── results/                # Test execution results
│   ├── logs/                   # Execution logs
│   └── ODG/                    # Operation Dependency Graph
```

## Key Features

- **Unified Directory Structure**: All components use the same database layout
- **Backward Compatibility**: Falls back to legacy structure if needed
- **Auto Configuration**: Automatically creates required directories
- **KAT Integration**: Direct integration with test case and data generation
- **SequenceRunner Integration**: Unified test execution

## API Endpoints

### Services Management

- `POST /api/v1/services` - Create new service
- `GET /api/v1/services` - List all services
- `GET /api/v1/services/{service_id}` - Get service details
- `PUT /api/v1/services/{service_id}/spec` - Update service spec
- `DELETE /api/v1/services/{service_id}` - Delete service

### Test Cases

- `POST /api/v1/services/{service_id}/generate/test-cases` - Generate test cases
- `GET /api/v1/services/{service_id}/test-cases` - List test cases
- `GET /api/v1/services/{service_id}/test-cases/{test_case_id}` - Get test case
- `PUT /api/v1/services/{service_id}/test-cases/{test_case_id}` - Update test case
- `DELETE /api/v1/services/{service_id}/test-cases/{test_case_id}` - Delete test case

### Test Data

- `POST /api/v1/services/{service_id}/generate/test-data` - Generate test data
- `GET /api/v1/services/{service_id}/test-data` - List test data files
- `POST /api/v1/services/{service_id}/test-data/validate` - Validate test data

### Test Runs

- `POST /api/v1/services/{service_id}/runs` - Create and start test run
- `GET /api/v1/services/{service_id}/runs` - List runs
- `GET /api/v1/services/{service_id}/runs/{run_id}` - Get run details
- `GET /api/v1/services/{service_id}/runs/{run_id}/results` - Get run results

### System

- `GET /api/v1/healthz` - Health check
- `GET /api/v1/version` - Version information
- `GET /api/v1/config` - Configuration details
