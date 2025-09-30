/**
 * Services Management Module
 * Handles service CRUD operations and OpenAPI spec management
 */

/**
 * Load and display services list
 */
async function loadServices() {
  showLoading("services-list");

  try {
    const response = await apiRequest("/services");
    const servicesData = response.data || [];

    if (servicesData.length === 0) {
      showEmpty(
        "services-list",
        "No services found",
        '<div class="mt-2"><button class="btn btn-primary btn-sm" onclick="showCreateServiceModal()"><i class="fas fa-plus me-1"></i>Create First Service</button></div>'
      );
      return;
    }

    displayServicesTable(servicesData);
  } catch (error) {
    showError("services-list", "Failed to load services");
  }
}

/**
 * Display services in a table format
 */
function displayServicesTable(services) {
  const container = document.getElementById("services-list");

  const table = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Service Name</th>
                    <th>Status</th>
                    <th>Endpoints</th>
                    <th>Test Cases</th>
                    <th>Test Data</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${services
                  .map(
                    (service) => `
                    <tr>
                        <td>
                            <div>
                                <strong>${escapeHtml(service.name)}</strong>
                                <br>
                                <small class="text-muted">${service.id}</small>
                            </div>
                        </td>
                        <td>
                            <span class="badge ${getStatusBadgeClass(
                              service.status
                            )}">${service.status}</span>
                        </td>
                        <td>
                            <span class="badge bg-primary">${
                              service.endpoints_count
                            }</span>
                        </td>
                        <td>
                            <span class="badge bg-success">${
                              service.test_cases_count
                            }</span>
                        </td>
                        <td>
                            <span class="badge bg-info">${
                              service.test_data_count
                            }</span>
                        </td>
                        <td>
                            <small>${formatDate(service.created_at)}</small>
                        </td>
                        <td>
                            <div class="btn-group" role="group">
                                <button class="btn btn-sm btn-outline-primary" onclick="viewServiceDetails('${
                                  service.id
                                }')" title="View Details">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="viewServiceEndpoints('${
                                  service.id
                                }')" title="View Endpoints">
                                    <i class="fas fa-list"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-warning" onclick="editServiceSpec('${
                                  service.id
                                }')" title="Edit Spec">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteService('${
                                  service.id
                                }', '${escapeHtml(
                      service.name
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
    `;

  container.innerHTML = table;
}

/**
 * Show create service modal
 */
function showCreateServiceModal() {
  // Reset form
  document.getElementById("createServiceForm").reset();
  document.getElementById("specSourceType").value = "upload";
  handleSpecSourceChange();

  showModal("createServiceModal");
}

/**
 * Handle spec source type change
 */
function handleSpecSourceChange() {
  const sourceType = document.getElementById("specSourceType").value;

  // Hide all divs
  document.getElementById("uploadSpecDiv").style.display = "none";
  document.getElementById("existingSpecDiv").style.display = "none";
  document.getElementById("urlSpecDiv").style.display = "none";

  // Show relevant div
  switch (sourceType) {
    case "upload":
      document.getElementById("uploadSpecDiv").style.display = "block";
      break;
    case "existing":
      document.getElementById("existingSpecDiv").style.display = "block";
      break;
    case "url":
      document.getElementById("urlSpecDiv").style.display = "block";
      break;
  }
}

/**
 * Create new service
 */
async function createService() {
  try {
    const form = document.getElementById("createServiceForm");
    const formData = new FormData(form);

    const serviceName = document.getElementById("serviceName").value.trim();
    const sourceType = document.getElementById("specSourceType").value;
    const rebuildOdg = document.getElementById("rebuildOdg").checked;

    if (!serviceName) {
      showNotification("Please enter a service name", "warning");
      return;
    }

    let pathOrUrl = "";

    // Handle different source types
    if (sourceType === "upload") {
      const fileInput = document.getElementById("specFile");
      if (!fileInput.files[0]) {
        showNotification("Please select a file to upload", "warning");
        return;
      }

      // First upload the file
      pathOrUrl = await uploadSpecFile(fileInput.files[0]);
    } else if (sourceType === "existing") {
      pathOrUrl = document.getElementById("existingSpecPath").value.trim();
      if (!pathOrUrl) {
        showNotification(
          "Please enter the path to existing spec file",
          "warning"
        );
        return;
      }
    } else if (sourceType === "url") {
      pathOrUrl = document.getElementById("specUrl").value.trim();
      if (!pathOrUrl) {
        showNotification("Please enter the spec URL", "warning");
        return;
      }
    }

    // Create service
    const serviceData = {
      service_name: serviceName,
      swagger_source: {
        type: sourceType,
        path_or_url: pathOrUrl,
      },
      rebuild_odg: rebuildOdg,
    };

    const response = await apiRequest("/services", {
      method: "POST",
      body: JSON.stringify(serviceData),
    });

    showNotification("Service created successfully!", "success");
    hideModal("createServiceModal");
    loadServices(); // Refresh services list
  } catch (error) {
    showNotification("Failed to create service: " + error.message, "danger");
  }
}

/**
 * Upload spec file
 */
async function uploadSpecFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE_URL}/services/upload-spec`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to upload file");
    }

    return data.data.file_path;
  } catch (error) {
    console.error("File upload failed:", error);
    throw error;
  }
}

/**
 * View service details
 */
async function viewServiceDetails(serviceId) {
  try {
    const response = await apiRequest(`/services/${serviceId}`);
    const service = response.data;

    // Create modal dynamically
    const modalHtml = `
            <div class="modal fade" id="serviceDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Service Details: ${escapeHtml(
                              service.name
                            )}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Basic Information</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>ID:</strong></td><td>${
                                          service.id
                                        }</td></tr>
                                        <tr><td><strong>Name:</strong></td><td>${escapeHtml(
                                          service.name
                                        )}</td></tr>
                                        <tr><td><strong>Status:</strong></td><td><span class="badge ${getStatusBadgeClass(
                                          service.status
                                        )}">${service.status}</span></td></tr>
                                        <tr><td><strong>Created:</strong></td><td>${formatDate(
                                          service.created_at
                                        )}</td></tr>
                                        <tr><td><strong>Updated:</strong></td><td>${formatDate(
                                          service.updated_at
                                        )}</td></tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>Statistics</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>Endpoints:</strong></td><td><span class="badge bg-primary">${
                                          service.endpoints_count
                                        }</span></td></tr>
                                        <tr><td><strong>Test Cases:</strong></td><td><span class="badge bg-success">${
                                          service.test_cases_count
                                        }</span></td></tr>
                                        <tr><td><strong>Test Data:</strong></td><td><span class="badge bg-info">${
                                          service.test_data_count
                                        }</span></td></tr>
                                    </table>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>File Paths</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>Spec File:</strong></td><td><code>${
                                          service.spec_path
                                        }</code></td></tr>
                                        <tr><td><strong>Working Directory:</strong></td><td><code>${
                                          service.working_dir
                                        }</code></td></tr>
                                        <tr><td><strong>Spec Source:</strong></td><td>${
                                          service.spec_source
                                        }</td></tr>
                                    </table>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-primary" onclick="viewServiceEndpoints('${
                              service.id
                            }')">
                                <i class="fas fa-list me-2"></i>View Endpoints
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("serviceDetailsModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("serviceDetailsModal");
  } catch (error) {
    showNotification(
      "Failed to load service details: " + error.message,
      "danger"
    );
  }
}

/**
 * View service endpoints
 */
async function viewServiceEndpoints(serviceId) {
  try {
    const response = await apiRequest(`/services/${serviceId}/endpoints`);
    const endpoints = response.data || [];

    // Create modal dynamically
    const modalHtml = `
            <div class="modal fade" id="serviceEndpointsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Service Endpoints</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${
                              endpoints.length === 0
                                ? '<div class="text-center text-muted py-4"><i class="fas fa-inbox me-2"></i>No endpoints found</div>'
                                : `<div class="list-group">
                                    ${endpoints
                                      .map(
                                        (endpoint) => `
                                        <div class="list-group-item">
                                            <div class="d-flex justify-content-between align-items-center">
                                                <div>
                                                    <span class="endpoint-method ${getMethodBadgeClass(
                                                      endpoint.method
                                                    )}">${
                                          endpoint.method
                                        }</span>
                                                    <code>${
                                                      endpoint.path
                                                    }</code>
                                                </div>
                                                <div>
                                                    <small class="text-muted">${
                                                      endpoint.operation_id
                                                    }</small>
                                                </div>
                                            </div>
                                            ${
                                              endpoint.summary
                                                ? `<small class="text-muted">${escapeHtml(
                                                    endpoint.summary
                                                  )}</small>`
                                                : ""
                                            }
                                        </div>
                                    `
                                      )
                                      .join("")}
                                </div>`
                            }
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("serviceEndpointsModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    showModal("serviceEndpointsModal");
  } catch (error) {
    showNotification("Failed to load endpoints: " + error.message, "danger");
  }
}

/**
 * Edit service specification
 */
async function editServiceSpec(serviceId) {
  try {
    const response = await apiRequest(`/services/${serviceId}`);
    const service = response.data;

    // Create modal dynamically
    const modalHtml = `
            <div class="modal fade" id="editSpecModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit OpenAPI Specification: ${escapeHtml(
                              service.name
                            )}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">OpenAPI Specification (JSON)</label>
                                <textarea class="form-control" id="specContent" rows="20" style="font-family: monospace;"></textarea>
                            </div>
                            <div class="mb-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="rebuildOdgEdit" checked>
                                    <label class="form-check-label" for="rebuildOdgEdit">
                                        Rebuild Operation Dependency Graph (ODG)
                                    </label>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="updateServiceSpec('${serviceId}')">
                                <i class="fas fa-save me-2"></i>Update Specification
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if any
    const existingModal = document.getElementById("editSpecModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);

    // Load current spec content
    try {
      const specResponse = await fetch(service.spec_path);
      const specContent = await specResponse.text();

      // Try to format JSON
      try {
        const parsed = JSON.parse(specContent);
        document.getElementById("specContent").value = JSON.stringify(
          parsed,
          null,
          2
        );
      } catch {
        document.getElementById("specContent").value = specContent;
      }
    } catch {
      document.getElementById("specContent").value =
        "// Unable to load current specification";
    }

    showModal("editSpecModal");
  } catch (error) {
    showNotification(
      "Failed to load service for editing: " + error.message,
      "danger"
    );
  }
}

/**
 * Update service specification
 */
async function updateServiceSpec(serviceId) {
  try {
    const specContent = document.getElementById("specContent").value.trim();
    const rebuildOdg = document.getElementById("rebuildOdgEdit").checked;

    if (!specContent) {
      showNotification("Please enter the specification content", "warning");
      return;
    }

    // Validate JSON
    try {
      JSON.parse(specContent);
    } catch (error) {
      showNotification(
        "Invalid JSON specification: " + error.message,
        "warning"
      );
      return;
    }

    const updateData = {
      spec_content: specContent,
      rebuild_odg: rebuildOdg,
    };

    await apiRequest(`/services/${serviceId}/spec`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });

    showNotification("Service specification updated successfully!", "success");
    hideModal("editSpecModal");
    loadServices(); // Refresh services list
  } catch (error) {
    showNotification(
      "Failed to update specification: " + error.message,
      "danger"
    );
  }
}

/**
 * Delete service
 */
async function deleteService(serviceId, serviceName) {
  if (
    !confirm(
      `Are you sure you want to delete the service "${serviceName}"?\n\nThis will permanently delete all associated test cases, test data, and results.`
    )
  ) {
    return;
  }

  try {
    await apiRequest(`/services/${serviceId}`, {
      method: "DELETE",
    });

    showNotification("Service deleted successfully!", "success");
    loadServices(); // Refresh services list
  } catch (error) {
    showNotification("Failed to delete service: " + error.message, "danger");
  }
}

// Export functions for global access
window.loadServices = loadServices;
window.showCreateServiceModal = showCreateServiceModal;
window.handleSpecSourceChange = handleSpecSourceChange;
window.createService = createService;
window.viewServiceDetails = viewServiceDetails;
window.viewServiceEndpoints = viewServiceEndpoints;
window.editServiceSpec = editServiceSpec;
window.updateServiceSpec = updateServiceSpec;
window.deleteService = deleteService;
