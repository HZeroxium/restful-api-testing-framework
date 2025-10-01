# application/services/validation_script_service.py

from typing import List, Optional
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

    async def create_script(self, script: ValidationScript) -> ValidationScript:
        """Create a new validation script."""
        if not script.id:
            script.id = str(uuid.uuid4())
        return await self.script_repository.create(script)

    async def get_script_by_id(self, script_id: str) -> Optional[ValidationScript]:
        """Get validation script by ID."""
        return await self.script_repository.get_by_id(script_id)

    async def get_scripts_by_endpoint_id(
        self, endpoint_id: str
    ) -> List[ValidationScript]:
        """Get all validation scripts for a specific endpoint."""
        return await self.script_repository.get_by_endpoint_id(endpoint_id)

    async def get_all_scripts(self) -> List[ValidationScript]:
        """Get all validation scripts."""
        return await self.script_repository.get_all()

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

    async def generate_scripts_for_endpoint(
        self, endpoint_id: str
    ) -> TestScriptGeneratorOutput:
        """Generate validation scripts for a specific endpoint using TestScriptGeneratorTool."""
        self.logger.info(f"Starting script generation for endpoint: {endpoint_id}")

        # Get endpoint info
        endpoint = await self.endpoint_repository.get_by_id(endpoint_id)
        if not endpoint:
            self.logger.error(f"Endpoint not found: {endpoint_id}")
            raise ValueError(f"Endpoint with ID {endpoint_id} not found")

        self.logger.debug(f"Found endpoint: {endpoint.method} {endpoint.path}")

        # Get constraints for the endpoint
        constraints = await self.constraint_repository.get_by_endpoint_id(endpoint_id)
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
        for script in generator_output.validation_scripts:
            # Set endpoint_id for the script
            script.endpoint_id = endpoint_id
            # Generate new ID if not present
            if not script.id:
                script.id = str(uuid.uuid4())

            # Save to repository
            saved_script = await self.script_repository.create(script)
            saved_scripts.append(saved_script)

        self.logger.info(f"Saved {len(saved_scripts)} scripts to repository")

        # Update the output with saved scripts
        generator_output.validation_scripts = saved_scripts

        return generator_output
