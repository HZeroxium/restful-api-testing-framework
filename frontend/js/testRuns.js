/**
 * Test Runs Management Module
 * Handles test execution, results viewing, and run management
 */

/**
 * Load test runs for selected service
 */
async function loadTestRunsForService(serviceId) {
  if (!serviceId) {
    showEmpty("test-runs-list", "Please select a service to view test runs");
    return;
  }

  showLoading("test-runs-list");

  try {
    const response = await apiRequest(`/services/${serviceId}/runs`);
    const testRuns = response.data || [];

    if (testRuns.length === 0) {
      showEmpty(
        "test-runs-list",
        "No test runs found for this service",
        '<div class="mt-2"><button class="btn btn-success btn-sm" onclick="showCreateRunModal()"><i class="fas fa-play me-1"></i>Start First Test Run</button></div>'
      );
      return;
    }

    displayTestRunsTable(testRuns, serviceId);
  } catch (error) {
    showError("test-runs-list", "Failed to load test runs");
  }
}

/**
 * Display test runs in a table format
 */
function displayTestRunsTable(testRuns, serviceId) {
  const container = document.getElementById("test-runs-list");

  // Sort runs by created date (newest first)
  const sortedRuns = testRuns.sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  const table = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5>Test Runs (${testRuns.length})</h5>
            <button class="btn btn-sm btn-outline-primary" onclick="refreshTestRuns()">
                <i class="fas fa-sync me-1"></i>Refresh
            </button>
        </div>
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Run ID</th>
                        <th>Status</th>
                        <th>Results</th>
                        <th>Success Rate</th>
                        <th>Configuration</th>
                        <th>Started</th>
                        <th>Duration</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${sortedRuns
                      .map(
                        (run) => `
                        <tr>
                            <td>
                                <code class="text-truncate" style="max-width: 100px; display: inline-block;" title="${
                                  run.id
                                }">
                                    ${run.id.substring(0, 8)}...
                                </code>
                            </td>
                            <td>
                                <span class="status-indicator status-${
                                  run.status
                                }">
                                    ${getStatusIcon(run.status)}
                                    ${run.status}
                                </span>
                            </td>
                            <td>
                                <div class="d-flex gap-1">
                                    <span class="badge bg-primary" title="Total tests">${
                                      run.results.total
                                    }</span>
                                    <span class="badge bg-success" title="Passed tests">${
                                      run.results.passed
                                    }</span>
                                    <span class="badge bg-danger" title="Failed tests">${
                                      run.results.failed
                                    }</span>
                                </div>
                            </td>
                            <td>
                                <div class="d-flex align-items-center">
                                    <div class="progress me-2" style="width: 60px; height: 8px;">
                                        <div class="progress-bar ${getProgressBarClass(
                                          run.results.success_rate
                                        )}" 
                                             style="width: ${
                                               run.results.success_rate
                                             }%"></div>
                                    </div>
                                    <small>${run.results.success_rate}%</small>
                                </div>
                            </td>
                            <td>
                                <div>
                                    <small class="text-muted">
                                        ${
                                          run.config.base_url
                                            ? `<div><strong>URL:</strong> ${escapeHtml(
                                                run.config.base_url
                                              )}</div>`
                                            : ""
                                        }
                                        ${
                                          run.config.endpoint_filter
                                            ? `<div><strong>Filter:</strong> ${escapeHtml(
                                                run.config.endpoint_filter
                                              )}</div>`
                                            : ""
                                        }
                                    </small>
                                </div>
                            </td>
                            <td>
                                <small>${formatDate(run.created_at)}</small>
                                ${
                                  run.started_at
                                    ? `<br><small class="text-muted">Started: ${formatDate(
                                        run.started_at
                                      )}</small>`
                                    : ""
                                }
                            </td>
                            <td>
                                <small>${calculateDuration(
                                  run.started_at,
                                  run.completed_at
                                )}</small>
                            </td>
                            <td>
                                <div class="btn-group" role="group">
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewTestRun('${serviceId}', '${
                          run.id
                        }')" title="View Details">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-info" onclick="viewRunResults('${serviceId}', '${
                          run.id
                        }')" title="View Results">
                                        <i class="fas fa-chart-bar"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-secondary" onclick="viewRunArtifacts('${serviceId}', '${
                          run.id
                        }')" title="View Artifacts">
                                        <i class="fas fa-file-archive"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTestRun('${serviceId}', '${
                          run.id
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
 * Show create run modal
 */
function showCreateRunModal() {
  if (!currentService) {
    showNotification("Please select a service first", "warning");
    return;
  }

  // Reset form
  document.getElementById("createRunForm").reset();

  showModal("createRunModal");
}

/**
 * Create and start test run
 */
async function createTestRun() {
  try {
    const baseUrl = document.getElementById("baseUrl").value.trim();
    const token = document.getElementById("authToken").value.trim();
    const endpointFilter = document
      .getElementById("endpointFilter")
      .value.trim();

    if (!baseUrl) {
      showNotification("Please enter a base URL", "warning");
      return;
    }

    const runData = {
      base_url: baseUrl,
      token: token || null,
      endpoint_filter: endpointFilter || null,
    };

    // Show loading state
    const createButton = event.target;
    const originalText = createButton.innerHTML;
    createButton.innerHTML =
      '<i class="fas fa-spinner fa-spin me-2"></i>Starting...';
    createButton.disabled = true;

    const response = await apiRequest(`/services/${currentService}/runs`, {
      method: "POST",
      body: JSON.stringify(runData),
    });

    showNotification("Test run started successfully!", "success");
    hideModal("createRunModal");
    loadTestRunsForService(currentService); // Refresh runs list

    // Start polling for updates
    const runId = response.data.run_id;
    startRunPolling(currentService, runId);
  } catch (error) {
    showNotification("Failed to start test run: " + error.message, "danger");
  } finally {
    // Reset button state
    const createButton = document.querySelector("#createRunModal .btn-success");
    if (createButton) {
      createButton.innerHTML = '<i class="fas fa-play me-2"></i>Start Run';
      createButton.disabled = false;
    }
  }
}

/**
 * Start polling for run updates
 */
function startRunPolling(serviceId, runId) {
  const pollInterval = setInterval(async () => {
    try {
      const response = await apiRequest(`/services/${serviceId}/runs/${runId}`);
      const run = response.data;

      if (run.status === "completed" || run.status === "failed") {
        clearInterval(pollInterval);
        loadTestRunsForService(serviceId); // Final refresh

        const statusMessage =
          run.status === "completed" ? "completed successfully" : "failed";
        showNotification(
          `Test run ${statusMessage}!`,
          run.status === "completed" ? "success" : "danger"
        );
      }
    } catch (error) {
      console.error("Error polling run status:", error);
      clearInterval(pollInterval);
    }
  }, 3000); // Poll every 3 seconds

  // Stop polling after 10 minutes
  setTimeout(() => {
    clearInterval(pollInterval);
  }, 600000);
}

/**
 * View test run details
 */
async function viewTestRun(serviceId, runId) {
  try {
    const response = await apiRequest(`/services/${serviceId}/runs/${runId}`);
    const run = response.data;

    // Update the modal content
    const modalContent = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Run Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Run ID:</strong></td><td><code>${
                          run.id
                        }</code></td></tr>
                        <tr><td><strong>Service ID:</strong></td><td><code>${
                          run.service_id
                        }</code></td></tr>
                        <tr><td><strong>Status:</strong></td><td><span class="status-indicator status-${
                          run.status
                        }">${getStatusIcon(run.status)} ${
      run.status
    }</span></td></tr>
                        <tr><td><strong>Created:</strong></td><td>${formatDate(
                          run.created_at
                        )}</td></tr>
                        <tr><td><strong>Started:</strong></td><td>${
                          run.started_at
                            ? formatDate(run.started_at)
                            : "Not started"
                        }</td></tr>
                        <tr><td><strong>Completed:</strong></td><td>${
                          run.completed_at
                            ? formatDate(run.completed_at)
                            : "Not completed"
                        }</td></tr>
                        <tr><td><strong>Duration:</strong></td><td>${calculateDuration(
                          run.started_at,
                          run.completed_at
                        )}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Results Summary</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Total Tests:</strong></td><td><span class="badge bg-primary">${
                          run.results.total
                        }</span></td></tr>
                        <tr><td><strong>Passed:</strong></td><td><span class="badge bg-success">${
                          run.results.passed
                        }</span></td></tr>
                        <tr><td><strong>Failed:</strong></td><td><span class="badge bg-danger">${
                          run.results.failed
                        }</span></td></tr>
                        <tr><td><strong>Success Rate:</strong></td><td>
                            <div class="d-flex align-items-center">
                                <div class="progress me-2" style="width: 80px; height: 12px;">
                                    <div class="progress-bar ${getProgressBarClass(
                                      run.results.success_rate
                                    )}" 
                                         style="width: ${
                                           run.results.success_rate
                                         }%"></div>
                                </div>
                                ${run.results.success_rate}%
                            </div>
                        </td></tr>
                    </table>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-12">
                    <h6>Configuration</h6>
                    <div class="code-block">${JSON.stringify(
                      run.config,
                      null,
                      2
                    )}</div>
                </div>
            </div>
            
            ${
              run.artifacts && run.artifacts.length > 0
                ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Artifacts (${run.artifacts.length})</h6>
                        <div class="list-group">
                            ${run.artifacts
                              .map(
                                (artifact) => `
                                <div class="list-group-item d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>${escapeHtml(
                                          artifact.name
                                        )}</strong>
                                        <br>
                                        <small class="text-muted">
                                            ${formatFileSize(artifact.size)} • 
                                            ${formatDate(artifact.created_at)}
                                        </small>
                                    </div>
                                    <div>
                                        <button class="btn btn-sm btn-outline-primary" onclick="downloadArtifact('${
                                          artifact.url
                                        }', '${artifact.name}')">
                                            <i class="fas fa-download"></i>
                                        </button>
                                    </div>
                                </div>
                            `
                              )
                              .join("")}
                        </div>
                    </div>
                </div>
            `
                : ""
            }
            
            ${
              run.logs && run.logs.length > 0
                ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Execution Logs</h6>
                        <div class="code-block" style="max-height: 200px; overflow-y: auto;">
                            ${run.logs.map((log) => escapeHtml(log)).join("")}
                        </div>
                    </div>
                </div>
            `
                : ""
            }
        `;

    // Set content and show modal
    document.getElementById("run-details-content").innerHTML = modalContent;
    showModal("viewRunModal");
  } catch (error) {
    showNotification(
      "Failed to load test run details: " + error.message,
      "danger"
    );
  }
}

/**
 * View run results in detail
 */
async function viewRunResults(serviceId, runId) {
  try {
    const response = await apiRequest(
      `/services/${serviceId}/runs/${runId}/results`
    );
    const resultsData = response.data;

    // Create results modal
    const modalHtml = `
            <div class="modal fade" id="runResultsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Test Run Results</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-md-3">
                                    <div class="card text-center">
                                        <div class="card-body">
                                            <h5 class="card-title text-primary">${
                                              resultsData.run_summary.total
                                            }</h5>
                                            <p class="card-text">Total Tests</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card text-center">
                                        <div class="card-body">
                                            <h5 class="card-title text-success">${
                                              resultsData.run_summary.passed
                                            }</h5>
                                            <p class="card-text">Passed</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card text-center">
                                        <div class="card-body">
                                            <h5 class="card-title text-danger">${
                                              resultsData.run_summary.failed
                                            }</h5>
                                            <p class="card-text">Failed</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card text-center">
                                        <div class="card-body">
                                            <h5 class="card-title text-info">${
                                              resultsData.run_summary
                                                .success_rate
                                            }%</h5>
                                            <p class="card-text">Success Rate</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            ${
                              resultsData.detailed_results &&
                              resultsData.detailed_results.length > 0
                                ? `
                                <h6>Detailed Results</h6>
                                <div class="table-responsive">
                                    <table class="table table-sm table-striped">
                                        <thead>
                                            <tr>
                                                <th>Test Case</th>
                                                <th>Endpoint</th>
                                                <th>Status</th>
                                                <th>Response Time</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${resultsData.detailed_results
                                              .map(
                                                (result) => `
                                                <tr class="test-result-${
                                                  result.status?.toLowerCase() ===
                                                  "pass"
                                                    ? "pass"
                                                    : "fail"
                                                }">
                                                    <td><code>${escapeHtml(
                                                      result.test_case || ""
                                                    )}</code></td>
                                                    <td><code>${escapeHtml(
                                                      result.endpoint || ""
                                                    )}</code></td>
                                                    <td>
                                                        <span class="badge ${
                                                          result.status?.toLowerCase() ===
                                                          "pass"
                                                            ? "bg-success"
                                                            : "bg-danger"
                                                        }">
                                                            ${
                                                              result.status ||
                                                              "Unknown"
                                                            }
                                                        </span>
                                                    </td>
                                                    <td>${
                                                      result.response_time ||
                                                      "N/A"
                                                    }</td>
                                                    <td>
                                                        ${
                                                          result.response_data
                                                            ? `
                                                            <button class="btn btn-sm btn-outline-info" onclick="viewResponseData('${JSON.stringify(
                                                              result.response_data
                                                            ).replace(
                                                              /"/g,
                                                              "&quot;"
                                                            )}')">
                                                                <i class="fas fa-eye"></i>
                                                            </button>
                                                        `
                                                            : ""
                                                        }
                                                    </td>
                                                </tr>
                                            `
                                              )
                                              .join("")}
                                        </tbody>
                                    </table>
                                </div>
                            `
                                : '<div class="text-center text-muted py-4">No detailed results available</div>'
                            }
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-primary" onclick="exportResults('${runId}')">
                                <i class="fas fa-download me-2"></i>Export Results
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("runResultsModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("runResultsModal");
  } catch (error) {
    showNotification("Failed to load test results: " + error.message, "danger");
  }
}

/**
 * View response data
 */
function viewResponseData(responseDataJson) {
  try {
    const responseData = JSON.parse(responseDataJson.replace(/&quot;/g, '"'));

    // Create response data modal
    const modalHtml = `
            <div class="modal fade" id="responseDataModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Response Data</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="json-viewer">${JSON.stringify(
                              responseData,
                              null,
                              2
                            )}</div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("responseDataModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("responseDataModal");
  } catch (error) {
    showNotification(
      "Failed to display response data: " + error.message,
      "danger"
    );
  }
}

/**
 * View run artifacts
 */
async function viewRunArtifacts(serviceId, runId) {
  try {
    const response = await apiRequest(`/services/${serviceId}/runs/${runId}`);
    const run = response.data;

    // Create artifacts modal
    const modalHtml = `
            <div class="modal fade" id="artifactsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Run Artifacts</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${
                              run.artifacts && run.artifacts.length > 0
                                ? `
                                <div class="list-group">
                                    ${run.artifacts
                                      .map(
                                        (artifact) => `
                                        <div class="artifact-item">
                                            <div class="d-flex justify-content-between align-items-center">
                                                <div>
                                                    <h6 class="mb-1">${escapeHtml(
                                                      artifact.name
                                                    )}</h6>
                                                    <small class="text-muted">
                                                        ${formatFileSize(
                                                          artifact.size
                                                        )} • 
                                                        Created ${formatDate(
                                                          artifact.created_at
                                                        )}
                                                    </small>
                                                </div>
                                                <div>
                                                    <button class="btn btn-sm btn-outline-primary" onclick="downloadArtifact('${
                                                      artifact.url
                                                    }', '${artifact.name}')">
                                                        <i class="fas fa-download me-1"></i>Download
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    `
                                      )
                                      .join("")}
                                </div>
                            `
                                : '<div class="text-center text-muted py-4"><i class="fas fa-inbox me-2"></i>No artifacts available</div>'
                            }
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-primary" onclick="downloadAllArtifacts('${serviceId}', '${runId}')">
                                <i class="fas fa-download me-2"></i>Download All
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("artifactsModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("artifactsModal");
  } catch (error) {
    showNotification("Failed to load artifacts: " + error.message, "danger");
  }
}

/**
 * Download artifact
 */
function downloadArtifact(artifactUrl, filename) {
  try {
    // Create a temporary link and trigger download
    const link = document.createElement("a");
    link.href = `${API_BASE_URL}${artifactUrl}`;
    link.download = filename;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showNotification(`Downloading ${filename}...`, "info");
  } catch (error) {
    showNotification("Failed to download artifact: " + error.message, "danger");
  }
}

/**
 * Download all artifacts
 */
async function downloadAllArtifacts(serviceId, runId) {
  try {
    // This would typically create a zip file of all artifacts
    // For now, we'll show a placeholder message
    showNotification(
      "Download all artifacts functionality would be implemented with a backend endpoint",
      "info"
    );
  } catch (error) {
    showNotification(
      "Failed to download artifacts: " + error.message,
      "danger"
    );
  }
}

/**
 * Export results
 */
function exportResults(runId) {
  try {
    // Create export functionality
    showNotification(
      "Export functionality would generate CSV/PDF reports",
      "info"
    );
  } catch (error) {
    showNotification("Failed to export results: " + error.message, "danger");
  }
}

/**
 * Delete test run
 */
async function deleteTestRun(serviceId, runId) {
  if (
    !confirm(
      "Are you sure you want to delete this test run and all its results?"
    )
  ) {
    return;
  }

  try {
    await apiRequest(`/services/${serviceId}/runs/${runId}`, {
      method: "DELETE",
    });

    showNotification("Test run deleted successfully!", "success");
    loadTestRunsForService(serviceId); // Refresh runs list
  } catch (error) {
    showNotification("Failed to delete test run: " + error.message, "danger");
  }
}

/**
 * Refresh test runs
 */
function refreshTestRuns() {
  if (currentService) {
    loadTestRunsForService(currentService);
  }
}

/**
 * Utility functions
 */
function getStatusIcon(status) {
  const iconMap = {
    pending: '<i class="fas fa-clock"></i>',
    running: '<i class="fas fa-spinner fa-spin"></i>',
    completed: '<i class="fas fa-check-circle"></i>',
    failed: '<i class="fas fa-times-circle"></i>',
    cancelled: '<i class="fas fa-stop-circle"></i>',
  };
  return iconMap[status] || '<i class="fas fa-question-circle"></i>';
}

function getProgressBarClass(successRate) {
  if (successRate >= 90) return "bg-success";
  if (successRate >= 70) return "bg-warning";
  return "bg-danger";
}

function calculateDuration(startTime, endTime) {
  if (!startTime) return "Not started";
  if (!endTime) return "Running...";

  try {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diff = end - start;

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  } catch (error) {
    return "Unknown";
  }
}

// Export functions for global access
window.loadTestRunsForService = loadTestRunsForService;
window.showCreateRunModal = showCreateRunModal;
window.createTestRun = createTestRun;
window.viewTestRun = viewTestRun;
window.viewRunResults = viewRunResults;
window.viewResponseData = viewResponseData;
window.viewRunArtifacts = viewRunArtifacts;
window.downloadArtifact = downloadArtifact;
window.downloadAllArtifacts = downloadAllArtifacts;
window.exportResults = exportResults;
window.deleteTestRun = deleteTestRun;
window.refreshTestRuns = refreshTestRuns;
