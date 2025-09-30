/**
 * Test Cases Management Module
 * Handles test case generation and CRUD operations
 */

/**
 * Load test cases for selected service
 */
async function loadTestCasesForService(serviceId) {
  if (!serviceId) {
    showEmpty("test-cases-list", "Please select a service to view test cases");
    return;
  }

  showLoading("test-cases-list");

  try {
    const response = await apiRequest(`/services/${serviceId}/test-cases`);
    const testCases = response.data || [];

    if (testCases.length === 0) {
      showEmpty(
        "test-cases-list",
        "No test cases found for this service",
        '<div class="mt-2"><button class="btn btn-primary btn-sm" onclick="showGenerateTestCasesModal()"><i class="fas fa-magic me-1"></i>Generate Test Cases</button></div>'
      );
      return;
    }

    displayTestCasesTable(testCases, serviceId);
  } catch (error) {
    showError("test-cases-list", "Failed to load test cases");
  }
}

/**
 * Display test cases in a table format
 */
function displayTestCasesTable(testCases, serviceId) {
  const container = document.getElementById("test-cases-list");

  const table = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5>Test Cases (${testCases.length})</h5>
            <button class="btn btn-sm btn-outline-primary" onclick="refreshTestCases()">
                <i class="fas fa-sync me-1"></i>Refresh
            </button>
        </div>
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Test Case ID</th>
                        <th>Endpoint</th>
                        <th>Method</th>
                        <th>Path</th>
                        <th>Description</th>
                        <th>Expected Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${testCases
                      .map(
                        (testCase) => `
                        <tr>
                            <td>
                                <code>${testCase.id}</code>
                            </td>
                            <td>
                                <span class="badge bg-secondary">${escapeHtml(
                                  testCase.endpoint
                                )}</span>
                            </td>
                            <td>
                                <span class="endpoint-method ${getMethodBadgeClass(
                                  testCase.method
                                )}">${testCase.method}</span>
                            </td>
                            <td>
                                <code>${escapeHtml(testCase.path)}</code>
                            </td>
                            <td>
                                <span class="text-truncate" style="max-width: 200px; display: inline-block;" title="${escapeHtml(
                                  testCase.description || ""
                                )}">
                                    ${escapeHtml(
                                      testCase.description || "No description"
                                    )}
                                </span>
                            </td>
                            <td>
                                ${
                                  testCase.expected_status
                                    ? `<span class="badge bg-info">${testCase.expected_status}</span>`
                                    : "-"
                                }
                            </td>
                            <td>
                                <small>${formatDate(
                                  testCase.created_at
                                )}</small>
                            </td>
                            <td>
                                <div class="btn-group" role="group">
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewTestCase('${serviceId}', '${
                          testCase.id
                        }')" title="View Details">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-secondary" onclick="editTestCase('${serviceId}', '${
                          testCase.id
                        }')" title="Edit">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-success" onclick="runSingleTestCase('${serviceId}', '${
                          testCase.id
                        }')" title="Dry Run">
                                        <i class="fas fa-play"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTestCase('${serviceId}', '${
                          testCase.id
                        }')" title="Delete">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `
                      )
                      .join("")}
                </tbody>
            </table>
        </div>
    `;

  container.innerHTML = table;
}

/**
 * Show generate test cases modal
 */
async function showGenerateTestCasesModal() {
  if (!currentService) {
    showNotification("Please select a service first", "warning");
    return;
  }

  try {
    // Load endpoints for the selected service
    const response = await apiRequest(`/services/${currentService}/endpoints`);
    const endpoints = response.data || [];

    // Populate endpoints list
    const endpointsList = document.getElementById("endpoints-list");

    if (endpoints.length === 0) {
      endpointsList.innerHTML =
        '<div class="text-center text-muted py-2">No endpoints found</div>';
    } else {
      endpointsList.innerHTML = endpoints
        .map(
          (endpoint) => `
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${endpoint.method.toLowerCase()}-${
            endpoint.path
          }" id="endpoint-${endpoint.operation_id}">
                    <label class="form-check-label" for="endpoint-${
                      endpoint.operation_id
                    }">
                        <span class="endpoint-method ${getMethodBadgeClass(
                          endpoint.method
                        )}">${endpoint.method}</span>
                        <code>${endpoint.path}</code>
                        ${
                          endpoint.summary
                            ? `<small class="text-muted d-block">${escapeHtml(
                                endpoint.summary
                              )}</small>`
                            : ""
                        }
                    </label>
                </div>
            `
        )
        .join("");
    }

    // Reset form
    document.getElementById("clearTestCases").checked = false;

    showModal("generateTestCasesModal");
  } catch (error) {
    showNotification("Failed to load endpoints: " + error.message, "danger");
  }
}

/**
 * Generate test cases
 */
async function generateTestCases() {
  try {
    // Get selected endpoints
    const selectedEndpoints = [];
    document
      .querySelectorAll('#endpoints-list input[type="checkbox"]:checked')
      .forEach((checkbox) => {
        selectedEndpoints.push(checkbox.value);
      });

    if (selectedEndpoints.length === 0) {
      showNotification("Please select at least one endpoint", "warning");
      return;
    }

    const clearTestCases = document.getElementById("clearTestCases").checked;

    const requestData = {
      selected_endpoints: selectedEndpoints,
      clear_test_cases: clearTestCases,
    };

    // Show loading state
    const generateButton = event.target;
    const originalText = generateButton.innerHTML;
    generateButton.innerHTML =
      '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    generateButton.disabled = true;

    const response = await apiRequest(
      `/services/${currentService}/generate/test-cases`,
      {
        method: "POST",
        body: JSON.stringify(requestData),
      }
    );

    showNotification(
      `Successfully generated test cases for ${selectedEndpoints.length} endpoint(s)!`,
      "success"
    );
    hideModal("generateTestCasesModal");
    loadTestCasesForService(currentService); // Refresh test cases list
  } catch (error) {
    showNotification(
      "Failed to generate test cases: " + error.message,
      "danger"
    );
  } finally {
    // Reset button state
    const generateButton = document.querySelector(
      "#generateTestCasesModal .btn-primary"
    );
    if (generateButton) {
      generateButton.innerHTML = '<i class="fas fa-magic me-2"></i>Generate';
      generateButton.disabled = false;
    }
  }
}

/**
 * View test case details
 */
async function viewTestCase(serviceId, testCaseId) {
  try {
    const response = await apiRequest(
      `/services/${serviceId}/test-cases/${testCaseId}`
    );
    const testCase = response.data;

    // Create modal dynamically
    const modalHtml = `
            <div class="modal fade" id="testCaseDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Test Case Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Basic Information</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>ID:</strong></td><td><code>${
                                          testCase.id
                                        }</code></td></tr>
                                        <tr><td><strong>Endpoint:</strong></td><td>${escapeHtml(
                                          testCase.endpoint || ""
                                        )}</td></tr>
                                        <tr><td><strong>Method:</strong></td><td><span class="endpoint-method ${getMethodBadgeClass(
                                          testCase.method || ""
                                        )}">${
      testCase.method || ""
    }</span></td></tr>
                                        <tr><td><strong>Path:</strong></td><td><code>${escapeHtml(
                                          testCase.path || ""
                                        )}</code></td></tr>
                                        <tr><td><strong>Expected Status:</strong></td><td>${
                                          testCase.expected_status
                                            ? `<span class="badge bg-info">${testCase.expected_status}</span>`
                                            : "Not specified"
                                        }</td></tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>Timestamps</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>Created:</strong></td><td>${formatDate(
                                          testCase.created_at || ""
                                        )}</td></tr>
                                        <tr><td><strong>Updated:</strong></td><td>${formatDate(
                                          testCase.updated_at || ""
                                        )}</td></tr>
                                    </table>
                                </div>
                            </div>
                            
                            ${
                              testCase.description
                                ? `
                                <div class="row mt-3">
                                    <div class="col-12">
                                        <h6>Description</h6>
                                        <p class="text-muted">${escapeHtml(
                                          testCase.description
                                        )}</p>
                                    </div>
                                </div>
                            `
                                : ""
                            }
                            
                            ${
                              testCase.parameters &&
                              Object.keys(testCase.parameters).length > 0
                                ? `
                                <div class="row mt-3">
                                    <div class="col-12">
                                        <h6>Parameters</h6>
                                        <div class="code-block">${JSON.stringify(
                                          testCase.parameters,
                                          null,
                                          2
                                        )}</div>
                                    </div>
                                </div>
                            `
                                : ""
                            }
                            
                            ${
                              testCase.body &&
                              Object.keys(testCase.body).length > 0
                                ? `
                                <div class="row mt-3">
                                    <div class="col-12">
                                        <h6>Request Body</h6>
                                        <div class="code-block">${JSON.stringify(
                                          testCase.body,
                                          null,
                                          2
                                        )}</div>
                                    </div>
                                </div>
                            `
                                : ""
                            }
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-primary" onclick="editTestCase('${serviceId}', '${testCaseId}')">
                                <i class="fas fa-edit me-2"></i>Edit
                            </button>
                            <button type="button" class="btn btn-success" onclick="runSingleTestCase('${serviceId}', '${testCaseId}')">
                                <i class="fas fa-play me-2"></i>Dry Run
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("testCaseDetailsModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("testCaseDetailsModal");
  } catch (error) {
    showNotification(
      "Failed to load test case details: " + error.message,
      "danger"
    );
  }
}

/**
 * Edit test case
 */
async function editTestCase(serviceId, testCaseId) {
  try {
    const response = await apiRequest(
      `/services/${serviceId}/test-cases/${testCaseId}`
    );
    const testCase = response.data;

    // Create modal dynamically
    const modalHtml = `
            <div class="modal fade" id="editTestCaseModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit Test Case</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="editTestCaseForm">
                                <div class="mb-3">
                                    <label class="form-label">Description</label>
                                    <textarea class="form-control" id="editDescription" rows="3">${escapeHtml(
                                      testCase.description || ""
                                    )}</textarea>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Expected Status Code</label>
                                    <input type="number" class="form-control" id="editExpectedStatus" value="${
                                      testCase.expected_status || ""
                                    }" min="100" max="599">
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Parameters (JSON)</label>
                                    <textarea class="form-control" id="editParameters" rows="5" style="font-family: monospace;">${
                                      testCase.parameters
                                        ? JSON.stringify(
                                            testCase.parameters,
                                            null,
                                            2
                                          )
                                        : "{}"
                                    }</textarea>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Request Body (JSON)</label>
                                    <textarea class="form-control" id="editBody" rows="5" style="font-family: monospace;">${
                                      testCase.body
                                        ? JSON.stringify(testCase.body, null, 2)
                                        : "{}"
                                    }</textarea>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="updateTestCase('${serviceId}', '${testCaseId}')">
                                <i class="fas fa-save me-2"></i>Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("editTestCaseModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("editTestCaseModal");
  } catch (error) {
    showNotification(
      "Failed to load test case for editing: " + error.message,
      "danger"
    );
  }
}

/**
 * Update test case
 */
async function updateTestCase(serviceId, testCaseId) {
  try {
    const description = document.getElementById("editDescription").value.trim();
    const expectedStatus = document.getElementById("editExpectedStatus").value;
    const parametersText = document
      .getElementById("editParameters")
      .value.trim();
    const bodyText = document.getElementById("editBody").value.trim();

    // Validate JSON fields
    let parameters = null;
    let body = null;

    try {
      if (parametersText && parametersText !== "{}") {
        parameters = JSON.parse(parametersText);
      }
    } catch (error) {
      showNotification(
        "Invalid JSON in parameters field: " + error.message,
        "warning"
      );
      return;
    }

    try {
      if (bodyText && bodyText !== "{}") {
        body = JSON.parse(bodyText);
      }
    } catch (error) {
      showNotification(
        "Invalid JSON in body field: " + error.message,
        "warning"
      );
      return;
    }

    const updateData = {};

    if (description) updateData.description = description;
    if (expectedStatus) updateData.expected_status = parseInt(expectedStatus);
    if (parameters) updateData.parameters = parameters;
    if (body) updateData.body = body;

    await apiRequest(`/services/${serviceId}/test-cases/${testCaseId}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });

    showNotification("Test case updated successfully!", "success");
    hideModal("editTestCaseModal");
    loadTestCasesForService(serviceId); // Refresh test cases list
  } catch (error) {
    showNotification("Failed to update test case: " + error.message, "danger");
  }
}

/**
 * Run single test case (dry run)
 */
async function runSingleTestCase(serviceId, testCaseId) {
  try {
    const response = await apiRequest(
      `/services/${serviceId}/test-cases/${testCaseId}`
    );
    const testCase = response.data;

    // Create dry run modal
    const modalHtml = `
            <div class="modal fade" id="dryRunModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Dry Run Test Case</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="dryRunForm">
                                <div class="mb-3">
                                    <label class="form-label">Base URL</label>
                                    <input type="url" class="form-control" id="dryRunBaseUrl" placeholder="https://api.example.com" required>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Endpoint</label>
                                    <div class="input-group">
                                        <span class="input-group-text">${
                                          testCase.method || "GET"
                                        }</span>
                                        <input type="text" class="form-control" value="${
                                          testCase.path || ""
                                        }" readonly>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Additional Headers (JSON)</label>
                                    <textarea class="form-control" id="dryRunHeaders" rows="3" style="font-family: monospace;" placeholder='{"Authorization": "Bearer token"}'></textarea>
                                </div>
                                
                                <div id="dryRunResult" style="display: none;">
                                    <hr>
                                    <h6>Dry Run Result</h6>
                                    <div id="dryRunResultContent"></div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-success" onclick="executeDryRun('${serviceId}', '${
      testCase.endpoint || ""
    }')">
                                <i class="fas fa-play me-2"></i>Execute Dry Run
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("dryRunModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("dryRunModal");
  } catch (error) {
    showNotification("Failed to prepare dry run: " + error.message, "danger");
  }
}

/**
 * Execute dry run
 */
async function executeDryRun(serviceId, endpoint) {
  try {
    const baseUrl = document.getElementById("dryRunBaseUrl").value.trim();
    const headersText = document.getElementById("dryRunHeaders").value.trim();

    if (!baseUrl) {
      showNotification("Please enter a base URL", "warning");
      return;
    }

    let headers = null;
    if (headersText) {
      try {
        headers = JSON.parse(headersText);
      } catch (error) {
        showNotification(
          "Invalid JSON in headers field: " + error.message,
          "warning"
        );
        return;
      }
    }

    const dryRunData = {
      endpoint: endpoint,
      base_url: baseUrl,
      headers: headers,
    };

    const response = await apiRequest(`/services/${serviceId}/dry-run`, {
      method: "POST",
      body: JSON.stringify(dryRunData),
    });

    // Display result
    const resultContainer = document.getElementById("dryRunResult");
    const resultContent = document.getElementById("dryRunResultContent");

    const result = response.data;

    resultContent.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h6>Request Details</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Method:</strong></td><td><span class="endpoint-method ${getMethodBadgeClass(
                          result.method
                        )}">${result.method}</span></td></tr>
                        <tr><td><strong>URL:</strong></td><td><code>${
                          result.url
                        }</code></td></tr>
                    </table>
                    
                    ${
                      result.headers
                        ? `
                        <h6>Headers</h6>
                        <div class="code-block">${JSON.stringify(
                          result.headers,
                          null,
                          2
                        )}</div>
                    `
                        : ""
                    }
                    
                    ${
                      result.params
                        ? `
                        <h6>Parameters</h6>
                        <div class="code-block">${JSON.stringify(
                          result.params,
                          null,
                          2
                        )}</div>
                    `
                        : ""
                    }
                    
                    ${
                      result.body
                        ? `
                        <h6>Body</h6>
                        <div class="code-block">${JSON.stringify(
                          result.body,
                          null,
                          2
                        )}</div>
                    `
                        : ""
                    }
                    
                    ${
                      result.validation_errors &&
                      result.validation_errors.length > 0
                        ? `
                        <h6>Validation Errors</h6>
                        <div class="alert alert-warning">
                            <ul class="mb-0">
                                ${result.validation_errors
                                  .map(
                                    (error) => `<li>${escapeHtml(error)}</li>`
                                  )
                                  .join("")}
                            </ul>
                        </div>
                    `
                        : ""
                    }
                </div>
            </div>
        `;

    resultContainer.style.display = "block";
  } catch (error) {
    showNotification("Failed to execute dry run: " + error.message, "danger");
  }
}

/**
 * Delete test case
 */
async function deleteTestCase(serviceId, testCaseId) {
  if (!confirm(`Are you sure you want to delete this test case?`)) {
    return;
  }

  try {
    await apiRequest(`/services/${serviceId}/test-cases/${testCaseId}`, {
      method: "DELETE",
    });

    showNotification("Test case deleted successfully!", "success");
    loadTestCasesForService(serviceId); // Refresh test cases list
  } catch (error) {
    showNotification("Failed to delete test case: " + error.message, "danger");
  }
}

/**
 * Refresh test cases
 */
function refreshTestCases() {
  if (currentService) {
    loadTestCasesForService(currentService);
  }
}

// Export functions for global access
window.loadTestCasesForService = loadTestCasesForService;
window.showGenerateTestCasesModal = showGenerateTestCasesModal;
window.generateTestCases = generateTestCases;
window.viewTestCase = viewTestCase;
window.editTestCase = editTestCase;
window.updateTestCase = updateTestCase;
window.runSingleTestCase = runSingleTestCase;
window.executeDryRun = executeDryRun;
window.deleteTestCase = deleteTestCase;
window.refreshTestCases = refreshTestCases;
