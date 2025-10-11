# application/services/test_data_service.py

import uuid
from typing import List, Optional
from datetime import datetime

from domain.ports.test_data_repository import TestDataRepositoryInterface
from schemas.core.test_data import TestData as CoreTestData, TestDataCollection
from schemas.tools.test_data_generator import (
    TestDataGeneratorOutput,
    TestData as ToolsTestData,
)
from tools.llm.test_data_generator import TestDataGeneratorTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestDataService:
    """Service for managing test data operations."""

    def __init__(
        self, test_data_repository: TestDataRepositoryInterface, verbose: bool = False
    ):
        self.test_data_repository = test_data_repository
        self.logger = LoggerFactory.get_logger(
            name="service.test_data",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.DEBUG if verbose else LogLevel.INFO,
        )

        # Initialize test data generator tool
        self.test_data_generator = TestDataGeneratorTool(verbose=verbose)

        # Import here to avoid circular imports
        from adapters.repository.json_file_test_data_repository import (
            JsonFileTestDataRepository,
        )

        self.JsonFileTestDataRepository = JsonFileTestDataRepository

    def _get_dataset_specific_repository(
        self, dataset_id: str
    ) -> TestDataRepositoryInterface:
        """Get a dataset-specific test data repository."""
        return self.JsonFileTestDataRepository(dataset_id=dataset_id)

    async def generate_test_data_for_endpoint(
        self,
        endpoint_id: str,
        endpoint_info: dict,
        count: int = 5,
        include_invalid: bool = True,
        override_existing: bool = True,
    ) -> TestDataGeneratorOutput:
        """
        Generate test data for an endpoint.

        Args:
            endpoint_id: ID of the endpoint
            endpoint_info: Endpoint information for generation
            count: Number of test data items to generate
            include_invalid: Whether to include invalid test data
            override_existing: Whether to delete existing test data first

        Returns:
            TestDataGeneratorOutput with generated test data
        """
        self.logger.info(
            f"Generating {count} test data items for endpoint: {endpoint_id}"
        )

        # Get dataset_id from endpoint_info
        dataset_id = endpoint_info.get("dataset_id")
        if not dataset_id:
            self.logger.warning(
                f"No dataset_id found in endpoint_info for endpoint {endpoint_id}"
            )
            # Fall back to global repository
            dataset_specific_repository = self.test_data_repository
        else:
            self.logger.info(
                f"Using dataset-specific repository for dataset: {dataset_id}"
            )
            dataset_specific_repository = self._get_dataset_specific_repository(
                dataset_id
            )

        # If override_existing, delete existing test data first
        if override_existing:
            existing_test_data = await dataset_specific_repository.get_by_endpoint_id(
                endpoint_id
            )
            if existing_test_data:
                deleted_count = await dataset_specific_repository.delete_by_endpoint_id(
                    endpoint_id
                )
                self.logger.info(
                    f"Deleted {deleted_count} existing test data items for endpoint {endpoint_id}"
                )
            else:
                self.logger.info(
                    f"No existing test data found for endpoint {endpoint_id}"
                )

        # Generate test data using the tool
        from schemas.tools.test_data_generator import TestDataGeneratorInput

        generator_input = TestDataGeneratorInput(
            endpoint_info=endpoint_info,
            test_case_count=count,
            include_invalid_data=include_invalid,
        )

        generator_output: TestDataGeneratorOutput = (
            await self.test_data_generator.execute(generator_input)
        )

        # Convert and save generated test data
        saved_test_data = []
        for test_data in generator_output.test_data_collection:
            # Convert to core TestData format and add endpoint_id
            core_test_data = CoreTestData(
                id=str(uuid.uuid4()),
                endpoint_id=endpoint_id,
                name=test_data.name,
                description=test_data.description,
                request_params=test_data.request_params,
                request_headers=test_data.request_headers,
                request_body=test_data.request_body,
                expected_status_code=test_data.expected_status_code,
                expected_response_schema=test_data.expected_response_schema,
                expected_response_contains=test_data.expected_response_contains,
                is_valid=test_data.expected_status_code < 400,  # Simple validity check
            )

            saved_test_data.append(
                await dataset_specific_repository.create(core_test_data)
            )

        self.logger.info(
            f"Generated and saved {len(saved_test_data)} test data items for endpoint: {endpoint_id}"
        )

        # Convert CoreTestData back to ToolsTestData for the output
        tools_test_data = []
        for core_test_data in saved_test_data:
            tools_test_data.append(
                ToolsTestData(
                    id=core_test_data.id,
                    name=core_test_data.name,
                    description=core_test_data.description,
                    request_params=core_test_data.request_params,
                    request_headers=core_test_data.request_headers,
                    request_body=core_test_data.request_body,
                    expected_status_code=core_test_data.expected_status_code,
                    expected_response_schema=core_test_data.expected_response_schema,
                    expected_response_contains=core_test_data.expected_response_contains,
                )
            )

        # Return in the expected format
        return TestDataGeneratorOutput(test_data_collection=tools_test_data)

    async def get_test_data_by_endpoint_id(
        self, endpoint_id: str
    ) -> List[CoreTestData]:
        """Get all test data for an endpoint."""
        self.logger.info(f"Retrieving test data for endpoint: {endpoint_id}")
        return await self.test_data_repository.get_by_endpoint_id(endpoint_id)

    async def get_test_data_by_id(self, test_data_id: str) -> Optional[CoreTestData]:
        """Get test data by ID."""
        self.logger.info(f"Retrieving test data: {test_data_id}")
        return await self.test_data_repository.get_by_id(test_data_id)

    async def save_test_data(self, test_data: CoreTestData) -> CoreTestData:
        """Save test data."""
        self.logger.info(f"Saving test data: {test_data.id}")
        return await self.test_data_repository.create(test_data)

    async def update_test_data(
        self, test_data_id: str, test_data: CoreTestData
    ) -> Optional[CoreTestData]:
        """Update test data."""
        self.logger.info(f"Updating test data: {test_data_id}")
        test_data.updated_at = datetime.now()
        return await self.test_data_repository.update(test_data_id, test_data)

    async def delete_test_data(self, test_data_id: str) -> bool:
        """Delete test data by ID."""
        self.logger.info(f"Deleting test data: {test_data_id}")
        return await self.test_data_repository.delete(test_data_id)

    async def delete_test_data_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all test data for an endpoint."""
        self.logger.info(f"Deleting all test data for endpoint: {endpoint_id}")
        return await self.test_data_repository.delete_by_endpoint_id(endpoint_id)

    async def get_test_data_collection(
        self, endpoint_id: str, endpoint_name: str
    ) -> TestDataCollection:
        """Get test data collection for an endpoint."""
        test_data_items = await self.get_test_data_by_endpoint_id(endpoint_id)

        collection = TestDataCollection(
            endpoint_id=endpoint_id,
            endpoint_name=endpoint_name,
            test_data_items=test_data_items,
            total_count=len(test_data_items),
            valid_count=sum(1 for item in test_data_items if item.is_valid),
            invalid_count=sum(1 for item in test_data_items if not item.is_valid),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.logger.info(
            f"Created test data collection for endpoint {endpoint_name}: {collection.total_count} items ({collection.valid_count} valid, {collection.invalid_count} invalid)"
        )
        return collection

    async def get_all_test_data(
        self, limit: int = 100, offset: int = 0
    ) -> List[CoreTestData]:
        """Get all test data across all endpoints with pagination."""
        self.logger.info(f"Retrieving all test data (limit={limit}, offset={offset})")
        return await self.test_data_repository.get_all(limit=limit, offset=offset)
