/**
 * Async Event Manager
 * Manages asynchronous operations, real-time updates, and event handling
 */

class AsyncEventManager {
  constructor() {
    this.activeOperations = new Map();
    this.eventListeners = new Map();
    this.pollingIntervals = new Map();
    this.notifications = [];
  }

  /**
   * Register an async operation
   */
  registerOperation(operationId, config = {}) {
    const operation = {
      id: operationId,
      status: "pending",
      progress: 0,
      startTime: Date.now(),
      config: {
        timeout: 300000, // 5 minutes default
        showProgress: true,
        showNotifications: true,
        ...config,
      },
    };

    this.activeOperations.set(operationId, operation);

    if (operation.config.showProgress) {
      this.showOperationProgress(operation);
    }

    return operation;
  }

  /**
   * Update operation status
   */
  updateOperation(operationId, updates) {
    const operation = this.activeOperations.get(operationId);
    if (!operation) return;

    Object.assign(operation, updates);

    if (operation.config.showProgress) {
      this.updateOperationProgress(operation);
    }

    // Emit events
    this.emit("operationUpdate", { operationId, operation, updates });

    // Auto-complete if progress reaches 100%
    if (operation.progress >= 100 && operation.status === "running") {
      this.completeOperation(operationId, { status: "completed" });
    }
  }

  /**
   * Complete an operation
   */
  completeOperation(operationId, result = {}) {
    const operation = this.activeOperations.get(operationId);
    if (!operation) return;

    operation.status = result.status || "completed";
    operation.endTime = Date.now();
    operation.duration = operation.endTime - operation.startTime;
    operation.result = result;

    if (operation.config.showProgress) {
      this.hideOperationProgress(operation);
    }

    if (operation.config.showNotifications) {
      const message = result.message || `Operation ${operation.status}`;
      const type =
        operation.status === "completed"
          ? "success"
          : operation.status === "failed"
          ? "danger"
          : "info";
      showNotification(message, type);
    }

    // Emit completion event
    this.emit("operationComplete", { operationId, operation, result });

    // Clean up
    setTimeout(() => {
      this.activeOperations.delete(operationId);
    }, 5000);
  }

  /**
   * Fail an operation
   */
  failOperation(operationId, error) {
    this.completeOperation(operationId, {
      status: "failed",
      error: error.message || error,
      message: `Operation failed: ${error.message || error}`,
    });
  }

  /**
   * Start polling for operation status
   */
  startPolling(operationId, pollFunction, interval = 2000) {
    if (this.pollingIntervals.has(operationId)) {
      this.stopPolling(operationId);
    }

    const intervalId = setInterval(async () => {
      try {
        const result = await pollFunction();

        if (result.completed || result.failed) {
          this.stopPolling(operationId);
          this.completeOperation(operationId, result);
        } else {
          this.updateOperation(operationId, result);
        }
      } catch (error) {
        this.stopPolling(operationId);
        this.failOperation(operationId, error);
      }
    }, interval);

    this.pollingIntervals.set(operationId, intervalId);

    // Auto-stop after timeout
    const operation = this.activeOperations.get(operationId);
    if (operation && operation.config.timeout) {
      setTimeout(() => {
        if (this.pollingIntervals.has(operationId)) {
          this.stopPolling(operationId);
          this.failOperation(operationId, new Error("Operation timeout"));
        }
      }, operation.config.timeout);
    }
  }

  /**
   * Stop polling for an operation
   */
  stopPolling(operationId) {
    const intervalId = this.pollingIntervals.get(operationId);
    if (intervalId) {
      clearInterval(intervalId);
      this.pollingIntervals.delete(operationId);
    }
  }

  /**
   * Show operation progress indicator
   */
  showOperationProgress(operation) {
    const progressId = `progress-${operation.id}`;

    // Remove existing progress if any
    const existing = document.getElementById(progressId);
    if (existing) {
      existing.remove();
    }

    const progressHtml = `
      <div class="toast-container position-fixed bottom-0 end-0 p-3" style="z-index: 1060;">
        <div id="${progressId}" class="toast show operation-progress-toast" role="alert">
          <div class="toast-header">
            <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
            <strong class="me-auto">Operation in Progress</strong>
            <button type="button" class="btn-close" onclick="asyncEventManager.cancelOperation('${operation.id}')"></button>
          </div>
          <div class="toast-body">
            <div class="operation-info mb-2">
              <small class="text-muted" id="${progressId}-description">Starting operation...</small>
            </div>
            <div class="progress" style="height: 6px;">
              <div class="progress-bar progress-bar-striped progress-bar-animated" 
                   id="${progressId}-bar"
                   role="progressbar" 
                   style="width: ${operation.progress}%"></div>
            </div>
            <div class="d-flex justify-content-between mt-2">
              <small class="text-muted" id="${progressId}-status">${operation.status}</small>
              <small class="text-muted" id="${progressId}-progress">${operation.progress}%</small>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", progressHtml);
  }

  /**
   * Update operation progress indicator
   */
  updateOperationProgress(operation) {
    const progressId = `progress-${operation.id}`;

    const bar = document.getElementById(`${progressId}-bar`);
    const status = document.getElementById(`${progressId}-status`);
    const progress = document.getElementById(`${progressId}-progress`);
    const description = document.getElementById(`${progressId}-description`);

    if (bar) bar.style.width = `${operation.progress}%`;
    if (status) status.textContent = operation.status;
    if (progress) progress.textContent = `${operation.progress}%`;
    if (description && operation.description)
      description.textContent = operation.description;
  }

  /**
   * Hide operation progress indicator
   */
  hideOperationProgress(operation) {
    const progressId = `progress-${operation.id}`;
    const progressElement = document.getElementById(progressId);

    if (progressElement) {
      // Fade out animation
      progressElement.classList.add("fade-out");
      setTimeout(() => {
        if (progressElement.parentNode) {
          progressElement.parentNode.removeChild(progressElement);
        }
      }, 500);
    }
  }

  /**
   * Cancel an operation
   */
  cancelOperation(operationId) {
    this.stopPolling(operationId);
    this.completeOperation(operationId, {
      status: "cancelled",
      message: "Operation cancelled by user",
    });
  }

  /**
   * Event system
   */
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);
  }

  off(event, callback) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach((callback) => {
        try {
          callback(data);
        } catch (error) {
          console.error("Event listener error:", error);
        }
      });
    }
  }

  /**
   * Batch operations manager
   */
  createBatch(batchId, operations = []) {
    const batch = {
      id: batchId,
      operations: operations,
      status: "pending",
      progress: 0,
      startTime: Date.now(),
    };

    this.registerOperation(batchId, {
      showProgress: true,
      showNotifications: false, // Will handle notifications at batch level
    });

    return batch;
  }

  async executeBatch(batch, executor) {
    this.updateOperation(batch.id, {
      status: "running",
      description: "Executing batch operations...",
    });

    try {
      for (let i = 0; i < batch.operations.length; i++) {
        const operation = batch.operations[i];
        const progress = Math.round(((i + 1) / batch.operations.length) * 100);

        this.updateOperation(batch.id, {
          progress: progress,
          description: `Processing ${
            operation.name || `operation ${i + 1}`
          }...`,
        });

        await executor(operation, i);
      }

      this.completeOperation(batch.id, {
        status: "completed",
        message: `Batch completed: ${batch.operations.length} operations processed`,
      });
    } catch (error) {
      this.failOperation(batch.id, error);
      throw error;
    }
  }

  /**
   * Real-time data synchronization
   */
  startRealTimeSync(syncId, syncFunction, interval = 5000) {
    this.startPolling(syncId, syncFunction, interval);
  }

  stopRealTimeSync(syncId) {
    this.stopPolling(syncId);
  }

  /**
   * File operation helpers
   */
  async trackFileUpload(file, uploadFunction, progressCallback) {
    const operationId = `upload-${Date.now()}`;

    this.registerOperation(operationId, {
      showProgress: true,
      description: `Uploading ${file.name}...`,
    });

    try {
      const result = await uploadFunction(file, (progress) => {
        this.updateOperation(operationId, { progress });
        if (progressCallback) progressCallback(progress);
      });

      this.completeOperation(operationId, {
        status: "completed",
        message: `File ${file.name} uploaded successfully`,
        result,
      });

      return result;
    } catch (error) {
      this.failOperation(operationId, error);
      throw error;
    }
  }

  /**
   * Test run tracking
   */
  trackTestRun(serviceId, runId) {
    const operationId = `test-run-${runId}`;

    this.registerOperation(operationId, {
      showProgress: true,
      description: "Starting test run...",
      timeout: 600000, // 10 minutes for test runs
    });

    this.startPolling(
      operationId,
      async () => {
        const response = await apiRequest(
          `/services/${serviceId}/runs/${runId}`
        );
        const run = response.data;

        const progress =
          run.status === "completed" || run.status === "failed"
            ? 100
            : run.status === "running"
            ? 50
            : 10;

        return {
          progress,
          status: run.status,
          description: `Test run ${run.status}...`,
          completed: run.status === "completed",
          failed: run.status === "failed",
          result: run,
        };
      },
      3000
    );

    return operationId;
  }

  /**
   * Get operation status
   */
  getOperation(operationId) {
    return this.activeOperations.get(operationId);
  }

  /**
   * Get all active operations
   */
  getActiveOperations() {
    return Array.from(this.activeOperations.values());
  }

  /**
   * Clear all operations
   */
  clearAll() {
    // Stop all polling
    this.pollingIntervals.forEach((intervalId, operationId) => {
      this.stopPolling(operationId);
    });

    // Clear all operations
    this.activeOperations.clear();

    // Remove all progress indicators
    document
      .querySelectorAll(".operation-progress-toast")
      .forEach((element) => {
        element.remove();
      });
  }
}

// Global instance
window.asyncEventManager = new AsyncEventManager();

// Add CSS for fade out animation
const style = document.createElement("style");
style.textContent = `
  .fade-out {
    opacity: 0;
    transition: opacity 0.5s ease-out;
  }
  
  .operation-progress-toast {
    min-width: 300px;
  }
  
  .cursor-pointer {
    cursor: pointer;
  }
  
  .recent-run-item:hover {
    background-color: #f8f9fa;
  }
  
  .service-header-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }
  
  .service-header-card .text-muted {
    color: rgba(255, 255, 255, 0.8) !important;
  }
  
  .service-stats {
    display: flex;
    gap: 1rem;
  }
  
  .stat-item {
    text-align: center;
  }
  
  .stat-value {
    display: block;
    font-size: 1.5rem;
    font-weight: bold;
  }
  
  .stat-label {
    display: block;
    font-size: 0.75rem;
    opacity: 0.8;
  }
  
  .overview-stat-card {
    transition: transform 0.2s ease-in-out;
  }
  
  .overview-stat-card:hover {
    transform: translateY(-2px);
  }
  
  .endpoint-card {
    transition: transform 0.2s ease-in-out;
  }
  
  .endpoint-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  }
  
  .health-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid #eee;
  }
  
  .health-item:last-child {
    border-bottom: none;
  }
  
  .test-case-details-row {
    background-color: #f8f9fa;
  }
  
  .service-tabs .nav-link {
    border: none;
    border-bottom: 3px solid transparent;
    background: none;
    color: #6c757d;
    font-weight: 500;
  }
  
  .service-tabs .nav-link.active {
    background: none;
    border-bottom-color: #0d6efd;
    color: #0d6efd;
  }
  
  .service-tabs .nav-link:hover {
    border-bottom-color: #dee2e6;
    color: #495057;
  }
`;
document.head.appendChild(style);
