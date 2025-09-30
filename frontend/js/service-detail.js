/**
 * Service Detail Management
 * Handles the service-centric UI with tabbed interface and interactive components
 */

// Current service state
let currentServiceData = null;
let currentActiveTab = "overview";
let asyncEventManager = new AsyncEventManager();

/**
 * Show service detail view for a specific service
 */
async function showServiceDetail(serviceId) {
  try {
    showLoading("dashboard-view");

    // Fetch service data
    const response = await apiRequest(`/services/${serviceId}`);
    currentServiceData = response.data;

    // Update navigation breadcrumb
    updateServiceBreadcrumb(currentServiceData.name);

    // Show service detail view
    showView("service-detail");

    // Render service header
    renderServiceHeader(currentServiceData);

    // Load overview tab by default
    await loadServiceOverview(serviceId);

    // Setup tab event listeners
    setupServiceTabListeners(serviceId);
  } catch (error) {
    showNotification(
      "Failed to load service details: " + error.message,
      "danger"
    );
    showDashboard();
  }
}

/**
 * Update navigation breadcrumb
 */
function updateServiceBreadcrumb(serviceName) {
  document.getElementById("current-service-name").textContent = serviceName;
  document.getElementById("service-breadcrumb").style.display = "block";
}

/**
 * Hide service breadcrumb
 */
function hideServiceBreadcrumb() {
  document.getElementById("service-breadcrumb").style.display = "none";
}

/**
 * Render service header with key information and actions
 */
function renderServiceHeader(service) {
  const headerContent = `
    <div class="card service-header-card">
      <div class="card-body">
        <div class="row align-items-center">
          <div class="col-md-8">
            <div class="d-flex align-items-center">
              <div class="service-icon me-3">
                <i class="fas fa-server fa-2x text-primary"></i>
              </div>
              <div>
                <h3 class="mb-1">${escapeHtml(service.name)}</h3>
                <div class="service-meta">
                  <span class="badge ${getStatusBadgeClass(
                    service.status
                  )} me-2">${service.status}</span>
                  <span class="text-muted">
                    <i class="fas fa-calendar me-1"></i>Created ${formatDate(
                      service.created_at
                    )}
                  </span>
                  <span class="text-muted ms-3">
                    <i class="fas fa-clock me-1"></i>Updated ${formatDate(
                      service.updated_at
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div class="col-md-4 text-end">
            <div class="service-stats">
              <div class="stat-item">
                <span class="stat-value">${service.endpoints_count}</span>
                <span class="stat-label">Endpoints</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">${service.test_cases_count}</span>
                <span class="stat-label">Test Cases</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">${service.test_runs_count || 0}</span>
                <span class="stat-label">Test Runs</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="row mt-3">
          <div class="col-12">
            <div class="service-actions">
              <button class="btn btn-outline-primary me-2" onclick="editServiceSpec('${
                service.id
              }')">
                <i class="fas fa-edit me-1"></i>Edit Spec
              </button>
              <button class="btn btn-outline-success me-2" onclick="generateAllForService('${
                service.id
              }')">
                <i class="fas fa-magic me-1"></i>Generate All
              </button>
              <button class="btn btn-outline-info me-2" onclick="runQuickTest('${
                service.id
              }')">
                <i class="fas fa-play me-1"></i>Quick Test
              </button>
              <div class="btn-group me-2" role="group">
                <button type="button" class="btn btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
                  <i class="fas fa-cog me-1"></i>Actions
                </button>
                <ul class="dropdown-menu">
                  <li><a class="dropdown-item" href="#" onclick="exportService('${
                    service.id
                  }')">
                    <i class="fas fa-download me-2"></i>Export Service
                  </a></li>
                  <li><a class="dropdown-item" href="#" onclick="cloneService('${
                    service.id
                  }')">
                    <i class="fas fa-copy me-2"></i>Clone Service
                  </a></li>
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item text-danger" href="#" onclick="deleteService('${
                    service.id
                  }', '${escapeHtml(service.name)}')">
                    <i class="fas fa-trash me-2"></i>Delete Service
                  </a></li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById("service-header").innerHTML = headerContent;
}

/**
 * Setup tab event listeners
 */
function setupServiceTabListeners(serviceId) {
  const tabs = document.querySelectorAll(
    '#service-tabs button[data-bs-toggle="tab"]'
  );

  tabs.forEach((tab) => {
    tab.addEventListener("shown.bs.tab", async function (event) {
      const tabId = event.target
        .getAttribute("data-bs-target")
        .replace("#", "");
      currentActiveTab = tabId;

      switch (tabId) {
        case "overview":
          await loadServiceOverview(serviceId);
          break;
        case "endpoints":
          await loadServiceEndpoints(serviceId);
          break;
        case "test-cases":
          await loadServiceTestCases(serviceId);
          break;
        case "test-data":
          await loadServiceTestData(serviceId);
          break;
        case "test-runs":
          await loadServiceTestRuns(serviceId);
          break;
        case "settings":
          await loadServiceSettings(serviceId);
          break;
      }
    });
  });
}

/**
 * Load service overview tab
 */
async function loadServiceOverview(serviceId) {
  const container = document.getElementById("service-overview-content");
  showLoading("service-overview-content");

  try {
    // Get recent data for overview
    const [testCasesResponse, testDataResponse, testRunsResponse] =
      await Promise.all([
        apiRequest(`/services/${serviceId}/test-cases`).catch(() => ({
          data: [],
        })),
        apiRequest(`/services/${serviceId}/test-data`).catch(() => ({
          data: [],
        })),
        apiRequest(`/services/${serviceId}/runs`).catch(() => ({ data: [] })),
      ]);

    const testCases = testCasesResponse.data || [];
    const testDataFiles = testDataResponse.data || [];
    const testRuns = testRunsResponse.data || [];

    // Calculate success rate
    const successRate =
      testRuns.length > 0
        ? Math.round(
            testRuns.reduce(
              (sum, run) => sum + (run.results.success_rate || 0),
              0
            ) / testRuns.length
          )
        : 0;

    const overviewContent = `
      <div class="row">
        <!-- Quick Stats -->
        <div class="col-md-12 mb-4">
          <div class="row">
            <div class="col-md-3">
              <div class="card text-center overview-stat-card">
                <div class="card-body">
                  <i class="fas fa-list-alt fa-2x text-primary mb-2"></i>
                  <h4>${currentServiceData.endpoints_count}</h4>
                  <p class="text-muted">API Endpoints</p>
                  <button class="btn btn-sm btn-outline-primary" onclick="switchToTab('endpoints')">
                    View Details
                  </button>
                </div>
              </div>
            </div>
            <div class="col-md-3">
              <div class="card text-center overview-stat-card">
                <div class="card-body">
                  <i class="fas fa-file-code fa-2x text-success mb-2"></i>
                  <h4>${testCases.length}</h4>
                  <p class="text-muted">Test Cases</p>
                  <button class="btn btn-sm btn-outline-success" onclick="switchToTab('test-cases')">
                    View Details
                  </button>
                </div>
              </div>
            </div>
            <div class="col-md-3">
              <div class="card text-center overview-stat-card">
                <div class="card-body">
                  <i class="fas fa-database fa-2x text-info mb-2"></i>
                  <h4>${testDataFiles.length}</h4>
                  <p class="text-muted">Test Data Files</p>
                  <button class="btn btn-sm btn-outline-info" onclick="switchToTab('test-data')">
                    View Details
                  </button>
                </div>
              </div>
            </div>
            <div class="col-md-3">
              <div class="card text-center overview-stat-card">
                <div class="card-body">
                  <i class="fas fa-chart-line fa-2x text-warning mb-2"></i>
                  <h4>${successRate}%</h4>
                  <p class="text-muted">Success Rate</p>
                  <button class="btn btn-sm btn-outline-warning" onclick="switchToTab('test-runs')">
                    View Details
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Recent Activity -->
        <div class="col-md-8">
          <div class="card">
            <div class="card-header">
              <h5><i class="fas fa-history me-2"></i>Recent Test Runs</h5>
            </div>
            <div class="card-body">
              ${
                testRuns.length > 0
                  ? renderRecentRuns(testRuns.slice(0, 5), serviceId)
                  : '<div class="text-muted text-center py-3">No test runs yet</div>'
              }
            </div>
          </div>
        </div>
        
        <!-- Quick Actions -->
        <div class="col-md-4">
          <div class="card">
            <div class="card-header">
              <h5><i class="fas fa-rocket me-2"></i>Quick Actions</h5>
            </div>
            <div class="card-body">
              <div class="d-grid gap-2">
                <button class="btn btn-primary" onclick="generateTestCasesQuick('${serviceId}')">
                  <i class="fas fa-magic me-2"></i>Generate Test Cases
                </button>
                <button class="btn btn-success" onclick="generateTestDataQuick('${serviceId}')">
                  <i class="fas fa-database me-2"></i>Generate Test Data
                </button>
                <button class="btn btn-warning" onclick="generateCompleteTestSuite('${serviceId}')">
                  <i class="fas fa-rocket me-2"></i>Generate Complete Suite
                </button>
                <button class="btn btn-info" onclick="runQuickTest('${serviceId}')">
                  <i class="fas fa-play me-2"></i>Run Quick Test
                </button>
                <button class="btn btn-outline-secondary" onclick="validateService('${serviceId}')">
                  <i class="fas fa-check-circle me-2"></i>Validate Setup
                </button>
              </div>
            </div>
          </div>
          
          <!-- Service Health -->
          <div class="card mt-3">
            <div class="card-header">
              <h5><i class="fas fa-heartbeat me-2"></i>Service Health</h5>
            </div>
            <div class="card-body">
              <div class="service-health-indicators">
                <div class="health-item">
                  <div class="d-flex justify-content-between">
                    <span>Spec Validity</span>
                    <span class="badge bg-success">Valid</span>
                  </div>
                </div>
                <div class="health-item">
                  <div class="d-flex justify-content-between">
                    <span>Test Coverage</span>
                    <span class="badge bg-${
                      testCases.length > 0 ? "success" : "warning"
                    }">${testCases.length > 0 ? "Good" : "Low"}</span>
                  </div>
                </div>
                <div class="health-item">
                  <div class="d-flex justify-content-between">
                    <span>Data Readiness</span>
                    <span class="badge bg-${
                      testDataFiles.length > 0 ? "success" : "warning"
                    }">${
      testDataFiles.length > 0 ? "Ready" : "Needs Data"
    }</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    container.innerHTML = overviewContent;
  } catch (error) {
    showError("service-overview-content", "Failed to load service overview");
  }
}

/**
 * Render recent test runs for overview
 */
function renderRecentRuns(runs, serviceId) {
  return runs
    .map(
      (run) => `
    <div class="recent-run-item mb-2 p-2 border rounded cursor-pointer" onclick="viewTestRun('${serviceId}', '${
        run.id
      }')">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <span class="fw-bold">${run.id.substring(0, 8)}</span>
          <span class="status-indicator status-${run.status} ms-2">${
        run.status
      }</span>
        </div>
        <div class="text-end">
          <small class="text-muted">${formatDate(run.created_at)}</small>
          <div class="progress mt-1" style="width: 60px; height: 4px;">
            <div class="progress-bar bg-${
              run.results.success_rate >= 90
                ? "success"
                : run.results.success_rate >= 70
                ? "warning"
                : "danger"
            }" 
                 style="width: ${run.results.success_rate}%"></div>
          </div>
        </div>
      </div>
    </div>
  `
    )
    .join("");
}

/**
 * Switch to a specific tab
 */
function switchToTab(tabName) {
  const tab = document.querySelector(`#${tabName}-tab`);
  if (tab) {
    tab.click();
  }
}

/**
 * Load service endpoints with interactive features
 */
async function loadServiceEndpoints(serviceId) {
  const container = document.getElementById("service-endpoints-content");
  showLoading("service-endpoints-content");

  try {
    const response = await apiRequest(`/services/${serviceId}/endpoints`);
    const endpoints = response.data || [];

    const endpointsContent = `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5>API Endpoints (${endpoints.length})</h5>
        <div class="endpoint-filters">
          <select class="form-select form-select-sm d-inline-block w-auto me-2" id="method-filter" onchange="filterEndpoints()">
            <option value="">All Methods</option>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="PATCH">PATCH</option>
            <option value="DELETE">DELETE</option>
          </select>
          <input type="text" class="form-control form-control-sm d-inline-block w-auto" 
                 placeholder="Search endpoints..." id="endpoint-search" onkeyup="filterEndpoints()">
        </div>
      </div>
      
      <div class="endpoints-grid" id="endpoints-grid">
        ${endpoints
          .map((endpoint) => renderEndpointCard(endpoint, serviceId))
          .join("")}
      </div>
    `;

    container.innerHTML = endpointsContent;
  } catch (error) {
    showError("service-endpoints-content", "Failed to load endpoints");
  }
}

/**
 * Render endpoint card with actions
 */
function renderEndpointCard(endpoint, serviceId) {
  return `
    <div class="card endpoint-card mb-3" data-method="${
      endpoint.method
    }" data-path="${endpoint.path}">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div class="endpoint-info">
            <div class="endpoint-signature">
              <span class="endpoint-method ${getMethodBadgeClass(
                endpoint.method
              )}">${endpoint.method}</span>
              <code class="endpoint-path ms-2">${endpoint.path}</code>
            </div>
            <h6 class="mt-2 mb-1">${endpoint.operation_id}</h6>
            ${
              endpoint.summary
                ? `<p class="text-muted small mb-2">${escapeHtml(
                    endpoint.summary
                  )}</p>`
                : ""
            }
            ${
              endpoint.description
                ? `<p class="text-muted small">${escapeHtml(
                    endpoint.description
                  ).substring(0, 100)}...</p>`
                : ""
            }
          </div>
          <div class="endpoint-actions">
            <div class="btn-group" role="group">
              <button class="btn btn-sm btn-outline-primary" onclick="generateTestCaseForEndpoint('${serviceId}', '${endpoint.method.toLowerCase()}-${
    endpoint.path
  }')" title="Generate Test Case">
                <i class="fas fa-plus"></i>
              </button>
              <button class="btn btn-sm btn-outline-success" onclick="generateTestDataForEndpoint('${serviceId}', '${endpoint.method.toLowerCase()}-${
    endpoint.path
  }')" title="Generate Test Data">
                <i class="fas fa-database"></i>
              </button>
              <button class="btn btn-sm btn-outline-info" onclick="testEndpointDirectly('${serviceId}', '${endpoint.method.toLowerCase()}-${
    endpoint.path
  }')" title="Test Directly">
                <i class="fas fa-play"></i>
              </button>
            </div>
          </div>
        </div>
        
        <!-- Endpoint Details (collapsible) -->
        <div class="endpoint-details mt-2">
          <small class="text-muted">
            ${
              endpoint.parameters
                ? `<span class="me-3"><i class="fas fa-list me-1"></i>${
                    Object.keys(endpoint.parameters).length
                  } parameters</span>`
                : ""
            }
            ${
              endpoint.request_body
                ? `<span class="me-3"><i class="fas fa-file-code me-1"></i>Has body</span>`
                : ""
            }
            ${
              endpoint.responses
                ? `<span class="me-3"><i class="fas fa-reply me-1"></i>${
                    Object.keys(endpoint.responses).length
                  } responses</span>`
                : ""
            }
          </small>
        </div>
      </div>
    </div>
  `;
}

/**
 * Filter endpoints based on method and search term
 */
function filterEndpoints() {
  const methodFilter = document.getElementById("method-filter").value;
  const searchTerm = document
    .getElementById("endpoint-search")
    .value.toLowerCase();
  const endpointCards = document.querySelectorAll(".endpoint-card");

  endpointCards.forEach((card) => {
    const method = card.getAttribute("data-method");
    const path = card.getAttribute("data-path").toLowerCase();

    const methodMatch = !methodFilter || method === methodFilter;
    const searchMatch = !searchTerm || path.includes(searchTerm);

    card.style.display = methodMatch && searchMatch ? "block" : "none";
  });
}

/**
 * Load service test cases with interactive table
 */
async function loadServiceTestCases(serviceId) {
  const container = document.getElementById("service-test-cases-content");
  showLoading("service-test-cases-content");

  try {
    const response = await apiRequest(`/services/${serviceId}/test-cases`);
    const testCases = response.data || [];

    const testCasesContent = `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5>Test Cases (${testCases.length})</h5>
        <div class="test-case-actions">
          <button class="btn btn-primary btn-sm" onclick="showGenerateTestCasesModal('${serviceId}')">
            <i class="fas fa-magic me-1"></i>Generate Test Cases
          </button>
          <button class="btn btn-outline-success btn-sm ms-2" onclick="runAllTestCases('${serviceId}')">
            <i class="fas fa-play me-1"></i>Run All
          </button>
        </div>
      </div>
      
      ${
        testCases.length > 0
          ? renderInteractiveTestCasesTable(testCases, serviceId)
          : renderEmptyTestCases(serviceId)
      }
    `;

    container.innerHTML = testCasesContent;
  } catch (error) {
    showError("service-test-cases-content", "Failed to load test cases");
  }
}

/**
 * Render interactive test cases table
 */
function renderInteractiveTestCasesTable(testCases, serviceId) {
  return `
    <div class="table-responsive">
      <table class="table table-hover test-cases-table">
        <thead>
          <tr>
            <th width="5%">
              <input type="checkbox" class="form-check-input" onchange="toggleAllTestCases(this)">
            </th>
            <th>Test Case</th>
            <th>Endpoint</th>
            <th>Method</th>
            <th>Expected Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${testCases
            .map(
              (testCase) => `
            <tr class="test-case-row" data-test-case-id="${testCase.id}">
              <td>
                <input type="checkbox" class="form-check-input test-case-checkbox" value="${
                  testCase.id
                }">
              </td>
              <td>
                <div class="test-case-info cursor-pointer" onclick="expandTestCase('${serviceId}', '${
                testCase.id
              }')">
                  <strong>${testCase.id}</strong>
                  <br>
                  <small class="text-muted">${escapeHtml(
                    testCase.description || "No description"
                  )}</small>
                </div>
              </td>
              <td><code>${escapeHtml(testCase.endpoint || "")}</code></td>
              <td><span class="endpoint-method ${getMethodBadgeClass(
                testCase.method || ""
              )}">${testCase.method || ""}</span></td>
              <td>${
                testCase.expected_status
                  ? `<span class="badge bg-info">${testCase.expected_status}</span>`
                  : "-"
              }</td>
              <td>
                <div class="btn-group" role="group">
                  <button class="btn btn-sm btn-outline-success" onclick="runSingleTestCaseInline('${serviceId}', '${
                testCase.id
              }')" title="Run Test">
                    <i class="fas fa-play"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-primary" onclick="editTestCase('${serviceId}', '${
                testCase.id
              }')" title="Edit">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" onclick="deleteTestCase('${serviceId}', '${
                testCase.id
              }')" title="Delete">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
            <tr class="test-case-details-row" id="details-${
              testCase.id
            }" style="display: none;">
              <td colspan="6">
                <div class="test-case-details-content p-3 bg-light">
                  <!-- Will be populated when expanded -->
                </div>
              </td>
            </tr>
          `
            )
            .join("")}
        </tbody>
      </table>
    </div>
    
    <div class="test-cases-bulk-actions mt-3" id="bulk-actions" style="display: none;">
      <div class="d-flex gap-2">
        <button class="btn btn-outline-success btn-sm" onclick="runSelectedTestCases('${serviceId}')">
          <i class="fas fa-play me-1"></i>Run Selected
        </button>
        <button class="btn btn-outline-danger btn-sm" onclick="deleteSelectedTestCases('${serviceId}')">
          <i class="fas fa-trash me-1"></i>Delete Selected
        </button>
      </div>
    </div>
  `;
}

/**
 * Render empty test cases state
 */
function renderEmptyTestCases(serviceId) {
  return `
    <div class="text-center py-5">
      <i class="fas fa-file-code fa-3x text-muted mb-3"></i>
      <h5 class="text-muted">No Test Cases Found</h5>
      <p class="text-muted">Generate test cases from your API endpoints to start testing.</p>
      <button class="btn btn-primary" onclick="showGenerateTestCasesModal('${serviceId}')">
        <i class="fas fa-magic me-2"></i>Generate Test Cases
      </button>
    </div>
  `;
}

/**
 * Load service test data with interactive file viewer
 */
async function loadServiceTestData(serviceId) {
  const container = document.getElementById("service-test-data-content");
  showLoading("service-test-data-content");

  try {
    const response = await apiRequest(`/services/${serviceId}/test-data`);
    const testDataFiles = response.data || [];

    const testDataContent = `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5>Test Data Files (${testDataFiles.length})</h5>
        <div class="test-data-actions">
          <button class="btn btn-primary btn-sm" onclick="showGenerateTestDataModal('${serviceId}')">
            <i class="fas fa-magic me-1"></i>Generate Test Data
          </button>
          <button class="btn btn-outline-info btn-sm ms-2" onclick="validateTestData('${serviceId}')">
            <i class="fas fa-check-circle me-1"></i>Validate All
          </button>
        </div>
      </div>
      
      ${
        testDataFiles.length > 0
          ? renderInteractiveTestDataGrid(testDataFiles, serviceId)
          : renderEmptyTestData(serviceId)
      }
    `;

    container.innerHTML = testDataContent;
  } catch (error) {
    showError("service-test-data-content", "Failed to load test data");
  }
}

/**
 * Render interactive test data grid with file preview
 */
function renderInteractiveTestDataGrid(testDataFiles, serviceId) {
  return `
    <div class="test-data-grid">
      ${testDataFiles
        .map(
          (file) => `
        <div class="card test-data-file-card mb-3">
          <div class="card-header">
            <div class="d-flex justify-content-between align-items-center">
              <h6 class="mb-0">
                <i class="fas fa-file-csv me-2 text-success"></i>
                ${escapeHtml(file.filename)}
              </h6>
              <div class="file-actions">
                <button class="btn btn-sm btn-outline-primary" onclick="viewCsvFileInline('${serviceId}', '${escapeHtml(
            file.filename
          )}')" title="View Data">
                  <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="downloadTestDataFile('${serviceId}', '${escapeHtml(
            file.filename
          )}')" title="Download">
                  <i class="fas fa-download"></i>
                </button>
                <button class="btn btn-sm btn-outline-warning" onclick="editTestDataFileInline('${serviceId}', '${escapeHtml(
            file.filename
          )}')" title="Edit">
                  <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteTestDataFile('${serviceId}', '${escapeHtml(
            file.filename
          )}')" title="Delete">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-8">
                <div class="file-info">
                  <small class="text-muted">
                    <span class="me-3"><i class="fas fa-table me-1"></i>${
                      file.row_count || 0
                    } rows</span>
                    <span class="me-3"><i class="fas fa-columns me-1"></i>${
                      file.headers ? file.headers.length : 0
                    } columns</span>
                    <span class="me-3"><i class="fas fa-file-alt me-1"></i>${formatFileSize(
                      file.size
                    )}</span>
                    <span><i class="fas fa-clock me-1"></i>${formatDate(
                      new Date(file.modified_at * 1000)
                    )}</span>
                  </small>
                </div>
                ${
                  file.headers && file.headers.length > 0
                    ? `
                  <div class="mt-2">
                    <strong class="small">Columns:</strong>
                    <div class="mt-1">
                      ${file.headers
                        .slice(0, 8)
                        .map(
                          (header) =>
                            `<span class="badge bg-light text-dark me-1 mb-1">${escapeHtml(
                              header
                            )}</span>`
                        )
                        .join("")}
                      ${
                        file.headers.length > 8
                          ? `<span class="text-muted small">+${
                              file.headers.length - 8
                            } more</span>`
                          : ""
                      }
                    </div>
                  </div>
                `
                    : ""
                }
              </div>
              <div class="col-md-4 text-end">
                <button class="btn btn-primary btn-sm" onclick="toggleFilePreview('${serviceId}', '${escapeHtml(
            file.filename
          )}', this)">
                  <i class="fas fa-chevron-down me-1"></i>Show Preview
                </button>
              </div>
            </div>
            
            <!-- File Preview Container -->
            <div class="file-preview mt-3" id="preview-${file.filename.replace(
              /[^a-zA-Z0-9]/g,
              "_"
            )}" style="display: none;">
              <div class="text-center text-muted py-3">
                <i class="fas fa-spinner fa-spin me-2"></i>Loading preview...
              </div>
            </div>
          </div>
        </div>
      `
        )
        .join("")}
    </div>
  `;
}

/**
 * Load service test runs with real-time updates
 */
async function loadServiceTestRuns(serviceId) {
  const container = document.getElementById("service-test-runs-content");
  showLoading("service-test-runs-content");

  try {
    const response = await apiRequest(`/services/${serviceId}/runs`);
    const testRuns = response.data || [];

    const testRunsContent = `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5>Test Runs (${testRuns.length})</h5>
        <div class="test-runs-actions">
          <button class="btn btn-success btn-sm" onclick="showCreateRunModal('${serviceId}')">
            <i class="fas fa-play me-1"></i>Start Test Run
          </button>
          <button class="btn btn-outline-info btn-sm ms-2" onclick="refreshTestRunsData('${serviceId}')">
            <i class="fas fa-sync me-1"></i>Refresh
          </button>
        </div>
      </div>
      
      ${
        testRuns.length > 0
          ? renderInteractiveTestRunsTable(testRuns, serviceId)
          : renderEmptyTestRuns(serviceId)
      }
    `;

    container.innerHTML = testRunsContent;

    // Start real-time sync for active runs
    startTestRunsSync(serviceId, testRuns);
  } catch (error) {
    showError("service-test-runs-content", "Failed to load test runs");
  }
}

/**
 * Load service settings
 */
async function loadServiceSettings(serviceId) {
  const container = document.getElementById("service-settings-content");
  showLoading("service-settings-content");

  try {
    const settingsContent = `
      <div class="row">
        <div class="col-md-8">
          <div class="card">
            <div class="card-header">
              <h5><i class="fas fa-cog me-2"></i>Service Configuration</h5>
            </div>
            <div class="card-body">
              <form id="service-settings-form">
                <div class="mb-3">
                  <label class="form-label">Service Name</label>
                  <input type="text" class="form-control" value="${escapeHtml(
                    currentServiceData.name
                  )}" id="settings-service-name">
                </div>
                
                <div class="mb-3">
                  <label class="form-label">OpenAPI Specification Path</label>
                  <input type="text" class="form-control" value="${escapeHtml(
                    currentServiceData.spec_path
                  )}" readonly>
                  <small class="text-muted">Use the "Edit Spec" button to modify the specification</small>
                </div>
                
                <div class="mb-3">
                  <label class="form-label">Working Directory</label>
                  <input type="text" class="form-control" value="${escapeHtml(
                    currentServiceData.working_dir
                  )}" readonly>
                </div>
                
                <div class="mb-3">
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="auto-generate-enabled" checked>
                    <label class="form-check-label" for="auto-generate-enabled">
                      Auto-generate test cases for new endpoints
                    </label>
                  </div>
                </div>
                
                <div class="mb-3">
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="auto-validate-enabled" checked>
                    <label class="form-check-label" for="auto-validate-enabled">
                      Auto-validate test data on generation
                    </label>
                  </div>
                </div>
                
                <button type="button" class="btn btn-primary" onclick="saveServiceSettings('${serviceId}')">
                  <i class="fas fa-save me-2"></i>Save Settings
                </button>
              </form>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card">
            <div class="card-header">
              <h5><i class="fas fa-tools me-2"></i>Service Actions</h5>
            </div>
            <div class="card-body">
              <div class="d-grid gap-2">
                <button class="btn btn-outline-primary" onclick="regenerateAllTestCases('${serviceId}')">
                  <i class="fas fa-refresh me-2"></i>Regenerate Test Cases
                </button>
                <button class="btn btn-outline-success" onclick="regenerateAllTestData('${serviceId}')">
                  <i class="fas fa-database me-2"></i>Regenerate Test Data
                </button>
                <button class="btn btn-outline-warning" onclick="validateAllTestData('${serviceId}')">
                  <i class="fas fa-check-circle me-2"></i>Validate All Data
                </button>
                <button class="btn btn-outline-info" onclick="exportServiceData('${serviceId}')">
                  <i class="fas fa-download me-2"></i>Export Service Data
                </button>
                <hr>
                <button class="btn btn-outline-danger" onclick="resetServiceData('${serviceId}')">
                  <i class="fas fa-trash me-2"></i>Reset All Data
                </button>
              </div>
            </div>
          </div>
          
          <div class="card mt-3">
            <div class="card-header">
              <h5><i class="fas fa-chart-bar me-2"></i>Service Statistics</h5>
            </div>
            <div class="card-body">
              <div class="service-stats-detail">
                <div class="stat-row">
                  <span>Total Endpoints:</span>
                  <span class="fw-bold">${
                    currentServiceData.endpoints_count
                  }</span>
                </div>
                <div class="stat-row">
                  <span>Test Cases:</span>
                  <span class="fw-bold">${
                    currentServiceData.test_cases_count
                  }</span>
                </div>
                <div class="stat-row">
                  <span>Test Data Files:</span>
                  <span class="fw-bold">${
                    currentServiceData.test_data_count || 0
                  }</span>
                </div>
                <div class="stat-row">
                  <span>Test Runs:</span>
                  <span class="fw-bold">${
                    currentServiceData.test_runs_count || 0
                  }</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    container.innerHTML = settingsContent;
  } catch (error) {
    showError("service-settings-content", "Failed to load service settings");
  }
}

/**
 * Toggle file preview in test data grid
 */
async function toggleFilePreview(serviceId, filename, button) {
  const previewId = `preview-${filename.replace(/[^a-zA-Z0-9]/g, "_")}`;
  const previewContainer = document.getElementById(previewId);
  const icon = button.querySelector("i");

  if (previewContainer.style.display === "none") {
    // Show preview
    previewContainer.style.display = "block";
    icon.className = "fas fa-chevron-up me-1";
    button.innerHTML = '<i class="fas fa-chevron-up me-1"></i>Hide Preview';

    // Load preview data
    try {
      const response = await apiRequest(
        `/services/${serviceId}/test-data/${encodeURIComponent(filename)}`
      );
      const fileData = response.data;

      const previewHtml = `
        <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
          <table class="table table-sm table-striped">
            <thead class="sticky-top bg-light">
              <tr>
                <th width="50">#</th>
                ${fileData.headers
                  .map((header) => `<th>${escapeHtml(header)}</th>`)
                  .join("")}
              </tr>
            </thead>
            <tbody>
              ${fileData.data
                .slice(0, 10)
                .map(
                  (row, index) => `
                <tr>
                  <td>${index + 1}</td>
                  ${fileData.headers
                    .map(
                      (header) =>
                        `<td title="${escapeHtml(
                          row[header] || ""
                        )}">${escapeHtml(
                          (row[header] || "").toString().substring(0, 50)
                        )}${
                          (row[header] || "").toString().length > 50
                            ? "..."
                            : ""
                        }</td>`
                    )
                    .join("")}
                </tr>
              `
                )
                .join("")}
              ${
                fileData.data.length > 10
                  ? `
                <tr>
                  <td colspan="${
                    fileData.headers.length + 1
                  }" class="text-center text-muted">
                    ... and ${fileData.data.length - 10} more rows
                  </td>
                </tr>
              `
                  : ""
              }
            </tbody>
          </table>
        </div>
      `;

      previewContainer.innerHTML = previewHtml;
    } catch (error) {
      previewContainer.innerHTML = `
        <div class="alert alert-danger">
          Failed to load preview: ${error.message}
        </div>
      `;
    }
  } else {
    // Hide preview
    previewContainer.style.display = "none";
    icon.className = "fas fa-chevron-down me-1";
    button.innerHTML = '<i class="fas fa-chevron-down me-1"></i>Show Preview';
  }
}

/**
 * Quick action functions
 */
async function generateTestCasesQuick(serviceId) {
  const operationId = asyncEventManager.registerOperation(
    `quick-test-cases-${serviceId}`,
    {
      showProgress: true,
      description: "Generating test cases for all endpoints...",
    }
  );

  try {
    const endpointsResponse = await apiRequest(
      `/services/${serviceId}/endpoints`
    );
    const endpoints = endpointsResponse.data || [];

    asyncEventManager.updateOperation(operationId, { progress: 25 });

    const selectedEndpoints = endpoints.map(
      (ep) => `${ep.method.toLowerCase()}-${ep.path}`
    );

    const response = await apiRequest(
      `/services/${serviceId}/generate/test-cases`,
      {
        method: "POST",
        body: JSON.stringify({
          selected_endpoints: selectedEndpoints,
          clear_test_cases: false,
        }),
      }
    );

    asyncEventManager.completeOperation(operationId, {
      status: "completed",
      message: `Generated test cases for ${selectedEndpoints.length} endpoints`,
    });

    // Refresh current tab if it's test cases
    if (currentActiveTab === "test-cases") {
      await loadServiceTestCases(serviceId);
    }
  } catch (error) {
    asyncEventManager.failOperation(operationId, error);
  }
}

async function generateTestDataQuick(serviceId) {
  const operationId = asyncEventManager.registerOperation(
    `quick-test-data-${serviceId}`,
    {
      showProgress: true,
      description: "Generating test data for all endpoints...",
    }
  );

  try {
    const response = await apiRequest(
      `/services/${serviceId}/generate/test-data`,
      {
        method: "POST",
        body: JSON.stringify({
          mode: "all",
          regenerate: false,
        }),
      }
    );

    asyncEventManager.completeOperation(operationId, {
      status: "completed",
      message: "Test data generated successfully",
    });

    // Refresh current tab if it's test data
    if (currentActiveTab === "test-data") {
      await loadServiceTestData(serviceId);
    }
  } catch (error) {
    asyncEventManager.failOperation(operationId, error);
  }
}

async function generateCompleteTestSuite(serviceId) {
  const operationId = asyncEventManager.registerOperation(
    `complete-suite-${serviceId}`,
    {
      showProgress: true,
      description: "Generating complete test suite (test cases + test data)...",
      timeout: 300000, // 5 minutes for complete generation
    }
  );

  try {
    asyncEventManager.updateOperation(operationId, {
      progress: 10,
      description: "Starting complete test suite generation...",
    });

    const response = await apiRequest(
      `/services/${serviceId}/generate/complete`,
      {
        method: "POST",
        body: JSON.stringify({
          mode: "all",
          regenerate: true, // Force regenerate for complete suite
        }),
      }
    );

    asyncEventManager.updateOperation(operationId, {
      progress: 90,
      description: "Finalizing generation...",
    });

    asyncEventManager.completeOperation(operationId, {
      message: `✅ Complete test suite generated! ${response.data.test_cases_generated} test cases, ${response.data.test_data_generated} test data files`,
      result: response.data,
    });

    // Refresh all relevant tabs
    if (currentActiveTab === "test-cases") {
      loadServiceTestCases(serviceId);
    }
    if (currentActiveTab === "test-data") {
      loadServiceTestData(serviceId);
    }

    // Show detailed success notification
    showNotification(
      `🚀 Complete test suite generated successfully!\n` +
        `📄 Test Cases: ${response.data.test_cases_generated}\n` +
        `💾 Test Data Files: ${response.data.test_data_generated}\n` +
        `🎯 Endpoints Processed: ${response.data.endpoints_processed}`,
      "success"
    );
  } catch (error) {
    asyncEventManager.failOperation(operationId, error);
  }
}

async function runQuickTest(serviceId) {
  const operationId = asyncEventManager.registerOperation(
    `quick-test-${serviceId}`,
    {
      showProgress: true,
      description: "Starting quick test run...",
    }
  );

  try {
    // Get service data to determine base URL
    const serviceResponse = await apiRequest(`/services/${serviceId}`);
    const service = serviceResponse.data;

    // Prompt for base URL if needed
    const baseUrl = prompt(
      "Enter base URL for testing:",
      "https://api.example.com"
    );
    if (!baseUrl) {
      asyncEventManager.cancelOperation(operationId);
      return;
    }

    asyncEventManager.updateOperation(operationId, { progress: 25 });

    const response = await apiRequest(`/services/${serviceId}/runs`, {
      method: "POST",
      body: JSON.stringify({
        base_url: baseUrl,
        token: null,
        endpoint_filter: null,
      }),
    });

    const runId = response.data.run_id;

    // Start tracking the test run
    asyncEventManager.trackTestRun(serviceId, runId);

    asyncEventManager.completeOperation(operationId, {
      status: "completed",
      message: "Test run started successfully",
    });

    // Switch to test runs tab
    switchToTab("test-runs");
  } catch (error) {
    asyncEventManager.failOperation(operationId, error);
  }
}

/**
 * Test case interaction functions
 */
function toggleAllTestCases(checkbox) {
  const checkboxes = document.querySelectorAll(".test-case-checkbox");
  checkboxes.forEach((cb) => (cb.checked = checkbox.checked));

  updateBulkActionsVisibility();
}

function updateBulkActionsVisibility() {
  const checkedBoxes = document.querySelectorAll(".test-case-checkbox:checked");
  const bulkActions = document.getElementById("bulk-actions");

  if (bulkActions) {
    bulkActions.style.display = checkedBoxes.length > 0 ? "block" : "none";
  }
}

async function expandTestCase(serviceId, testCaseId) {
  const detailsRow = document.getElementById(`details-${testCaseId}`);
  const detailsContent = detailsRow.querySelector(".test-case-details-content");

  if (detailsRow.style.display === "none") {
    detailsRow.style.display = "table-row";

    // Load test case details
    try {
      const response = await apiRequest(
        `/services/${serviceId}/test-cases/${testCaseId}`
      );
      const testCase = response.data;

      detailsContent.innerHTML = `
        <div class="row">
          <div class="col-md-6">
            <h6>Parameters</h6>
            <div class="code-block small">${
              testCase.parameters
                ? JSON.stringify(testCase.parameters, null, 2)
                : "No parameters"
            }</div>
          </div>
          <div class="col-md-6">
            <h6>Request Body</h6>
            <div class="code-block small">${
              testCase.body ? JSON.stringify(testCase.body, null, 2) : "No body"
            }</div>
          </div>
        </div>
        <div class="row mt-3">
          <div class="col-12">
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-success" onclick="runSingleTestCaseInline('${serviceId}', '${testCaseId}')">
                <i class="fas fa-play me-1"></i>Run Test
              </button>
              <button class="btn btn-sm btn-primary" onclick="editTestCase('${serviceId}', '${testCaseId}')">
                <i class="fas fa-edit me-1"></i>Edit
              </button>
              <button class="btn btn-sm btn-outline-secondary" onclick="duplicateTestCase('${serviceId}', '${testCaseId}')">
                <i class="fas fa-copy me-1"></i>Duplicate
              </button>
            </div>
          </div>
        </div>
      `;
    } catch (error) {
      detailsContent.innerHTML = `<div class="alert alert-danger">Failed to load test case details: ${error.message}</div>`;
    }
  } else {
    detailsRow.style.display = "none";
  }
}

async function runSingleTestCaseInline(serviceId, testCaseId) {
  try {
    showNotification("Executing test case with SequenceRunner...", "info");

    // Use new API endpoint to run single test case
    const response = await apiRequest(
      `/services/${serviceId}/test-cases/${testCaseId}/run`,
      {
        method: "POST",
        body: JSON.stringify({
          base_url: "https://bills-api.parliament.uk", // Default for Bill service
          token: null,
          endpoint_filter: null,
          test_case_filter: [testCaseId],
        }),
      }
    );

    if (response.data.test_passed) {
      showNotification(
        `✅ Test case PASSED: ${response.data.result}`,
        "success"
      );
    } else {
      showNotification(
        `❌ Test case FAILED: ${response.data.result}`,
        "danger"
      );
    }

    // Show detailed results
    console.log("Test execution details:", response.data);
  } catch (error) {
    showNotification(`Failed to execute test case: ${error.message}`, "danger");
  }
}

/**
 * Service management functions
 */
async function editServiceSpec(serviceId) {
  try {
    // Navigate to service detail view and switch to settings tab
    await showServiceDetail(serviceId);
    switchToTab("settings");

    // Focus on the spec editor if available
    setTimeout(() => {
      const specEditor = document.querySelector(
        '#service-settings-content textarea, #service-settings-content input[type="file"]'
      );
      if (specEditor) {
        specEditor.scrollIntoView({ behavior: "smooth" });
        specEditor.focus();
      }
    }, 500);
  } catch (error) {
    console.error("Failed to edit service spec:", error);
    showNotification("Failed to open service spec editor", "danger");
  }
}

/**
 * Endpoint interaction functions
 */
async function generateTestCaseForEndpoint(serviceId, endpointId) {
  try {
    showNotification("Generating test case for endpoint...", "info");

    const response = await apiRequest(
      `/services/${serviceId}/generate/test-cases`,
      {
        method: "POST",
        body: JSON.stringify({
          selected_endpoints: [endpointId],
          clear_test_cases: false,
        }),
      }
    );

    showNotification("Test case generated successfully!", "success");

    // Refresh test cases if we're on that tab
    if (currentActiveTab === "test-cases") {
      loadServiceTestCases(serviceId);
    }
  } catch (error) {
    showNotification(
      `Failed to generate test case: ${error.message}`,
      "danger"
    );
  }
}

async function generateTestDataForEndpoint(serviceId, endpointId) {
  try {
    showNotification("Generating test data for endpoint...", "info");

    const response = await apiRequest(
      `/services/${serviceId}/generate/test-data`,
      {
        method: "POST",
        body: JSON.stringify({
          endpoints: [endpointId],
          mode: "selected",
          regenerate: false,
        }),
      }
    );

    showNotification("Test data generated successfully!", "success");

    // Refresh test data if we're on that tab
    if (currentActiveTab === "test-data") {
      loadServiceTestData(serviceId);
    }
  } catch (error) {
    showNotification(
      `Failed to generate test data: ${error.message}`,
      "danger"
    );
  }
}

async function testEndpointDirectly(serviceId, endpointMethod, endpointPath) {
  try {
    showNotification("Starting endpoint test...", "info");

    // Create a dry run for this specific endpoint
    const response = await apiRequest(`/services/${serviceId}/dry-run`, {
      method: "POST",
      body: JSON.stringify({
        endpoint: `${endpointMethod.toLowerCase()}-${endpointPath}`,
        include_test_data: true,
      }),
    });

    showNotification("Endpoint test completed!", "success");

    // Show results in a modal or navigate to results
    console.log("Test results:", response.data);
  } catch (error) {
    showNotification(`Failed to test endpoint: ${error.message}`, "danger");
  }
}

async function runSelectedTestCases(serviceId) {
  const selectedCheckboxes = document.querySelectorAll(
    ".test-case-checkbox:checked"
  );
  const selectedIds = Array.from(selectedCheckboxes).map((cb) => cb.value);

  if (selectedIds.length === 0) {
    showNotification("Please select test cases to run", "warning");
    return;
  }

  try {
    showNotification(`Running ${selectedIds.length} test cases...`, "info");

    // Create a run with selected test cases
    const response = await apiRequest(`/services/${serviceId}/runs`, {
      method: "POST",
      body: JSON.stringify({
        test_cases: selectedIds,
        description: `Bulk run of ${selectedIds.length} test cases`,
      }),
    });

    const runId = response.data.id;
    showNotification("Test run created successfully!", "success");

    // Navigate to test runs tab to show the running test
    switchToTab("test-runs");

    // Track the test run
    asyncEventManager.trackTestRun(serviceId, runId);
  } catch (error) {
    showNotification(`Failed to run test cases: ${error.message}`, "danger");
  }
}

async function deleteSelectedTestCases(serviceId) {
  const selectedCheckboxes = document.querySelectorAll(
    ".test-case-checkbox:checked"
  );
  const selectedIds = Array.from(selectedCheckboxes).map((cb) => cb.value);

  if (selectedIds.length === 0) {
    showNotification("Please select test cases to delete", "warning");
    return;
  }

  if (
    !confirm(
      `Are you sure you want to delete ${selectedIds.length} test case(s)?`
    )
  ) {
    return;
  }

  try {
    showNotification(`Deleting ${selectedIds.length} test cases...`, "info");

    // Delete each test case
    const deletePromises = selectedIds.map((id) =>
      apiRequest(`/services/${serviceId}/test-cases/${id}`, {
        method: "DELETE",
      })
    );

    await Promise.all(deletePromises);

    showNotification("Test cases deleted successfully!", "success");

    // Refresh the test cases list
    loadServiceTestCases(serviceId);
  } catch (error) {
    showNotification(`Failed to delete test cases: ${error.message}`, "danger");
  }
}

/**
 * Service management functions
 */
async function validateService(serviceId) {
  try {
    showNotification("Validating service configuration...", "info");

    const response = await apiRequest(`/services/${serviceId}/health`);

    if (response.data.status === "healthy") {
      showNotification("Service validation successful!", "success");
    } else {
      showNotification("Service validation found issues", "warning");
    }
  } catch (error) {
    showNotification(`Service validation failed: ${error.message}`, "danger");
  }
}

async function generateAllForService(serviceId) {
  try {
    const operationId = asyncEventManager.registerOperation(
      `generate-all-${serviceId}`,
      {
        showProgress: true,
        description: "Generating all test cases and test data...",
      }
    );

    const response = await apiRequest(`/services/${serviceId}/generate/all`, {
      method: "POST",
      body: JSON.stringify({}),
    });

    asyncEventManager.completeOperation(operationId, {
      message: "Successfully generated all test cases and test data!",
    });

    // Refresh current tab if it's test cases or test data
    if (currentActiveTab === "test-cases") {
      loadServiceTestCases(serviceId);
    } else if (currentActiveTab === "test-data") {
      loadServiceTestData(serviceId);
    }
  } catch (error) {
    asyncEventManager.failOperation(operationId, error);
  }
}

async function exportService(serviceId) {
  try {
    showNotification("Exporting service data...", "info");

    const response = await apiRequest(`/services/${serviceId}/export`);

    // Create download link
    const blob = new Blob([JSON.stringify(response.data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentServiceData.name}_export.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showNotification("Service exported successfully!", "success");
  } catch (error) {
    showNotification(`Failed to export service: ${error.message}`, "danger");
  }
}

async function cloneService(serviceId) {
  try {
    const newName = prompt(
      "Enter name for cloned service:",
      `${currentServiceData.name} (Copy)`
    );
    if (!newName) return;

    showNotification("Cloning service...", "info");

    const response = await apiRequest(`/services/${serviceId}/clone`, {
      method: "POST",
      body: JSON.stringify({
        name: newName,
      }),
    });

    showNotification("Service cloned successfully!", "success");

    // Optionally navigate to the new service
    const newServiceId = response.data.id;
    showServiceDetail(newServiceId);
  } catch (error) {
    showNotification(`Failed to clone service: ${error.message}`, "danger");
  }
}

/**
 * Test data interaction functions
 */
async function viewCsvFileInline(serviceId, filename) {
  try {
    showNotification("Loading CSV data...", "info");

    const response = await apiRequest(
      `/services/${serviceId}/test-data/${encodeURIComponent(filename)}`
    );
    const fileData = response.data;

    // Create a modal to display the CSV data
    const modalContent = `
      <div class="modal fade" id="csvViewModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">
                <i class="fas fa-table me-2"></i>${escapeHtml(filename)}
              </h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div class="table-responsive" style="max-height: 600px;">
                <table class="table table-striped table-hover">
                  <thead class="sticky-top bg-light">
                    <tr>
                      <th width="50">#</th>
                      ${fileData.headers
                        .map((header) => `<th>${escapeHtml(header)}</th>`)
                        .join("")}
                    </tr>
                  </thead>
                  <tbody>
                    ${fileData.data
                      .map(
                        (row, index) => `
                          <tr>
                            <td>${index + 1}</td>
                            ${fileData.headers
                              .map(
                                (header) =>
                                  `<td title="${escapeHtml(
                                    row[header] || ""
                                  )}">${escapeHtml(
                                    (row[header] || "").toString()
                                  )}</td>`
                              )
                              .join("")}
                          </tr>
                        `
                      )
                      .join("")}
                  </tbody>
                </table>
              </div>
              <div class="mt-3 text-muted">
                <small>Total rows: ${fileData.data.length}</small>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                Close
              </button>
              <button type="button" class="btn btn-primary" onclick="editTestDataFileInline('${serviceId}', '${filename}')">
                <i class="fas fa-edit me-1"></i>Edit
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById("csvViewModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalContent);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById("csvViewModal"));
    modal.show();

    showNotification("CSV data loaded successfully!", "success");
  } catch (error) {
    showNotification(`Failed to load CSV data: ${error.message}`, "danger");
  }
}

async function editTestDataFileInline(serviceId, filename) {
  try {
    showNotification("Loading file for editing...", "info");

    const response = await apiRequest(
      `/services/${serviceId}/test-data/${encodeURIComponent(filename)}`
    );
    const fileData = response.data;

    // Create an editable modal
    const modalContent = `
      <div class="modal fade" id="csvEditModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">
                <i class="fas fa-edit me-2"></i>Edit ${escapeHtml(filename)}
              </h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Edit the CSV data below. Each row should be on a separate line.
              </div>
              <div class="mb-3">
                <label class="form-label">CSV Data:</label>
                <textarea id="csvEditContent" class="form-control" rows="15" style="font-family: monospace;">${escapeHtml(
                  convertToCsvString(fileData)
                )}</textarea>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                Cancel
              </button>
              <button type="button" class="btn btn-primary" onclick="saveCsvFile('${serviceId}', '${filename}')">
                <i class="fas fa-save me-1"></i>Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById("csvEditModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalContent);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById("csvEditModal"));
    modal.show();

    showNotification("File loaded for editing!", "success");
  } catch (error) {
    showNotification(
      `Failed to load file for editing: ${error.message}`,
      "danger"
    );
  }
}

function convertToCsvString(fileData) {
  const headers = fileData.headers.join(",");
  const rows = fileData.data.map((row) =>
    fileData.headers
      .map(
        (header) => `"${(row[header] || "").toString().replace(/"/g, '""')}"`
      )
      .join(",")
  );
  return [headers, ...rows].join("\n");
}

async function saveCsvFile(serviceId, filename) {
  try {
    const csvContent = document.getElementById("csvEditContent").value;

    showNotification("Saving file...", "info");

    // Note: This would require a backend endpoint to save CSV files
    // For now, we'll just show a success message
    const response = await apiRequest(
      `/services/${serviceId}/test-data/${encodeURIComponent(filename)}`,
      {
        method: "PUT",
        body: JSON.stringify({
          content: csvContent,
        }),
      }
    );

    showNotification("File saved successfully!", "success");

    // Close modal
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("csvEditModal")
    );
    modal.hide();

    // Refresh test data if we're on that tab
    if (currentActiveTab === "test-data") {
      loadServiceTestData(serviceId);
    }
  } catch (error) {
    showNotification(`Failed to save file: ${error.message}`, "danger");
  }
}

// Export functions to global scope
window.showServiceDetail = showServiceDetail;
window.hideServiceBreadcrumb = hideServiceBreadcrumb;
window.switchToTab = switchToTab;
window.filterEndpoints = filterEndpoints;
window.generateTestCaseForEndpoint = generateTestCaseForEndpoint;
window.generateTestDataForEndpoint = generateTestDataForEndpoint;
window.testEndpointDirectly = testEndpointDirectly;
window.toggleAllTestCases = toggleAllTestCases;
window.expandTestCase = expandTestCase;
window.runSingleTestCaseInline = runSingleTestCaseInline;
window.runSelectedTestCases = runSelectedTestCases;
window.deleteSelectedTestCases = deleteSelectedTestCases;
window.generateTestCasesQuick = generateTestCasesQuick;
window.generateTestDataQuick = generateTestDataQuick;
window.generateCompleteTestSuite = generateCompleteTestSuite;
window.runQuickTest = runQuickTest;
window.validateService = validateService;
window.generateAllForService = generateAllForService;
window.exportService = exportService;
window.cloneService = cloneService;
window.toggleFilePreview = toggleFilePreview;
window.viewCsvFileInline = viewCsvFileInline;
window.editTestDataFileInline = editTestDataFileInline;
window.saveServiceSettings = saveServiceSettings;
window.editServiceSpec = editServiceSpec;
window.saveCsvFile = saveCsvFile;
