# application/services/validation_script_service.py

from typing import List, Optional, Tuple
import uuid

from domain.ports.validation_script_repository import (
    ValidationScriptRepositoryInterface,
)
from domain.ports.constraint_repository import ConstraintRepositoryInterface
from domain.ports.endpoint_repository import EndpointRepositoryInterface
from schemas.tools.test_script_generator import (
    ValidationScript,
    TestScriptGeneratorInput,
    TestScriptGeneratorOutput,
)
from common.logger import LoggerFactory, LoggerType, LogLevel
from tools.llm.test_script_generator import TestScriptGeneratorTool


class ValidationScriptService:
    """Service for managing ValidationScript operations."""

    def __init__(
        self,
        script_repository: ValidationScriptRepositoryInterface,
        constraint_repository: ConstraintRepositoryInterface,
        endpoint_repository: EndpointRepositoryInterface,
    ):
        self.script_repository = script_repository
        self.constraint_repository = constraint_repository
        self.endpoint_repository = endpoint_repository
        self.logger = LoggerFactory.get_logger(
            name="service.validation_script",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

    async def create_script(self, script: ValidationScript) -> ValidationScript:
        """Create a new validation script."""
        if not script.id:
            script.id = str(uuid.uuid4())
        return await self.script_repository.create(script)

    async def get_script_by_id(self, script_id: str) -> Optional[ValidationScript]:
        """Get validation script by ID."""
        return await self.script_repository.get_by_id(script_id)

    async def get_scripts_by_endpoint_id(
        self, endpoint_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ValidationScript], int]:
        """Get all validation scripts for a specific endpoint with pagination."""
        return await self.script_repository.get_by_endpoint_id(
            endpoint_id, limit, offset
        )

    async def get_validation_scripts_by_endpoint_name(
        self, endpoint_name: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ValidationScript], int]:
        """Get validation scripts for a specific endpoint by name with pagination."""
        # Get endpoint by name to get the ID
        endpoint = await self.endpoint_repository.get_by_name(endpoint_name)
        if not endpoint:
            self.logger.warning(f"Endpoint '{endpoint_name}' not found")
            return [], 0

        return await self.script_repository.get_by_endpoint_id(
            endpoint.id, limit, offset
        )

    async def get_all_scripts(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ValidationScript], int]:
        """Get all validation scripts with pagination."""
        return await self.script_repository.get_all(limit, offset)

    async def update_script(
        self, script_id: str, script: ValidationScript
    ) -> Optional[ValidationScript]:
        """Update an existing validation script."""
        existing = await self.script_repository.get_by_id(script_id)
        if not existing:
            return None
        return await self.script_repository.update(script_id, script)

    async def delete_script(self, script_id: str) -> bool:
        """Delete a validation script."""
        return await self.script_repository.delete(script_id)

    async def delete_scripts_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all validation scripts for a specific endpoint."""
        return await self.script_repository.delete_by_endpoint_id(endpoint_id)

    async def delete_validation_scripts_by_endpoint_name(
        self, endpoint_name: str
    ) -> int:
        """Delete all validation scripts for a specific endpoint by name."""
        # Get endpoint by name to get the ID
        endpoint = await self.endpoint_repository.get_by_name(endpoint_name)
        if not endpoint:
            self.logger.warning(f"Endpoint '{endpoint_name}' not found for deletion")
            return 0

        return await self.script_repository.delete_by_endpoint_id(endpoint.id)

    async def generate_scripts_for_endpoint(
        self, endpoint_id: str, override_existing: bool = True
    ) -> TestScriptGeneratorOutput:
        """Generate validation scripts for a specific endpoint using TestScriptGeneratorTool."""
        self.logger.info(f"Starting script generation for endpoint: {endpoint_id}")

        # Get endpoint info
        endpoint = await self.endpoint_repository.get_by_id(endpoint_id)
        if not endpoint:
            self.logger.error(f"Endpoint not found: {endpoint_id}")
            raise ValueError(f"Endpoint with ID {endpoint_id} not found")

        self.logger.debug(f"Found endpoint: {endpoint.method} {endpoint.path}")

        # If override_existing is True, delete existing validation scripts first
        if override_existing:
            existing_scripts, _ = await self.script_repository.get_by_endpoint_id(
                endpoint_id
            )
            if existing_scripts:
                deleted_count = await self.script_repository.delete_by_endpoint_id(
                    endpoint_id
                )
                self.logger.info(
                    f"Deleted {deleted_count} existing validation scripts for endpoint {endpoint_id}"
                )
            else:
                self.logger.info(
                    f"No existing validation scripts found for endpoint {endpoint_id}"
                )

        # Get constraints for the endpoint
        constraints, _ = await self.constraint_repository.get_by_endpoint_id(
            endpoint_id
        )
        self.logger.info(f"Retrieved {len(constraints)} constraints for endpoint")

        # Create input for script generator
        generator_input = TestScriptGeneratorInput(
            endpoint_info=endpoint, constraints=constraints
        )

        # Use TestScriptGeneratorTool to generate scripts
        self.logger.info("Invoking TestScriptGeneratorTool...")
        generator_tool = TestScriptGeneratorTool(verbose=False, cache_enabled=False)
        generator_output = await generator_tool.execute(generator_input)
        self.logger.info(
            f"Generated {len(generator_output.validation_scripts)} validation scripts"
        )

        # Save generated scripts to repository
        saved_scripts = []

        # Get dataset_id from endpoint
        dataset_id = getattr(endpoint, "dataset_id", None)
        if not dataset_id:
            self.logger.error(f"Endpoint {endpoint_id} has no dataset_id")
            raise ValueError(f"Endpoint {endpoint_id} has no dataset_id")

        # Create dataset-specific validation script repository
        from adapters.repository.json_file_validation_script_repository import (
            JsonFileValidationScriptRepository,
        )

        dataset_script_repo = JsonFileValidationScriptRepository(dataset_id=dataset_id)

        for script in generator_output.validation_scripts:
            # Set endpoint_id for the script
            script.endpoint_id = endpoint_id
            # Generate new ID if not present
            if not script.id:
                script.id = str(uuid.uuid4())

            # Normalize validation script code to use .get() syntax
            script.validation_code = self._normalize_validation_script(
                script.validation_code
            )

            # Save to dataset-specific repository
            saved_script = await dataset_script_repo.create(script)
            saved_scripts.append(saved_script)

        self.logger.info(f"Saved {len(saved_scripts)} scripts to repository")

        # Update the output with saved scripts
        generator_output.validation_scripts = saved_scripts

        return generator_output

    def _normalize_validation_script(self, validation_code: str) -> str:
        """
        Normalize validation script code to use .get() syntax instead of direct attribute access.

        Args:
            validation_code: The original validation script code

        Returns:
            Normalized validation script code
        """
        if not validation_code:
            return validation_code

        normalized_code = validation_code

        # Fix response.status_code -> response.get('status_code')
        normalized_code = normalized_code.replace(
            "response.status_code", "response.get('status_code')"
        )

        # Fix response.get('status') -> response.get('status_code') for consistency
        normalized_code = normalized_code.replace(
            "response.get('status')", "response.get('status_code')"
        )

        # Fix other common response attribute access patterns
        response_attributes = [
            "headers",
            "body",
            "json",
            "text",
            "content",
            "url",
            "method",
        ]

        for attr in response_attributes:
            # Fix response.attr -> response.get('attr')
            normalized_code = normalized_code.replace(
                f"response.{attr}", f"response.get('{attr}')"
            )

        # Fix request attribute access patterns
        request_attributes = ["params", "headers", "body", "json", "method", "url"]

        for attr in request_attributes:
            # Fix request.attr -> request.get('attr')
            normalized_code = normalized_code.replace(
                f"request.{attr}", f"request.get('{attr}')"
            )

        # Log normalization if changes were made
        if normalized_code != validation_code:
            self.logger.debug("Normalized validation script code to use .get() syntax")

        return normalized_code
