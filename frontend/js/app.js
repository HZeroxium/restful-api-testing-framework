/**
 * RESTful API Testing Framework Frontend
 * Main application JavaScript file
 */

// Configuration
const API_BASE_URL = "http://localhost:8000/api/v1";
const POLLING_INTERVAL = 5000; // 5 seconds

// Global state
let currentView = "dashboard";
let currentService = null;
let services = [];
let refreshInterval = null;

// Initialize application
document.addEventListener("DOMContentLoaded", function () {
  console.log("RESTful API Testing Framework - Frontend Initialized");

  // Check backend connection
  checkBackendHealth();

  // Load initial data
  loadDashboard();

  // Setup periodic refresh for active data
  setupPeriodicRefresh();

  // Setup event listeners
  setupEventListeners();
});

/**
 * API Helper Functions
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const config = { ...defaultOptions, ...options };

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP error! status: ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error("API Request failed:", error);
    showNotification("Error: " + error.message, "danger");
    throw error;
  }
}

/**
 * Health Check
 */
async function checkBackendHealth() {
  try {
    const response = await apiRequest("/healthz");
    updateConnectionStatus(true, response.status);
  } catch (error) {
    updateConnectionStatus(false, "Disconnected");
  }
}

function updateConnectionStatus(connected, status) {
  const indicator = document.getElementById("status-indicator");
  if (connected) {
    indicator.innerHTML =
      '<i class="fas fa-circle text-success me-1"></i>Connected';
  } else {
    indicator.innerHTML =
      '<i class="fas fa-circle text-danger me-1"></i>Disconnected';
  }
}

/**
 * Navigation Functions
 */
function showView(viewName) {
  // Hide all views
  document.querySelectorAll(".content-view").forEach((view) => {
    view.style.display = "none";
  });

  // Show selected view
  const selectedView = document.getElementById(`${viewName}-view`);
  if (selectedView) {
    selectedView.style.display = "block";
    currentView = viewName;
  }

  // Update navigation
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.remove("active");
  });
}

function showDashboard() {
  showView("dashboard");
  hideServiceBreadcrumb();
  currentService = null;
  loadDashboard();
}

// This function will be overridden by service-detail.js
// We don't need to define it here

// Fallback functions for service operations (will be overridden by service-detail.js)
function runQuickTest(serviceId) {
  console.warn("runQuickTest called before service-detail.js is loaded");
  if (window.runQuickTest && window.runQuickTest !== arguments.callee) {
    window.runQuickTest(serviceId);
  }
}

function editServiceSpec(serviceId) {
  console.warn("editServiceSpec called before service-detail.js is loaded");
  if (window.editServiceSpec && window.editServiceSpec !== arguments.callee) {
    window.editServiceSpec(serviceId);
  }
}

/**
 * Dashboard Functions
 */
async function loadDashboard() {
  try {
    // Load services for stats
    const servicesResponse = await apiRequest("/services");
    const servicesData = servicesResponse.data || [];

    // Update stats
    updateDashboardStats(servicesData);

    // Load services grid
    loadServicesGrid(servicesData);

    // Load system status
    loadSystemStatus();
  } catch (error) {
    console.error("Failed to load dashboard:", error);
  }
}

function updateDashboardStats(servicesData) {
  const totalServices = servicesData.length;
  const totalTestCases = servicesData.reduce(
    (sum, service) => sum + (service.test_cases_count || 0),
    0
  );
  const totalTestRuns = servicesData.reduce(
    (sum, service) => sum + (service.test_runs_count || 0),
    0
  );

  // Update stats with null checks
  const statsServices = document.getElementById("stats-services");
  const statsTestCases = document.getElementById("stats-test-cases");
  const statsTestRuns = document.getElementById("stats-test-runs");
  const statsSuccessRate = document.getElementById("stats-success-rate");

  if (statsServices) statsServices.textContent = totalServices;
  if (statsTestCases) statsTestCases.textContent = totalTestCases;
  if (statsTestRuns) statsTestRuns.textContent = totalTestRuns;
  if (statsSuccessRate) statsSuccessRate.textContent = "95%"; // Placeholder
}

function loadServicesGrid(servicesData) {
  const container = document.getElementById("services-grid");

  if (servicesData.length === 0) {
    container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-server fa-3x mb-3"></i>
                <h5>No Services Found</h5>
                <p>Create your first service to start testing APIs.</p>
                <button class="btn btn-primary" onclick="showCreateServiceModal()">
                    <i class="fas fa-plus me-2"></i>Create First Service
                </button>
            </div>
        `;
    return;
  }

  // Create service cards grid
  const servicesGrid = servicesData
    .map(
      (service) => `
    <div class="col-md-4 mb-4">
      <div class="card service-card h-100 cursor-pointer" onclick="showServiceDetail('${
        service.id
      }')">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-3">
            <div class="service-icon">
              <i class="fas fa-server fa-2x text-primary"></i>
            </div>
            <span class="badge ${getStatusBadgeClass(service.status)}">${
        service.status
      }</span>
          </div>
          
          <h5 class="card-title">${escapeHtml(service.name)}</h5>
          <p class="card-text text-muted small">
            Updated ${formatDate(service.updated_at)}
          </p>
          
          <div class="service-stats-mini">
            <div class="row text-center">
              <div class="col-4">
                <small class="stat-value">${service.endpoints_count}</small>
                <small class="stat-label d-block text-muted">Endpoints</small>
              </div>
              <div class="col-4">
                <small class="stat-value">${service.test_cases_count}</small>
                <small class="stat-label d-block text-muted">Test Cases</small>
              </div>
              <div class="col-4">
                <small class="stat-value">${
                  service.test_runs_count || 0
                }</small>
                <small class="stat-label d-block text-muted">Runs</small>
              </div>
            </div>
          </div>
        </div>
        
        <div class="card-footer bg-transparent">
          <div class="d-flex justify-content-between align-items-center">
            <small class="text-muted">
              <i class="fas fa-file-code me-1"></i>${
                service.test_data_count || 0
              } data files
            </small>
            <div class="service-actions-mini">
              <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); editServiceSpec('${
                service.id
              }')" title="Edit Spec">
                <i class="fas fa-edit"></i>
              </button>
              <button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation(); runQuickTest('${
                service.id
              }')" title="Quick Test">
                <i class="fas fa-play"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
    )
    .join("");

  container.innerHTML = `<div class="row">${servicesGrid}</div>`;
}

async function loadSystemStatus() {
  try {
    const healthResponse = await apiRequest("/healthz");
    const versionResponse = await apiRequest("/version");

    const container = document.getElementById("system-status");
    container.innerHTML = `
            <div class="mb-2">
                <strong>Status:</strong> 
                <span class="status-indicator status-active">${
                  healthResponse.status
                }</span>
            </div>
            <div class="mb-2">
                <strong>Version:</strong> ${
                  versionResponse.data?.version || "Unknown"
                }
            </div>
            <div class="mb-2">
                <strong>Uptime:</strong> ${formatUptime(
                  healthResponse.timestamp
                )}
            </div>
        `;
  } catch (error) {
    document.getElementById("system-status").innerHTML = `
            <div class="text-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Unable to load system status
            </div>
        `;
  }
}

/**
 * Service Selector Functions
 */
async function loadServiceSelectors() {
  try {
    const response = await apiRequest("/services");
    const servicesData = response.data || [];
    services = servicesData;

    // Update all service selectors
    const selectors = [
      "service-selector-test-cases",
      "service-selector-test-data",
      "service-selector-test-runs",
    ];

    selectors.forEach((selectorId) => {
      const selector = document.getElementById(selectorId);
      if (selector) {
        selector.innerHTML =
          '<option value="">Select Service</option>' +
          servicesData
            .map(
              (service) =>
                `<option value="${service.id}">${escapeHtml(
                  service.name
                )}</option>`
            )
            .join("");

        // Add change event listener
        selector.addEventListener("change", function () {
          handleServiceSelection(this.value, selectorId);
        });
      }
    });
  } catch (error) {
    console.error("Failed to load services:", error);
  }
}

function handleServiceSelection(serviceId, selectorId) {
  currentService = serviceId;

  // Enable/disable related buttons
  const buttonMappings = {
    "service-selector-test-cases": "generate-test-cases-btn",
    "service-selector-test-data": "generate-test-data-btn",
    "service-selector-test-runs": "create-run-btn",
  };

  const buttonId = buttonMappings[selectorId];
  if (buttonId) {
    const button = document.getElementById(buttonId);
    if (button) {
      button.disabled = !serviceId;
    }
  }

  // Load content based on view
  if (selectorId === "service-selector-test-cases") {
    loadTestCasesForService(serviceId);
  } else if (selectorId === "service-selector-test-data") {
    loadTestDataForService(serviceId);
  } else if (selectorId === "service-selector-test-runs") {
    loadTestRunsForService(serviceId);
  }
}

/**
 * Notification System
 */
function showNotification(message, type = "info", duration = 5000) {
  const notification = document.createElement("div");
  notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  notification.style.cssText =
    "top: 20px; right: 20px; z-index: 1050; min-width: 300px;";

  notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

  document.body.appendChild(notification);

  // Auto remove after duration
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, duration);
}

/**
 * Modal Functions
 */
function showModal(modalId) {
  const modal = new bootstrap.Modal(document.getElementById(modalId));
  modal.show();
}

function hideModal(modalId) {
  const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
  if (modal) {
    modal.hide();
  }
}

/**
 * Utility Functions
 */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(dateString) {
  try {
    return new Date(dateString).toLocaleString();
  } catch {
    return dateString;
  }
}

function formatUptime(timestamp) {
  try {
    const now = new Date();
    const start = new Date(timestamp);
    const diff = now - start;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  } catch {
    return "Unknown";
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function getStatusBadgeClass(status) {
  const statusMap = {
    active: "bg-success",
    pending: "bg-warning",
    running: "bg-info",
    completed: "bg-success",
    failed: "bg-danger",
    cancelled: "bg-secondary",
  };
  return statusMap[status] || "bg-secondary";
}

function getMethodBadgeClass(method) {
  const methodMap = {
    GET: "method-get",
    POST: "method-post",
    PUT: "method-put",
    PATCH: "method-patch",
    DELETE: "method-delete",
  };
  return methodMap[method.toUpperCase()] || "method-get";
}

/**
 * Periodic Refresh
 */
function setupPeriodicRefresh() {
  refreshInterval = setInterval(() => {
    // Only refresh if on dashboard or if viewing active runs
    if (currentView === "dashboard") {
      loadDashboard();
    } else if (currentView === "test-runs" && currentService) {
      loadTestRunsForService(currentService);
    }
  }, POLLING_INTERVAL);
}

/**
 * Event Listeners
 */
function setupEventListeners() {
  // Handle browser back/forward buttons
  window.addEventListener("popstate", function (event) {
    if (event.state && event.state.view) {
      showView(event.state.view);
    }
  });

  // Handle window focus to refresh data
  window.addEventListener("focus", function () {
    checkBackendHealth();
    if (currentView === "dashboard") {
      loadDashboard();
    }
  });

  // Handle form submissions
  document.addEventListener("submit", function (event) {
    event.preventDefault();
  });
}

/**
 * Loading States
 */
function showLoading(containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-spinner fa-spin me-2"></i>Loading...
            </div>
        `;
  }
}

function showError(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `
            <div class="text-center text-danger py-4">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${escapeHtml(message)}
            </div>
        `;
  }
}

function showEmpty(containerId, message, actionButton = null) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-inbox me-2"></i>
                ${escapeHtml(message)}
                ${actionButton || ""}
            </div>
        `;
  }
}

// Export functions for global access
window.showDashboard = showDashboard;
window.showNotification = showNotification;
window.showModal = showModal;
window.hideModal = hideModal;
window.apiRequest = apiRequest;
