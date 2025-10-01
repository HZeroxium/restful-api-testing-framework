# infra/di/container.py

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide

from domain.ports.endpoint_repository import EndpointRepositoryInterface
from domain.ports.constraint_repository import ConstraintRepositoryInterface
from domain.ports.validation_script_repository import (
    ValidationScriptRepositoryInterface,
)

from adapters.repository.json_file_endpoint_repository import (
    JsonFileEndpointRepository,
)
from adapters.repository.json_file_constraint_repository import (
    JsonFileConstraintRepository,
)
from adapters.repository.json_file_validation_script_repository import (
    JsonFileValidationScriptRepository,
)

from application.services.endpoint_service import EndpointService
from application.services.constraint_service import ConstraintService
from application.services.validation_script_service import ValidationScriptService


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
