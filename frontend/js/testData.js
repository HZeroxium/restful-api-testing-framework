/**
 * Test Data Management Module
 * Handles test data generation, viewing, validation, and management
 */

/**
 * Load test data for selected service
 */
async function loadTestDataForService(serviceId) {
  if (!serviceId) {
    showEmpty("test-data-list", "Please select a service to view test data");
    return;
  }

  showLoading("test-data-list");

  try {
    const response = await apiRequest(`/services/${serviceId}/test-data`);
    const testDataFiles = response.data || [];

    if (testDataFiles.length === 0) {
      showEmpty(
        "test-data-list",
        "No test data found for this service",
        '<div class="mt-2"><button class="btn btn-primary btn-sm" onclick="showGenerateTestDataModal()"><i class="fas fa-magic me-1"></i>Generate Test Data</button></div>'
      );
      return;
    }

    displayTestDataTable(testDataFiles, serviceId);
  } catch (error) {
    showError("test-data-list", "Failed to load test data");
  }
}

/**
 * Display test data files in a table format
 */
function displayTestDataTable(testDataFiles, serviceId) {
  const container = document.getElementById("test-data-list");

  const table = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5>Test Data Files (${testDataFiles.length})</h5>
            <div>
                <button class="btn btn-sm btn-outline-secondary me-2" onclick="validateTestData('${serviceId}')">
                    <i class="fas fa-check-circle me-1"></i>Validate All
                </button>
                <button class="btn btn-sm btn-outline-primary" onclick="refreshTestData()">
                    <i class="fas fa-sync me-1"></i>Refresh
                </button>
            </div>
        </div>
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>File Name</th>
                        <th>Endpoint</th>
                        <th>Columns</th>
                        <th>Rows</th>
                        <th>File Size</th>
                        <th>Modified</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${testDataFiles
                      .map(
                        (file) => `
                        <tr>
                            <td>
                                <div>
                                    <strong>${escapeHtml(
                                      file.filename
                                    )}</strong>
                                    <br>
                                    <small class="text-muted">${
                                      file.path
                                    }</small>
                                </div>
                            </td>
                            <td>
                                <span class="badge bg-secondary">${escapeHtml(
                                  file.endpoint || "Unknown"
                                )}</span>
                            </td>
                            <td>
                                <span class="badge bg-info">${
                                  file.headers ? file.headers.length : 0
                                }</span>
                                ${
                                  file.headers && file.headers.length > 0
                                    ? `
                                    <div class="mt-1">
                                        ${file.headers
                                          .slice(0, 3)
                                          .map(
                                            (header) =>
                                              `<small class="badge bg-light text-dark me-1">${escapeHtml(
                                                header
                                              )}</small>`
                                          )
                                          .join("")}
                                        ${
                                          file.headers.length > 3
                                            ? `<small class="text-muted">+${
                                                file.headers.length - 3
                                              } more</small>`
                                            : ""
                                        }
                                    </div>
                                `
                                    : ""
                                }
                            </td>
                            <td>
                                <span class="badge bg-primary">${
                                  file.row_count || 0
                                }</span>
                            </td>
                            <td>
                                <small>${formatFileSize(file.size)}</small>
                            </td>
                            <td>
                                <small>${formatDate(
                                  new Date(file.modified_at * 1000)
                                )}</small>
                            </td>
                            <td>
                                <div class="btn-group" role="group">
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewTestDataFile('${serviceId}', '${escapeHtml(
                          file.filename
                        )}')" title="View Data">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-secondary" onclick="downloadTestDataFile('${serviceId}', '${escapeHtml(
                          file.filename
                        )}')" title="Download">
                                        <i class="fas fa-download"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-warning" onclick="editTestDataFile('${serviceId}', '${escapeHtml(
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
 * Show generate test data modal
 */
async function showGenerateTestDataModal() {
  if (!currentService) {
    showNotification("Please select a service first", "warning");
    return;
  }

  try {
    // Load endpoints for the selected service
    const response = await apiRequest(`/services/${currentService}/endpoints`);
    const endpoints = response.data || [];

    // Populate endpoints list for selected mode
    const endpointsList = document.getElementById("test-data-endpoints");

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
          }" id="td-endpoint-${endpoint.operation_id}">
                    <label class="form-check-label" for="td-endpoint-${
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
    document.getElementById("testDataMode").value = "all";
    document.getElementById("regenerateTestData").checked = false;
    handleTestDataModeChange();

    showModal("generateTestDataModal");
  } catch (error) {
    showNotification("Failed to load endpoints: " + error.message, "danger");
  }
}

/**
 * Handle test data mode change
 */
function handleTestDataModeChange() {
  const mode = document.getElementById("testDataMode").value;
  const endpointsList = document.getElementById("testDataEndpointsList");

  if (mode === "selected") {
    endpointsList.style.display = "block";
  } else {
    endpointsList.style.display = "none";
  }
}

/**
 * Generate test data
 */
async function generateTestData() {
  try {
    const mode = document.getElementById("testDataMode").value;
    const regenerate = document.getElementById("regenerateTestData").checked;

    let selectedEndpoints = null;

    if (mode === "selected") {
      selectedEndpoints = [];
      document
        .querySelectorAll('#test-data-endpoints input[type="checkbox"]:checked')
        .forEach((checkbox) => {
          selectedEndpoints.push(checkbox.value);
        });

      if (selectedEndpoints.length === 0) {
        showNotification("Please select at least one endpoint", "warning");
        return;
      }
    }

    const requestData = {
      mode: mode,
      endpoints: selectedEndpoints,
      regenerate: regenerate,
    };

    // Show loading state
    const generateButton = event.target;
    const originalText = generateButton.innerHTML;
    generateButton.innerHTML =
      '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    generateButton.disabled = true;

    const response = await apiRequest(
      `/services/${currentService}/generate/test-data`,
      {
        method: "POST",
        body: JSON.stringify(requestData),
      }
    );

    const endpointCount = selectedEndpoints ? selectedEndpoints.length : "all";
    showNotification(
      `Successfully generated test data for ${endpointCount} endpoint(s)!`,
      "success"
    );
    hideModal("generateTestDataModal");
    loadTestDataForService(currentService); // Refresh test data list
  } catch (error) {
    showNotification(
      "Failed to generate test data: " + error.message,
      "danger"
    );
  } finally {
    // Reset button state
    const generateButton = document.querySelector(
      "#generateTestDataModal .btn-primary"
    );
    if (generateButton) {
      generateButton.innerHTML = '<i class="fas fa-magic me-2"></i>Generate';
      generateButton.disabled = false;
    }
  }
}

/**
 * View test data file content
 */
async function viewTestDataFile(serviceId, filename) {
  try {
    const response = await apiRequest(
      `/services/${serviceId}/test-data/${encodeURIComponent(filename)}`
    );
    const fileData = response.data;

    // Create modal dynamically
    const modalHtml = `
            <div class="modal fade" id="viewTestDataModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Test Data: ${escapeHtml(
                              filename
                            )}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <h6>File Information</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>Filename:</strong></td><td>${escapeHtml(
                                          fileData.filename
                                        )}</td></tr>
                                        <tr><td><strong>Columns:</strong></td><td><span class="badge bg-info">${
                                          fileData.headers.length
                                        }</span></td></tr>
                                        <tr><td><strong>Rows:</strong></td><td><span class="badge bg-primary">${
                                          fileData.row_count
                                        }</span></td></tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>Column Headers</h6>
                                    <div>
                                        ${fileData.headers
                                          .map(
                                            (header) =>
                                              `<span class="badge bg-light text-dark me-1 mb-1">${escapeHtml(
                                                header
                                              )}</span>`
                                          )
                                          .join("")}
                                    </div>
                                </div>
                            </div>
                            
                            <h6>Data Preview</h6>
                            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                                ${
                                  fileData.data && fileData.data.length > 0
                                    ? `
                                    <table class="table table-sm table-striped">
                                        <thead class="sticky-top bg-light">
                                            <tr>
                                                <th>#</th>
                                                ${fileData.headers
                                                  .map(
                                                    (header) =>
                                                      `<th>${escapeHtml(
                                                        header
                                                      )}</th>`
                                                  )
                                                  .join("")}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${fileData.data
                                              .slice(0, 100)
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
                                                            row[header] || ""
                                                          )}</td>`
                                                      )
                                                      .join("")}
                                                </tr>
                                            `
                                              )
                                              .join("")}
                                            ${
                                              fileData.data.length > 100
                                                ? `
                                                <tr>
                                                    <td colspan="${
                                                      fileData.headers.length +
                                                      1
                                                    }" class="text-center text-muted">
                                                        ... and ${
                                                          fileData.data.length -
                                                          100
                                                        } more rows
                                                    </td>
                                                </tr>
                                            `
                                                : ""
                                            }
                                        </tbody>
                                    </table>
                                `
                                    : '<div class="text-center text-muted py-4">No data available</div>'
                                }
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-secondary" onclick="downloadTestDataFile('${serviceId}', '${escapeHtml(
      filename
    )}')">
                                <i class="fas fa-download me-2"></i>Download
                            </button>
                            <button type="button" class="btn btn-primary" onclick="editTestDataFile('${serviceId}', '${escapeHtml(
      filename
    )}')">
                                <i class="fas fa-edit me-2"></i>Edit
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("viewTestDataModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("viewTestDataModal");
  } catch (error) {
    showNotification(
      "Failed to load test data file: " + error.message,
      "danger"
    );
  }
}

/**
 * Edit test data file
 */
async function editTestDataFile(serviceId, filename) {
  try {
    const response = await apiRequest(
      `/services/${serviceId}/test-data/${encodeURIComponent(filename)}`
    );
    const fileData = response.data;

    // Convert data to CSV format for editing
    let csvContent = "";
    if (fileData.headers && fileData.headers.length > 0) {
      csvContent = fileData.headers.join(",") + "\n";

      if (fileData.data && fileData.data.length > 0) {
        csvContent += fileData.data
          .map((row) =>
            fileData.headers
              .map((header) => JSON.stringify(row[header] || ""))
              .join(",")
          )
          .join("\n");
      }
    }

    // Create modal dynamically
    const modalHtml = `
            <div class="modal fade" id="editTestDataModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit Test Data: ${escapeHtml(
                              filename
                            )}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                Edit the CSV data below. Ensure proper CSV formatting with headers in the first row.
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">CSV Content</label>
                                <textarea class="form-control" id="csvContent" rows="15" style="font-family: monospace;">${escapeHtml(
                                  csvContent
                                )}</textarea>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <small class="text-muted">
                                        <strong>Current:</strong> ${
                                          fileData.row_count
                                        } rows, ${
      fileData.headers.length
    } columns
                                    </small>
                                </div>
                                <div class="col-md-6 text-end">
                                    <button class="btn btn-sm btn-outline-secondary" onclick="previewCsvChanges()">
                                        <i class="fas fa-eye me-1"></i>Preview Changes
                                    </button>
                                </div>
                            </div>
                            
                            <div id="csvPreview" style="display: none;" class="mt-3">
                                <h6>Preview</h6>
                                <div id="csvPreviewContent" class="border rounded p-2" style="max-height: 200px; overflow: auto; background-color: #f8f9fa;"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-warning" onclick="validateCsvData()">
                                <i class="fas fa-check me-2"></i>Validate
                            </button>
                            <button type="button" class="btn btn-primary" onclick="saveTestDataFile('${serviceId}', '${escapeHtml(
      filename
    )}')">
                                <i class="fas fa-save me-2"></i>Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("editTestDataModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("editTestDataModal");
  } catch (error) {
    showNotification(
      "Failed to load test data file for editing: " + error.message,
      "danger"
    );
  }
}

/**
 * Preview CSV changes
 */
function previewCsvChanges() {
  try {
    const csvContent = document.getElementById("csvContent").value;
    const lines = csvContent.trim().split("\n");

    if (lines.length === 0) {
      document.getElementById("csvPreviewContent").innerHTML =
        '<div class="text-muted">No data to preview</div>';
      return;
    }

    const headers = lines[0].split(",").map((h) => h.replace(/"/g, "").trim());
    const dataLines = lines.slice(1, 6); // Show first 5 data rows

    let previewHtml = `
            <table class="table table-sm">
                <thead>
                    <tr>
                        ${headers
                          .map((header) => `<th>${escapeHtml(header)}</th>`)
                          .join("")}
                    </tr>
                </thead>
                <tbody>
                    ${dataLines
                      .map((line) => {
                        const cells = line
                          .split(",")
                          .map((cell) => cell.replace(/"/g, "").trim());
                        return `<tr>${cells
                          .map((cell) => `<td>${escapeHtml(cell)}</td>`)
                          .join("")}</tr>`;
                      })
                      .join("")}
                    ${
                      lines.length > 6
                        ? `
                        <tr>
                            <td colspan="${
                              headers.length
                            }" class="text-center text-muted">
                                ... and ${lines.length - 6} more rows
                            </td>
                        </tr>
                    `
                        : ""
                    }
                </tbody>
            </table>
        `;

    document.getElementById("csvPreviewContent").innerHTML = previewHtml;
    document.getElementById("csvPreview").style.display = "block";
  } catch (error) {
    document.getElementById(
      "csvPreviewContent"
    ).innerHTML = `<div class="text-danger">Error parsing CSV: ${escapeHtml(
      error.message
    )}</div>`;
    document.getElementById("csvPreview").style.display = "block";
  }
}

/**
 * Validate CSV data
 */
function validateCsvData() {
  try {
    const csvContent = document.getElementById("csvContent").value.trim();
    const lines = csvContent.split("\n");

    if (lines.length === 0) {
      showNotification("CSV content is empty", "warning");
      return;
    }

    const headers = lines[0].split(",").map((h) => h.replace(/"/g, "").trim());
    const dataLines = lines.slice(1);

    // Basic validation
    const issues = [];

    if (headers.length === 0) {
      issues.push("No headers found");
    }

    if (dataLines.length === 0) {
      issues.push("No data rows found");
    }

    // Check for inconsistent column counts
    dataLines.forEach((line, index) => {
      const cells = line.split(",");
      if (cells.length !== headers.length) {
        issues.push(
          `Row ${index + 2}: Expected ${headers.length} columns, found ${
            cells.length
          }`
        );
      }
    });

    if (issues.length === 0) {
      showNotification("CSV data is valid!", "success");
    } else {
      showNotification(
        `Validation issues found:\n${issues.join("\n")}`,
        "warning"
      );
    }
  } catch (error) {
    showNotification("Error validating CSV: " + error.message, "danger");
  }
}

/**
 * Save test data file (Note: This would require a backend endpoint to save files)
 */
async function saveTestDataFile(serviceId, filename) {
  try {
    const csvContent = document.getElementById("csvContent").value.trim();

    if (!csvContent) {
      showNotification("CSV content cannot be empty", "warning");
      return;
    }

    // TODO: Implement save endpoint in backend
    // For now, show a placeholder message
    showNotification(
      "Save functionality would be implemented with a backend endpoint",
      "info"
    );

    // Uncomment when backend endpoint is available:
    /*
        const saveData = {
            content: csvContent
        };
        
        await apiRequest(`/services/${serviceId}/test-data/${encodeURIComponent(filename)}`, {
            method: 'PUT',
            body: JSON.stringify(saveData)
        });
        
        showNotification('Test data file saved successfully!', 'success');
        hideModal('editTestDataModal');
        loadTestDataForService(serviceId); // Refresh test data list
        */
  } catch (error) {
    showNotification(
      "Failed to save test data file: " + error.message,
      "danger"
    );
  }
}

/**
 * Download test data file
 */
function downloadTestDataFile(serviceId, filename) {
  try {
    // Create download link
    const downloadUrl = `${API_BASE_URL}/services/${serviceId}/test-data/${encodeURIComponent(
      filename
    )}/download`;

    // For now, we'll open the API endpoint directly
    // In a real implementation, you might want to fetch the file and create a blob
    window.open(downloadUrl, "_blank");

    showNotification("Download started", "info");
  } catch (error) {
    showNotification("Failed to download file: " + error.message, "danger");
  }
}

/**
 * Validate all test data
 */
async function validateTestData(serviceId) {
  try {
    showNotification("Validating test data files...", "info");

    const response = await apiRequest(
      `/services/${serviceId}/test-data/validate`,
      {
        method: "POST",
      }
    );

    const validation = response.data;

    // Create validation results modal
    const modalHtml = `
            <div class="modal fade" id="validationResultsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Test Data Validation Results</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert ${
                              validation.overall_valid
                                ? "alert-success"
                                : "alert-warning"
                            }">
                                <i class="fas ${
                                  validation.overall_valid
                                    ? "fa-check-circle"
                                    : "fa-exclamation-triangle"
                                } me-2"></i>
                                ${
                                  validation.overall_valid
                                    ? "All test data files are valid!"
                                    : "Some test data files have issues"
                                }
                            </div>
                            
                            <div class="accordion" id="validationAccordion">
                                ${validation.file_results
                                  .map(
                                    (file, index) => `
                                    <div class="accordion-item">
                                        <h2 class="accordion-header" id="heading${index}">
                                            <button class="accordion-button ${
                                              file.valid ? "collapsed" : ""
                                            }" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${index}">
                                                <i class="fas ${
                                                  file.valid
                                                    ? "fa-check text-success"
                                                    : "fa-times text-danger"
                                                } me-2"></i>
                                                ${escapeHtml(file.filename)}
                                                <span class="badge ${
                                                  file.valid
                                                    ? "bg-success"
                                                    : "bg-danger"
                                                } ms-2">
                                                    ${
                                                      file.valid
                                                        ? "Valid"
                                                        : "Invalid"
                                                    }
                                                </span>
                                                ${
                                                  file.row_count
                                                    ? `<small class="text-muted ms-2">(${file.row_count} rows)</small>`
                                                    : ""
                                                }
                                            </button>
                                        </h2>
                                        <div id="collapse${index}" class="accordion-collapse collapse ${
                                      !file.valid ? "show" : ""
                                    }" data-bs-parent="#validationAccordion">
                                            <div class="accordion-body">
                                                ${
                                                  file.errors &&
                                                  file.errors.length > 0
                                                    ? `
                                                    <h6 class="text-danger">Errors:</h6>
                                                    <ul class="list-unstyled">
                                                        ${file.errors
                                                          .map(
                                                            (error) =>
                                                              `<li class="text-danger"><i class="fas fa-times me-1"></i>${escapeHtml(
                                                                error
                                                              )}</li>`
                                                          )
                                                          .join("")}
                                                    </ul>
                                                `
                                                    : ""
                                                }
                                                
                                                ${
                                                  file.warnings &&
                                                  file.warnings.length > 0
                                                    ? `
                                                    <h6 class="text-warning">Warnings:</h6>
                                                    <ul class="list-unstyled">
                                                        ${file.warnings
                                                          .map(
                                                            (warning) =>
                                                              `<li class="text-warning"><i class="fas fa-exclamation-triangle me-1"></i>${escapeHtml(
                                                                warning
                                                              )}</li>`
                                                          )
                                                          .join("")}
                                                    </ul>
                                                `
                                                    : ""
                                                }
                                                
                                                ${
                                                  file.valid &&
                                                  (!file.errors ||
                                                    file.errors.length === 0) &&
                                                  (!file.warnings ||
                                                    file.warnings.length === 0)
                                                    ? `
                                                    <div class="text-success">
                                                        <i class="fas fa-check-circle me-2"></i>File is valid and ready for testing
                                                    </div>
                                                `
                                                    : ""
                                                }
                                            </div>
                                        </div>
                                    </div>
                                `
                                  )
                                  .join("")}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("validationResultsModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("validationResultsModal");
  } catch (error) {
    showNotification(
      "Failed to validate test data: " + error.message,
      "danger"
    );
  }
}

/**
 * Delete test data file
 */
async function deleteTestDataFile(serviceId, filename) {
  if (
    !confirm(
      `Are you sure you want to delete the test data file "${filename}"?`
    )
  ) {
    return;
  }

  try {
    await apiRequest(
      `/services/${serviceId}/test-data/${encodeURIComponent(filename)}`,
      {
        method: "DELETE",
      }
    );

    showNotification("Test data file deleted successfully!", "success");
    loadTestDataForService(serviceId); // Refresh test data list
  } catch (error) {
    showNotification(
      "Failed to delete test data file: " + error.message,
      "danger"
    );
  }
}

/**
 * Refresh test data
 */
function refreshTestData() {
  if (currentService) {
    loadTestDataForService(currentService);
  }
}

// Setup event listeners for test data mode change
document.addEventListener("DOMContentLoaded", function () {
  const testDataModeSelect = document.getElementById("testDataMode");
  if (testDataModeSelect) {
    testDataModeSelect.addEventListener("change", handleTestDataModeChange);
  }
});

// Export functions for global access
window.loadTestDataForService = loadTestDataForService;
window.showGenerateTestDataModal = showGenerateTestDataModal;
window.handleTestDataModeChange = handleTestDataModeChange;
window.generateTestData = generateTestData;
window.viewTestDataFile = viewTestDataFile;
window.editTestDataFile = editTestDataFile;
window.previewCsvChanges = previewCsvChanges;
window.validateCsvData = validateCsvData;
window.saveTestDataFile = saveTestDataFile;
window.downloadTestDataFile = downloadTestDataFile;
window.validateTestData = validateTestData;
window.deleteTestDataFile = deleteTestDataFile;
window.refreshTestData = refreshTestData;
