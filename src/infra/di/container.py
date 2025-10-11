# infra/di/container.py

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide
from fastapi import Depends

from domain.ports.endpoint_repository import EndpointRepositoryInterface
from domain.ports.constraint_repository import ConstraintRepositoryInterface
from domain.ports.validation_script_repository import (
    ValidationScriptRepositoryInterface,
)
from domain.ports.dataset_repository import DatasetRepositoryInterface
from domain.ports.test_data_repository import TestDataRepositoryInterface
from domain.ports.execution_repository import ExecutionRepositoryInterface

from adapters.repository.json_file_endpoint_repository import (
    JsonFileEndpointRepository,
)
from adapters.repository.json_file_constraint_repository import (
    JsonFileConstraintRepository,
)
from adapters.repository.json_file_validation_script_repository import (
    JsonFileValidationScriptRepository,
)
from adapters.repository.json_file_dataset_repository import (
    JsonFileDatasetRepository,
)
from adapters.repository.json_file_test_data_repository import (
    JsonFileTestDataRepository,
)
from adapters.repository.json_file_execution_repository import (
    JsonFileExecutionRepository,
)

from application.services.endpoint_service import EndpointService
from application.services.constraint_service import ConstraintService
from application.services.validation_script_service import ValidationScriptService
from application.services.dataset_service import DatasetService
from application.services.verification_service import VerificationService
from application.services.aggregator_service import AggregatorService
from application.services.test_data_service import TestDataService
from application.services.test_execution_service import TestExecutionService

from tools.core.test_data_verifier import TestDataVerifierTool
from tools.core.code_executor import CodeExecutorTool


class Container(containers.DeclarativeContainer):
    """Dependency injection container for the application."""

    # Configuration
    config = providers.Configuration()

    # Repositories
    endpoint_repository: providers.Singleton[EndpointRepositoryInterface] = (
        providers.Singleton(
            JsonFileEndpointRepository, file_path=config.endpoints.file_path
        )
    )

    constraint_repository: providers.Singleton[ConstraintRepositoryInterface] = (
        providers.Singleton(
            JsonFileConstraintRepository, file_path=config.constraints.file_path
        )
    )

    validation_script_repository: providers.Singleton[
        ValidationScriptRepositoryInterface
    ] = providers.Singleton(
        JsonFileValidationScriptRepository,
        file_path=config.validation_scripts.file_path,
    )

    dataset_repository: providers.Singleton[DatasetRepositoryInterface] = (
        providers.Singleton(
            JsonFileDatasetRepository, base_path=config.datasets.base_path
        )
    )

    test_data_repository: providers.Singleton[TestDataRepositoryInterface] = (
        providers.Singleton(JsonFileTestDataRepository)
    )

    execution_repository: providers.Singleton[ExecutionRepositoryInterface] = (
        providers.Singleton(JsonFileExecutionRepository)
    )

    # Services
    endpoint_service: providers.Factory[EndpointService] = providers.Factory(
        EndpointService, repository=endpoint_repository
    )

    constraint_service: providers.Factory[ConstraintService] = providers.Factory(
        ConstraintService,
        constraint_repository=constraint_repository,
        endpoint_repository=endpoint_repository,
    )

    validation_script_service: providers.Factory[ValidationScriptService] = (
        providers.Factory(
            ValidationScriptService,
            script_repository=validation_script_repository,
            constraint_repository=constraint_repository,
            endpoint_repository=endpoint_repository,
        )
    )

    dataset_service: providers.Factory[DatasetService] = providers.Factory(
        DatasetService,
        dataset_repo=dataset_repository,
        endpoint_repo=endpoint_repository,
    )

    test_data_service: providers.Factory[TestDataService] = providers.Factory(
        TestDataService,
        test_data_repository=test_data_repository,
    )

    test_execution_service: providers.Factory[TestExecutionService] = providers.Factory(
        TestExecutionService,
        execution_repository=execution_repository,
        test_data_repository=test_data_repository,
    )

    # Tools
    test_data_verifier: providers.Singleton[TestDataVerifierTool] = providers.Singleton(
        TestDataVerifierTool
    )

    code_executor: providers.Singleton[CodeExecutorTool] = providers.Singleton(
        CodeExecutorTool
    )

    # Verification Service
    verification_service: providers.Factory[VerificationService] = providers.Factory(
        VerificationService,
        endpoint_service=endpoint_service,
        validation_script_service=validation_script_service,
        test_data_verifier=test_data_verifier,
        code_executor=code_executor,
    )

    # Aggregator Service
    aggregator_service: providers.Factory[AggregatorService] = providers.Factory(
        AggregatorService,
        constraint_service=constraint_service,
        validation_script_service=validation_script_service,
        endpoint_service=endpoint_service,
        test_data_service=test_data_service,
        test_execution_service=test_execution_service,
    )


# Global container instance
_container: Container = None


def get_container() -> Container:
    """Get the configured container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container


# Dependency functions for FastAPI routers
# These functions provide a clean interface for dependency injection
# and eliminate the need to repeat Provide[Container.service_name] patterns


def get_endpoint_service() -> EndpointService:
    """Get EndpointService instance from DI container."""
    return get_container().endpoint_service()


def get_constraint_service() -> ConstraintService:
    """Get ConstraintService instance from DI container."""
    return get_container().constraint_service()


def get_validation_script_service() -> ValidationScriptService:
    """Get ValidationScriptService instance from DI container."""
    return get_container().validation_script_service()


def get_dataset_service() -> DatasetService:
    """Get DatasetService instance from DI container."""
    return get_container().dataset_service()


def get_verification_service() -> VerificationService:
    """Get VerificationService instance from DI container."""
    return get_container().verification_service()


def get_aggregator_service() -> AggregatorService:
    """Get AggregatorService instance from DI container."""
    return get_container().aggregator_service()


def get_test_data_service() -> TestDataService:
    """Get TestDataService instance from DI container."""
    return get_container().test_data_service()


def get_test_execution_service() -> TestExecutionService:
    """Get TestExecutionService instance from DI container."""
    return get_container().test_execution_service()


# FastAPI dependency providers
# These can be used directly in router endpoints as Depends(get_service_name)
endpoint_service_dependency = Depends(get_endpoint_service)
constraint_service_dependency = Depends(get_constraint_service)
validation_script_service_dependency = Depends(get_validation_script_service)
dataset_service_dependency = Depends(get_dataset_service)
verification_service_dependency = Depends(get_verification_service)
aggregator_service_dependency = Depends(get_aggregator_service)
test_data_service_dependency = Depends(get_test_data_service)
test_execution_service_dependency = Depends(get_test_execution_service)
