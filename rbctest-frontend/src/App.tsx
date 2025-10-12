import React, { Suspense } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "@/app/store";
import AppLayout from "@/components/layout/AppLayout";
import LoadingOverlay from "@/components/common/LoadingOverlay";
import ErrorBoundary from "@/components/common/ErrorBoundary";

// Lazy load components for code splitting
const Dashboard = React.lazy(() => import("@/features/dashboard/Dashboard"));

// Placeholder components for other routes (to be implemented)
const DatasetsPage = React.lazy(
  () => import("@/features/datasets/DatasetsPage")
);
const DatasetDetailPage = React.lazy(
  () => import("@/features/datasets/DatasetDetailPage")
);
const UploadSpecPage = React.lazy(
  () => import("@/features/datasets/UploadSpecPage")
);
const EndpointsPage = React.lazy(
  () => import("@/features/endpoints/EndpointsPage")
);
const EndpointDetailPage = React.lazy(
  () => import("@/features/endpoints/EndpointDetailPage")
);
const ConstraintsPage = React.lazy(
  () => import("@/features/constraints/ConstraintsPage")
);
const ValidationScriptsPage = React.lazy(
  () => import("@/features/validation-scripts/ValidationScriptsPage")
);
const TestDataPage = React.lazy(
  () => import("@/features/test-data/TestDataPage")
);
const ExecutionsPage = React.lazy(
  () => import("@/features/execution/ExecutionsPage")
);
const ExecutionDetailPage = React.lazy(
  () => import("@/features/execution/ExecutionDetailPage")
);
const VerificationPage = React.lazy(
  () => import("@/features/verification/VerificationPage")
);
const BatchOperationsPage = React.lazy(
  () => import("@/features/batch/BatchOperationsPage")
);
const NotFoundPage = React.lazy(() => import("@/pages/NotFoundPage"));

// Loading component for Suspense
const LoadingFallback = () => (
  <LoadingOverlay open={true} message="Loading page..." />
);

function App() {
  return (
    <Provider store={store}>
      <ErrorBoundary>
        <Router>
          <Suspense fallback={<LoadingFallback />}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Dashboard />} />
                <Route path="datasets" element={<DatasetsPage />} />
                <Route path="datasets/:id" element={<DatasetDetailPage />} />
                <Route path="datasets/upload" element={<UploadSpecPage />} />
                <Route path="endpoints" element={<EndpointsPage />} />
                <Route path="endpoints/:id" element={<EndpointDetailPage />} />
                <Route path="constraints" element={<ConstraintsPage />} />
                <Route
                  path="validation-scripts"
                  element={<ValidationScriptsPage />}
                />
                <Route path="test-data" element={<TestDataPage />} />
                <Route path="executions" element={<ExecutionsPage />} />
                <Route
                  path="executions/:id"
                  element={<ExecutionDetailPage />}
                />
                <Route path="verification" element={<VerificationPage />} />
                <Route
                  path="batch-operations"
                  element={<BatchOperationsPage />}
                />
              </Route>
              {/* Catch-all route for 404 */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </Router>
      </ErrorBoundary>
    </Provider>
  );
}

export default App;
