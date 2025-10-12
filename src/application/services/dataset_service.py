# application/services/dataset_service.py

from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import json

from domain.ports.dataset_repository import DatasetRepositoryInterface
from domain.ports.endpoint_repository import EndpointRepositoryInterface
from schemas.core.dataset import Dataset
from schemas.tools.openapi_parser import EndpointInfo
from tools.core.openapi_parser import OpenAPIParserTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class DatasetService:
    """Service for managing datasets and their OpenAPI specifications."""

    def __init__(
        self,
        dataset_repo: DatasetRepositoryInterface,
        endpoint_repo: EndpointRepositoryInterface,
    ):
        self.dataset_repo = dataset_repo
        self.endpoint_repo = endpoint_repo
        self.logger = LoggerFactory.get_logger(
            name="service.dataset",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )
        self.openapi_parser = OpenAPIParserTool(verbose=False)

    async def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        spec_file_path: Optional[str] = None,
    ) -> Dataset:
        """Create a new dataset."""
        self.logger.info(f"Creating new dataset: {name}")

        dataset = Dataset(
            name=name,
            description=description,
            spec_file_path=spec_file_path,
        )

        created_dataset = await self.dataset_repo.create(dataset)
        self.logger.info(f"Dataset created with ID: {created_dataset.id}")
        return created_dataset

    async def create_dataset_from_file(
        self, file_content: bytes, filename: str, dataset_name: str = None
    ) -> Dict[str, Any]:
        """Create a new dataset from uploaded OpenAPI spec file."""
        self.logger.info(f"Creating dataset from file: {filename}")

        # Determine if file is YAML or JSON based on extension
        is_yaml = filename.lower().endswith((".yaml", ".yml"))

        # Parse the file content
        try:
            if is_yaml:
                import yaml

                spec_dict = yaml.safe_load(file_content.decode("utf-8"))
            else:
                spec_dict = json.loads(file_content.decode("utf-8"))
        except Exception as e:
            self.logger.error(f"Failed to parse spec file: {e}")
            raise ValueError(f"Invalid spec format: {e}")

        # Extract dataset name from spec if not provided
        if not dataset_name:
            dataset_name = spec_dict.get("info", {}).get(
                "title", f"Dataset from {filename}"
            )

        # Create new dataset
        dataset = Dataset(
            name=dataset_name,
            description=spec_dict.get("info", {}).get(
                "description", f"Dataset created from {filename}"
            ),
        )

        created_dataset = await self.dataset_repo.create(dataset)
        dataset_id = created_dataset.id

        # Save spec file to dataset directory
        datasets_base_path = getattr(
            self.dataset_repo, "base_path", Path("data/datasets")
        )
        dataset_dir = datasets_base_path / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Save original file
        spec_file = dataset_dir / filename
        with open(spec_file, "wb") as f:
            f.write(file_content)

        # Also save as JSON for consistency
        json_spec_file = dataset_dir / "openapi_spec.json"
        with open(json_spec_file, "w", encoding="utf-8") as f:
            json.dump(spec_dict, f, indent=2, ensure_ascii=False)

        # Update dataset with spec info
        created_dataset.spec_file_path = str(spec_file)
        created_dataset.spec_content = spec_dict
        created_dataset.version = spec_dict.get("info", {}).get("version")

        # Extract base URL from servers
        servers = spec_dict.get("servers", [])
        if servers:
            created_dataset.base_url = servers[0].get("url")

        await self.dataset_repo.update(dataset_id, created_dataset)

        # Parse endpoints using OpenAPIParserTool
        from schemas.tools.openapi_parser import OpenAPIParserInput, SpecSourceType

        parser_input = OpenAPIParserInput(
            spec_source=str(json_spec_file),
            source_type=SpecSourceType.FILE,
        )

        parser_output = await self.openapi_parser.execute(parser_input)

        # Create dataset-specific endpoint repository
        from adapters.repository.json_file_endpoint_repository import (
            JsonFileEndpointRepository,
        )

        dataset_endpoint_repo = JsonFileEndpointRepository(dataset_id=dataset_id)

        # Save endpoints to dataset-specific repository
        endpoints_saved = 0
        for endpoint_info in parser_output.endpoints:
            # Set dataset_id for each endpoint
            endpoint_info.dataset_id = dataset_id
            await dataset_endpoint_repo.create(endpoint_info)
            endpoints_saved += 1

        self.logger.info(
            f"Created dataset {dataset_id} with {endpoints_saved} endpoints from {filename}"
        )

        return {
            "dataset_id": dataset_id,
            "dataset_name": created_dataset.name,
            "spec_version": created_dataset.version,
            "base_url": created_dataset.base_url,
            "endpoints_count": endpoints_saved,
            "api_title": spec_dict.get("info", {}).get("title", "Unknown API"),
        }

    async def upload_and_parse_spec(
        self, dataset_id: str, spec_content: str, is_yaml: bool = False
    ) -> Dict[str, Any]:
        """Upload and parse an OpenAPI spec for a dataset."""
        self.logger.info(f"Uploading and parsing spec for dataset: {dataset_id}")

        # Verify dataset exists
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # Parse the spec content
        try:
            if is_yaml:
                import yaml

                spec_dict = yaml.safe_load(spec_content)
            else:
                spec_dict = json.loads(spec_content)
        except Exception as e:
            self.logger.error(f"Failed to parse spec: {e}")
            raise ValueError(f"Invalid spec format: {e}")

        # Save spec file to dataset directory
        datasets_base_path = getattr(
            self.dataset_repo, "datasets_base_path", "data/datasets"
        )
        dataset_dir = Path(datasets_base_path) / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        spec_file = dataset_dir / "openapi_spec.json"
        with open(spec_file, "w", encoding="utf-8") as f:
            json.dump(spec_dict, f, indent=2, ensure_ascii=False)

        # Update dataset with spec info
        dataset.spec_file_path = str(spec_file)
        dataset.spec_content = spec_dict
        dataset.version = spec_dict.get("info", {}).get("version")

        # Extract base URL from servers
        servers = spec_dict.get("servers", [])
        if servers:
            dataset.base_url = servers[0].get("url")

        await self.dataset_repo.update(dataset_id, dataset)

        # Parse endpoints using OpenAPIParserTool
        from schemas.tools.openapi_parser import OpenAPIParserInput, SpecSourceType

        parser_input = OpenAPIParserInput(
            spec_source=str(spec_file),
            source_type=SpecSourceType.FILE,
        )

        parser_output = await self.openapi_parser.execute(parser_input)

        # Save endpoints to dataset's endpoint file and repository
        endpoints_saved = 0
        for endpoint_info in parser_output.endpoints:
            # Set dataset_id for each endpoint
            endpoint_info.dataset_id = dataset_id
            await self.endpoint_repo.create(endpoint_info)
            endpoints_saved += 1

        self.logger.info(
            f"Parsed and saved {endpoints_saved} endpoints for dataset {dataset_id}"
        )

        return {
            "dataset_id": dataset_id,
            "spec_version": dataset.version,
            "base_url": dataset.base_url,
            "endpoints_count": endpoints_saved,
            "api_title": parser_output.title,
        }

    async def get_dataset_endpoints(
        self, dataset_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[EndpointInfo], int]:
        """Get all endpoints for a dataset with pagination."""
        self.logger.info(f"Retrieving endpoints for dataset: {dataset_id}")

        # Verify dataset exists
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # Create dataset-specific endpoint repository
        from adapters.repository.json_file_endpoint_repository import (
            JsonFileEndpointRepository,
        )

        dataset_endpoint_repo = JsonFileEndpointRepository(dataset_id=dataset_id)

        endpoints, total_count = await dataset_endpoint_repo.get_all(limit, offset)
        self.logger.info(
            f"Retrieved {len(endpoints)} endpoints for dataset {dataset_id}"
        )
        return endpoints, total_count

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID."""
        return await self.dataset_repo.get_by_id(dataset_id)

    async def get_all_datasets(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Dataset], int]:
        """Get all datasets with pagination."""
        return await self.dataset_repo.get_all(limit, offset)

    async def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset and all its associated data."""
        self.logger.info(f"Deleting dataset: {dataset_id}")

        # Delete the dataset directory and all its files (including endpoints, constraints, etc.)
        datasets_base_path = getattr(
            self.dataset_repo, "base_path", Path("data/datasets")
        )
        dataset_dir = datasets_base_path / dataset_id

        if dataset_dir.exists():
            import shutil

            shutil.rmtree(dataset_dir)
            self.logger.info(f"Deleted dataset directory: {dataset_dir}")

        # Delete the dataset from index
        result = await self.dataset_repo.delete(dataset_id)
        if result:
            self.logger.info(f"Successfully deleted dataset: {dataset_id}")
        else:
            self.logger.warning(f"Failed to delete dataset: {dataset_id}")

        return result
