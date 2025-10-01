# application/services/dataset_service.py

from typing import List, Optional, Dict, Any
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
        datasets_base_path = getattr(self.dataset_repo, "datasets_base_path", "data/datasets")
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

    async def get_dataset_endpoints(self, dataset_id: str) -> List[EndpointInfo]:
        """Get all endpoints for a dataset."""
        self.logger.info(f"Retrieving endpoints for dataset: {dataset_id}")

        # Verify dataset exists
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        endpoints = await self.endpoint_repo.get_by_dataset_id(dataset_id)
        self.logger.info(
            f"Retrieved {len(endpoints)} endpoints for dataset {dataset_id}"
        )
        return endpoints

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID."""
        return await self.dataset_repo.get_by_id(dataset_id)

    async def get_all_datasets(self) -> List[Dataset]:
        """Get all datasets."""
        return await self.dataset_repo.get_all()

    async def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset and all its associated data."""
        self.logger.info(f"Deleting dataset: {dataset_id}")

        # Delete all endpoints for this dataset
        endpoints = await self.endpoint_repo.get_by_dataset_id(dataset_id)
        for endpoint in endpoints:
            if endpoint.id:
                await self.endpoint_repo.delete(endpoint.id)

        # Delete the dataset
        result = await self.dataset_repo.delete(dataset_id)
        if result:
            self.logger.info(f"Successfully deleted dataset: {dataset_id}")
        else:
            self.logger.warning(f"Failed to delete dataset: {dataset_id}")

        return result
