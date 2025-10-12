# application/services/test_data_service.py

import uuid
from typing import List, Optional, Tuple
from datetime import datetime

from domain.ports.test_data_repository import TestDataRepositoryInterface
from schemas.tools.test_data_generator import (
    TestDataGeneratorOutput,
    TestData,
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
            error_msg = f"No dataset_id found in endpoint_info for endpoint {endpoint_id}. Cannot generate test data without dataset context."
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info(f"Using dataset-specific repository for dataset: {dataset_id}")
        dataset_specific_repository = self._get_dataset_specific_repository(dataset_id)

        # If override_existing, delete existing test data first
        if override_existing:
            existing_test_data, _ = (
                await dataset_specific_repository.get_by_endpoint_id(endpoint_id)
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

        # Save generated test data directly (no conversion needed since schemas are now the same)
        saved_test_data = []
        for test_data in generator_output.test_data_collection:
            # Ensure endpoint_id is set correctly
            self.logger.debug(f"Before setting endpoint_id: {test_data.model_dump()}")
            test_data.endpoint_id = endpoint_id
            self.logger.debug(f"After setting endpoint_id: {test_data.model_dump()}")

            saved_test_data.append(await dataset_specific_repository.create(test_data))

        self.logger.info(
            f"Generated and saved {len(saved_test_data)} test data items for endpoint: {endpoint_id}"
        )

        # Return in the expected format
        return TestDataGeneratorOutput(test_data_collection=saved_test_data)

    async def get_test_data_by_endpoint_id(
        self, endpoint_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[TestData], int]:
        """Get all test data for an endpoint with pagination."""
        self.logger.info(f"Retrieving test data for endpoint: {endpoint_id}")
        return await self.test_data_repository.get_by_endpoint_id(
            endpoint_id, limit, offset
        )

    async def get_test_data_by_id(self, test_data_id: str) -> Optional[TestData]:
        """Get test data by ID."""
        self.logger.info(f"Retrieving test data: {test_data_id}")
        return await self.test_data_repository.get_by_id(test_data_id)

    async def save_test_data(self, test_data: TestData) -> TestData:
        """Save test data."""
        self.logger.info(f"Saving test data: {test_data.id}")
        return await self.test_data_repository.create(test_data)

    async def update_test_data(
        self, test_data_id: str, test_data: TestData
    ) -> Optional[TestData]:
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

    async def get_all_test_data(
        self, limit: int = 100, offset: int = 0
    ) -> Tuple[List[TestData], int]:
        """Get all test data across all endpoints with pagination."""
        self.logger.info(f"Retrieving all test data (limit={limit}, offset={offset})")
        return await self.test_data_repository.get_all(limit=limit, offset=offset)
