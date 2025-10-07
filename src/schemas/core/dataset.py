# schemas/core/dataset.py

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Dataset(BaseModel):
    """Dataset entity representing an OpenAPI specification."""

    id: Optional[str] = Field(None, description="Unique identifier for the dataset")
    name: str = Field(..., description="Name of the dataset")
    description: Optional[str] = Field(None, description="Description of the dataset")
    spec_file_path: Optional[str] = Field(
        None, description="Path to the OpenAPI spec file"
    )
    spec_content: Optional[Dict[str, Any]] = Field(
        None, description="Parsed OpenAPI spec content"
    )
    version: Optional[str] = Field(None, description="API version from spec")
    base_url: Optional[str] = Field(None, description="Base URL for API")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "dataset-123",
                "name": "Petstore API",
                "description": "Sample Petstore API v1.0",
                "version": "1.0.0",
                "base_url": "https://api.petstore.com",
                "created_at": "2025-10-01T10:00:00",
                "updated_at": "2025-10-01T10:00:00",
            }
        }
