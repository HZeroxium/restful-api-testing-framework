# application/services/constraint_service.py

from typing import List, Optional, Tuple
import uuid

from domain.ports.constraint_repository import ConstraintRepositoryInterface
from domain.ports.endpoint_repository import EndpointRepositoryInterface
from schemas.tools.constraint_miner import (
    ApiConstraint,
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
)
from tools.llm.static_constraint_miner import StaticConstraintMinerTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class ConstraintService:
    """Service for managing ApiConstraint operations."""

    def __init__(
        self,
        constraint_repository: ConstraintRepositoryInterface,
        endpoint_repository: EndpointRepositoryInterface,
    ):
        self.constraint_repository = constraint_repository
        self.endpoint_repository = endpoint_repository
        self.logger = LoggerFactory.get_logger(
            name="service.constraint",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

    async def create_constraint(self, constraint: ApiConstraint) -> ApiConstraint:
        """Create a new constraint."""
        if not constraint.id:
            constraint.id = str(uuid.uuid4())
        return await self.constraint_repository.create(constraint)

    async def get_constraint_by_id(self, constraint_id: str) -> Optional[ApiConstraint]:
        """Get constraint by ID."""
        return await self.constraint_repository.get_by_id(constraint_id)

    async def get_constraints_by_endpoint_id(
        self, endpoint_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ApiConstraint], int]:
        """Get all constraints for a specific endpoint with pagination."""
        return await self.constraint_repository.get_by_endpoint_id(
            endpoint_id, limit, offset
        )

    async def get_constraints_by_endpoint_name(
        self, endpoint_name: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ApiConstraint], int]:
        """Get constraints for a specific endpoint by name with pagination."""
        # Get endpoint by name to get the ID
        endpoint = await self.endpoint_repository.get_by_name(endpoint_name)
        if not endpoint:
            self.logger.warning(f"Endpoint '{endpoint_name}' not found")
            return [], 0

        return await self.constraint_repository.get_by_endpoint_id(
            endpoint.id, limit, offset
        )

    async def get_all_constraints(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ApiConstraint], int]:
        """Get all constraints with pagination."""
        return await self.constraint_repository.get_all(limit, offset)

    async def update_constraint(
        self, constraint_id: str, constraint: ApiConstraint
    ) -> Optional[ApiConstraint]:
        """Update an existing constraint."""
        existing = await self.constraint_repository.get_by_id(constraint_id)
        if not existing:
            return None
        return await self.constraint_repository.update(constraint_id, constraint)

    async def delete_constraint(self, constraint_id: str) -> bool:
        """Delete a constraint."""
        return await self.constraint_repository.delete(constraint_id)

    async def delete_constraints_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all constraints for a specific endpoint."""
        return await self.constraint_repository.delete_by_endpoint_id(endpoint_id)

    async def delete_constraints_by_endpoint_name(self, endpoint_name: str) -> int:
        """Delete all constraints for a specific endpoint by name."""
        # Get endpoint by name to get the ID
        endpoint = await self.endpoint_repository.get_by_name(endpoint_name)
        if not endpoint:
            self.logger.warning(f"Endpoint '{endpoint_name}' not found for deletion")
            return 0

        return await self.constraint_repository.delete_by_endpoint_id(endpoint.id)

    async def mine_constraints_for_endpoint(
        self, endpoint_id: str, override_existing: bool = True
    ) -> StaticConstraintMinerOutput:
        """Mine constraints for a specific endpoint using StaticConstraintMinerTool."""
        self.logger.info(f"Starting constraint mining for endpoint: {endpoint_id}")

        # Get endpoint info
        endpoint = await self.endpoint_repository.get_by_id(endpoint_id)
        if not endpoint:
            self.logger.error(f"Endpoint not found: {endpoint_id}")
            raise ValueError(f"Endpoint with ID {endpoint_id} not found")

        self.logger.debug(f"Found endpoint: {endpoint.method} {endpoint.path}")

        # If override_existing is True, delete existing constraints first
        if override_existing:
            existing_constraints, _ = (
                await self.constraint_repository.get_by_endpoint_id(endpoint_id)
            )
            if existing_constraints:
                deleted_count = await self.constraint_repository.delete_by_endpoint_id(
                    endpoint_id
                )
                self.logger.info(
                    f"Deleted {deleted_count} existing constraints for endpoint {endpoint_id}"
                )
            else:
                self.logger.info(
                    f"No existing constraints found for endpoint {endpoint_id}"
                )

        # Create input for constraint miner
        miner_input = StaticConstraintMinerInput(
            endpoint_info=endpoint,
            constraint_types=[
                "REQUEST_PARAM",
                "REQUEST_BODY",
                "RESPONSE_PROPERTY",
                "REQUEST_RESPONSE",
            ],
            include_examples=True,
            # Avoid generating schema-only/type/required constraints; focus on complex rules
            include_schema_constraints=False,
            include_correlation_constraints=True,
        )

        # Use StaticConstraintMinerTool to mine constraints
        self.logger.info("Invoking StaticConstraintMinerTool...")
        miner_tool = StaticConstraintMinerTool(verbose=False, cache_enabled=False)
        miner_output = await miner_tool.execute(miner_input)
        self.logger.info(f"Mined {len(miner_output.constraints)} constraints")

        # Post-filter: drop trivial constraints (type/required/shape-only)
        try:
            from tools.constraint_miner_tools.filters import is_trivial_constraint

            before_count = len(miner_output.constraints)
            filtered_constraints = [
                c for c in miner_output.constraints if not is_trivial_constraint(c)
            ]
            dropped = before_count - len(filtered_constraints)
            if dropped > 0:
                self.logger.info(
                    f"Dropped {dropped} trivial constraints out of {before_count}"
                )
            # miner_output.constraints = filtered_constraints
        except Exception as e:
            self.logger.warning(
                f"Constraint filter failed; proceeding without drop. Error: {e}"
            )

        # Save mined constraints to repository
        saved_constraints = []

        # Get dataset_id from endpoint
        dataset_id = getattr(endpoint, "dataset_id", None)
        if not dataset_id:
            self.logger.error(f"Endpoint {endpoint_id} has no dataset_id")
            raise ValueError(f"Endpoint {endpoint_id} has no dataset_id")

        # Create dataset-specific constraint repository
        from adapters.repository.json_file_constraint_repository import (
            JsonFileConstraintRepository,
        )

        dataset_constraint_repo = JsonFileConstraintRepository(dataset_id=dataset_id)

        for constraint in miner_output.constraints:
            # Set endpoint_id for the constraint
            constraint.endpoint_id = endpoint_id
            # Generate new ID if not present
            if not constraint.id:
                constraint.id = str(uuid.uuid4())

            # Save to dataset-specific repository
            saved_constraint = await dataset_constraint_repo.create(constraint)
            saved_constraints.append(saved_constraint)

        self.logger.info(f"Saved {len(saved_constraints)} constraints to repository")

        # Update the output with saved constraints
        miner_output.constraints = saved_constraints
        miner_output.request_param_constraints = [
            c for c in saved_constraints if c.type.value == "request_param"
        ]
        miner_output.request_body_constraints = [
            c for c in saved_constraints if c.type.value == "request_body"
        ]
        miner_output.response_property_constraints = [
            c for c in saved_constraints if c.type.value == "response_property"
        ]
        miner_output.request_response_constraints = [
            c for c in saved_constraints if c.type.value == "request_response"
        ]

        return miner_output
