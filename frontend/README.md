# RESTful API Testing Framework - Frontend

A modern, service-centric web interface for the RESTful API Testing Framework backend, featuring interactive workflows, real-time async operations, and comprehensive API testing capabilities.

## 🌟 Key Features

### 🎯 Service-Centric Design

- **Focused Workflow**: Select a service once and manage all related resources
- **Tabbed Interface**: Organized tabs for Overview, Endpoints, Test Cases, Test Data, Runs, and Settings
- **Interactive Cards**: Click on service cards to enter detailed management mode
- **Breadcrumb Navigation**: Clear service context with easy navigation back to dashboard

### 🚀 Interactive Components

- **Expandable Test Cases**: Click to expand test case details inline
- **CSV File Preview**: Toggle preview of test data files without full page reload
- **Real-time Updates**: Live progress tracking for async operations
- **Bulk Operations**: Select multiple test cases for batch operations
- **Quick Actions**: One-click generation and testing from overview

### 🎛️ Enhanced Dashboard

- Service grid with visual cards showing key metrics
- Quick access to service management
- Real-time system status
- Statistics overview with drill-down capabilities

### 🔧 Advanced Service Management

- **Service Detail View**: Comprehensive service management in one place
- **Quick Test Runner**: Instant test execution with progress tracking
- **Batch Operations**: Generate all test cases/data at once
- **Service Health**: Monitor service status and data completeness
- **Export/Import**: Service configuration and data management

### 🧪 Interactive Test Cases

- **Inline Expansion**: View test case details without modal dialogs
- **Direct Execution**: Run individual test cases from the list
- **Bulk Selection**: Select and run multiple test cases together
- **Real-time Results**: See test execution progress and results instantly

### 📊 Advanced Test Data

- **File Previews**: Expandable CSV previews with column information
- **Inline Editing**: Edit test data files without leaving the page
- **Validation Feedback**: Real-time validation with detailed error reporting
- **Column Analysis**: View data structure and statistics

### ▶️ Async Test Execution

- **Progress Tracking**: Real-time progress bars for long-running operations
- **Operation Management**: Track multiple concurrent operations
- **Auto-refresh**: Automatic updates for test run status
- **Notification System**: Toast notifications for operation completion
- Download execution logs
- Export test reports

## Technology Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **UI Framework**: Bootstrap 5.3
- **Icons**: Font Awesome 6.4
- **API Communication**: Fetch API
- **Backend**: FastAPI (Python)

## Project Structure

```
frontend/
├── index.html              # Main application page
├── css/
│   └── style.css           # Custom styles and themes
├── js/
│   ├── app.js              # Main application logic
│   ├── services.js         # Service management
│   ├── testCases.js        # Test case operations
│   ├── testData.js         # Test data management
│   └── testRuns.js         # Test execution and results
└── README.md               # This file
```

## Getting Started

### Prerequisites

1. **Backend Server**: Ensure the FastAPI backend is running on `http://localhost:8000`
2. **Modern Browser**: Chrome, Firefox, Safari, or Edge (ES6+ support required)

### Quick Start

1. **Clone or download** the frontend files to your local machine

2. **Serve the files** using any static file server:

   ```bash
   # Using Python's built-in server
   cd frontend
   python -m http.server 8080

   # Using Node.js serve
   npx serve .

   # Using PHP's built-in server
   php -S localhost:8080
   ```

3. **Open your browser** and navigate to `http://localhost:8080`

4. **Verify connection** - The status indicator should show "Connected" if the backend is running

### Configuration

The frontend is configured to connect to the backend at `http://localhost:8000`. To change this:

1. Open `js/app.js`
2. Modify the `API_BASE_URL` constant:
   ```javascript
   const API_BASE_URL = "http://your-backend-url:port/api/v1";
   ```

## Usage Guide

### 1. Service Management

**Creating a Service:**

1. Navigate to the Services tab
2. Click "Create Service"
3. Enter service name
4. Choose specification source:
   - **Upload**: Select OpenAPI JSON/YAML file
   - **Existing**: Provide path to existing file
   - **URL**: Enter URL to specification
5. Configure ODG rebuild option
6. Click "Create Service"

**Managing Services:**

- **View Details**: Click the eye icon to see service information
- **View Endpoints**: Click the list icon to see API endpoints
- **Edit Spec**: Click the edit icon to modify OpenAPI specification
- **Delete**: Click the trash icon to remove service and all data

### 2. Test Case Generation

**Generating Test Cases:**

1. Select a service from the dropdown
2. Click "Generate Test Cases"
3. Select specific endpoints or all
4. Choose whether to clear existing test cases
5. Click "Generate"

**Managing Test Cases:**

- **View**: Click eye icon to see test case details
- **Edit**: Modify parameters, body, and expected status
- **Dry Run**: Test individual cases without full execution
- **Delete**: Remove unwanted test cases

### 3. Test Data Management

**Generating Test Data:**

1. Select a service from the dropdown
2. Click "Generate Test Data"
3. Choose generation mode (all or selected endpoints)
4. Configure regeneration options
5. Click "Generate"

**Managing Test Data:**

- **View**: See CSV data with preview
- **Edit**: Modify data inline with validation
- **Validate**: Check data structure and format
- **Download**: Export CSV files
- **Delete**: Remove data files

### 4. Test Execution

**Running Tests:**

1. Select a service from the dropdown
2. Click "Start Test Run"
3. Configure:
   - Base URL of the API to test
   - Authentication token (optional)
   - Endpoint filter (optional)
4. Click "Start Run"

**Monitoring Runs:**

- Real-time status updates
- Progress indicators
- Success/failure rates
- Execution logs

**Viewing Results:**

- Detailed test results table
- Response data inspection
- Artifact downloads
- Export capabilities

## API Integration

The frontend communicates with the backend through RESTful APIs:

### Service Management

- `GET /api/v1/services` - List services
- `POST /api/v1/services` - Create service
- `GET /api/v1/services/{id}` - Get service details
- `PUT /api/v1/services/{id}/spec` - Update specification
- `DELETE /api/v1/services/{id}` - Delete service

### Test Cases

- `POST /api/v1/services/{id}/generate/test-cases` - Generate test cases
- `GET /api/v1/services/{id}/test-cases` - List test cases
- `GET /api/v1/services/{id}/test-cases/{case_id}` - Get test case
- `PUT /api/v1/services/{id}/test-cases/{case_id}` - Update test case
- `DELETE /api/v1/services/{id}/test-cases/{case_id}` - Delete test case

### Test Data

- `POST /api/v1/services/{id}/generate/test-data` - Generate test data
- `GET /api/v1/services/{id}/test-data` - List test data files
- `GET /api/v1/services/{id}/test-data/{filename}` - Get test data content
- `POST /api/v1/services/{id}/test-data/validate` - Validate test data
- `DELETE /api/v1/services/{id}/test-data/{filename}` - Delete test data

### Test Runs

- `POST /api/v1/services/{id}/runs` - Create test run
- `GET /api/v1/services/{id}/runs` - List runs
- `GET /api/v1/services/{id}/runs/{run_id}` - Get run details
- `GET /api/v1/services/{id}/runs/{run_id}/results` - Get run results
- `DELETE /api/v1/services/{id}/runs/{run_id}` - Delete run

## Features in Detail

### Real-time Updates

- Automatic polling for test run status
- Live progress indicators
- Background health checks
- Periodic data refresh

### Error Handling

- Comprehensive error messages
- Graceful degradation
- Connection status monitoring
- User-friendly notifications

### Responsive Design

- Mobile-friendly interface
- Adaptive layouts
- Touch-friendly controls
- Accessibility features

### Data Visualization

- Progress bars for success rates
- Status indicators with colors
- Interactive tables
- Syntax highlighting for JSON/CSV

## Browser Compatibility

- **Chrome**: 60+
- **Firefox**: 55+
- **Safari**: 11+
- **Edge**: 79+

## Development

### Adding New Features

1. **Create new JS module** in the `js/` directory
2. **Add HTML structure** to `index.html`
3. **Style with CSS** in `css/style.css`
4. **Export functions** for global access
5. **Update navigation** in `app.js`

### Customization

**Theming:**

- Modify CSS variables in `style.css`
- Update Bootstrap theme colors
- Add custom component styles

**API Endpoints:**

- Update `API_BASE_URL` in `app.js`
- Modify API request functions
- Add new endpoint integrations

**UI Components:**

- Extend Bootstrap components
- Add custom modals and forms
- Implement new visualization types

## Troubleshooting

### Common Issues

**Connection Error:**

- Verify backend server is running
- Check `API_BASE_URL` configuration
- Ensure CORS is enabled on backend

**File Upload Issues:**

- Verify file size limits
- Check file format (JSON/YAML)
- Ensure proper file permissions

**Performance Issues:**

- Reduce polling frequency
- Implement pagination for large datasets
- Use browser caching

### Debug Mode

Enable debug logging by adding to browser console:

```javascript
localStorage.setItem("debug", "true");
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Follow code style guidelines

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

- Create GitHub issues
- Check documentation
- Review API specifications
- Contact development team
