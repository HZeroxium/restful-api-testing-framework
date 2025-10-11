# application/services/test_execution_service.py

import uuid
import time
from typing import List, Optional
from datetime import datetime

from domain.ports.execution_repository import ExecutionRepositoryInterface
from domain.ports.test_data_repository import TestDataRepositoryInterface
from schemas.core.execution_history import (
    ExecutionHistory,
    ExecutionStatus,
    TestCaseExecutionResult,
)
from schemas.core.test_data import TestData
from tools.core.test_executor import TestExecutorTool
from tools.core.test_data_verifier import TestDataVerifierTool
from tools.core.rest_api_caller import RestApiCallerTool
from tools.core.code_executor import CodeExecutorTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestExecutionService:
    """Service for managing test execution operations."""

    def __init__(
        self,
        execution_repository: ExecutionRepositoryInterface,
        test_data_repository: TestDataRepositoryInterface,
        verbose: bool = False,
    ):
        self.execution_repository = execution_repository
        self.test_data_repository = test_data_repository
        self.logger = LoggerFactory.get_logger(
            name="service.test_execution",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.DEBUG if verbose else LogLevel.INFO,
        )

        # Initialize tools
        self.test_executor = TestExecutorTool(verbose=verbose)
        self.test_data_verifier = TestDataVerifierTool(verbose=verbose)
        self.rest_api_caller = RestApiCallerTool(verbose=verbose)
        self.code_executor = CodeExecutorTool(verbose=verbose)

        # Import here to avoid circular imports
        from adapters.repository.json_file_execution_repository import (
            JsonFileExecutionRepository,
        )
        from adapters.repository.json_file_test_data_repository import (
            JsonFileTestDataRepository,
        )

        self.JsonFileExecutionRepository = JsonFileExecutionRepository
        self.JsonFileTestDataRepository = JsonFileTestDataRepository

    def _get_dataset_specific_repositories(self, dataset_id: str):
        """Get dataset-specific repositories."""
        execution_repo = self.JsonFileExecutionRepository(dataset_id=dataset_id)
        test_data_repo = self.JsonFileTestDataRepository(dataset_id=dataset_id)
        return execution_repo, test_data_repo

    async def execute_test_for_endpoint(
        self,
        endpoint_id: str,
        endpoint_name: str,
        base_url: str,
        dataset_id: Optional[str] = None,
        test_data_ids: Optional[List[str]] = None,
        timeout: int = 30,
    ) -> ExecutionHistory:
        """
        Execute tests for an endpoint.

        Args:
            endpoint_id: ID of the endpoint
            endpoint_name: Name of the endpoint
            base_url: Base URL for API calls
            test_data_ids: Optional list of specific test data IDs to use
            timeout: Request timeout in seconds

        Returns:
            ExecutionHistory with execution results
        """
        self.logger.info(
            f"Starting test execution for endpoint: {endpoint_name} ({endpoint_id})"
        )

        # Get dataset-specific repositories if dataset_id is provided
        if dataset_id:
            self.logger.info(
                f"Using dataset-specific repositories for dataset: {dataset_id}"
            )
            execution_repo, test_data_repo = self._get_dataset_specific_repositories(
                dataset_id
            )
        else:
            self.logger.warning(f"No dataset_id provided, using global repositories")
            execution_repo = self.execution_repository
            test_data_repo = self.test_data_repository

        # Create execution record
        execution_id = str(uuid.uuid4())
        execution = ExecutionHistory(
            id=execution_id,
            endpoint_id=endpoint_id,
            endpoint_name=endpoint_name,
            base_url=base_url,
            overall_status=ExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )

        # Save initial execution record
        await execution_repo.create(execution)

        try:
            # Get test data to execute
            if test_data_ids:
                test_data_items = []
                for test_data_id in test_data_ids:
                    test_data = await test_data_repo.get_by_id(test_data_id)
                    if test_data:
                        test_data_items.append(test_data)
            else:
                test_data_items = await test_data_repo.get_by_endpoint_id(endpoint_id)

            if not test_data_items:
                execution.overall_status = ExecutionStatus.FAILED
                execution.error_message = "No test data found for endpoint"
                execution.completed_at = datetime.now()
                await execution_repo.update(execution_id, execution)
                return execution

            execution.test_data_used = [item.id for item in test_data_items]
            execution.total_tests = len(test_data_items)

            self.logger.info(
                f"Executing {len(test_data_items)} test cases for endpoint: {endpoint_name}"
            )

            # Execute each test case
            execution_results = []
            total_execution_time = 0.0

            for test_data in test_data_items:
                test_result = await self._execute_single_test_case(
                    test_data, base_url, timeout
                )
                execution_results.append(test_result)
                total_execution_time += test_result.execution_time_ms

            # Update execution with results
            execution.execution_results = execution_results
            execution.total_execution_time_ms = total_execution_time
            execution.passed_tests = sum(
                1 for result in execution_results if result.passed
            )
            execution.failed_tests = execution.total_tests - execution.passed_tests
            execution.success_rate = (
                execution.passed_tests / execution.total_tests
                if execution.total_tests > 0
                else 0.0
            )
            execution.overall_status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now()

            # Save final execution record
            await execution_repo.update(execution_id, execution)

            self.logger.info(
                f"Test execution completed for endpoint {endpoint_name}: "
                f"{execution.passed_tests}/{execution.total_tests} passed "
                f"({execution.success_rate:.2%} success rate)"
            )

            return execution

        except Exception as e:
            self.logger.error(
                f"Test execution failed for endpoint {endpoint_name}: {e}"
            )
            execution.overall_status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            await execution_repo.update(execution_id, execution)
            return execution

    async def _execute_single_test_case(
        self, test_data: TestData, base_url: str, timeout: int
    ) -> TestCaseExecutionResult:
        """Execute a single test case."""
        start_time = time.time()

        try:
            # Build request URL
            if test_data.request_params:
                # Simple query string building (could be enhanced)
                query_params = "&".join(
                    [f"{k}={v}" for k, v in test_data.request_params.items()]
                )
                full_url = f"{base_url}?{query_params}"
            else:
                full_url = base_url

            # Prepare request
            from schemas.tools.rest_api_caller import RestApiCallerInput, RestRequest

            rest_request = RestRequest(
                method="GET",  # Default method, could be enhanced based on endpoint info
                url=full_url,
                headers=test_data.request_headers or {},
                json_body=test_data.request_body,
            )

            request_data = RestApiCallerInput(request=rest_request)

            # Make API call
            api_response = await self.rest_api_caller.execute(request_data)

            # Prepare response data
            response_data = {
                "status_code": api_response.get("status_code", 0),
                "headers": api_response.get("headers", {}),
                "body": api_response.get("body", {}),
                "text": api_response.get("text", ""),
                "json": api_response.get("json", {}),
            }

            # Simple validation (status code check)
            passed = response_data["status_code"] == test_data.expected_status_code

            execution_time_ms = (time.time() - start_time) * 1000

            return TestCaseExecutionResult(
                test_data_id=test_data.id,
                test_data_name=test_data.name,
                request_sent=rest_request.dict(),
                response_received=response_data,
                execution_status=ExecutionStatus.COMPLETED,
                validation_results=[],  # Could be enhanced with actual validation scripts
                execution_time_ms=execution_time_ms,
                error_message=None,
                passed=passed,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return TestCaseExecutionResult(
                test_data_id=test_data.id,
                test_data_name=test_data.name,
                request_sent={},
                response_received={},
                execution_status=ExecutionStatus.FAILED,
                validation_results=[],
                execution_time_ms=execution_time_ms,
                error_message=str(e),
                passed=False,
            )

    async def get_execution_history(
        self, endpoint_id: str, limit: int = 10
    ) -> List[ExecutionHistory]:
        """Get execution history for an endpoint."""
        self.logger.info(f"Retrieving execution history for endpoint: {endpoint_id}")
        return await self.execution_repository.get_by_endpoint_id(endpoint_id, limit)

    async def get_execution_by_id(
        self, execution_id: str
    ) -> Optional[ExecutionHistory]:
        """Get execution by ID."""
        self.logger.info(f"Retrieving execution: {execution_id}")
        return await self.execution_repository.get_by_id(execution_id)

    async def delete_execution(self, execution_id: str) -> bool:
        """Delete execution by ID."""
        self.logger.info(f"Deleting execution: {execution_id}")
        return await self.execution_repository.delete(execution_id)

    async def save_execution_result(
        self, execution: ExecutionHistory
    ) -> ExecutionHistory:
        """Save execution result."""
        self.logger.info(f"Saving execution result: {execution.id}")
        return await self.execution_repository.create(execution)

    async def get_all_execution_history(
        self, limit: int = 50, offset: int = 0
    ) -> List[ExecutionHistory]:
        """Get all execution history across all endpoints with pagination."""
        self.logger.info(
            f"Retrieving all execution history (limit={limit}, offset={offset})"
        )
        return await self.execution_repository.get_all(limit=limit, offset=offset)
