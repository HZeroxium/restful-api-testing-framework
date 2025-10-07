# app/api/dto/validation_script_dto.py

from typing import List, Optional
from pydantic import BaseModel, Field

from schemas.tools.test_script_generator import ValidationScript


class ValidationScriptCreateRequest(BaseModel):
    """Request for creating a new validation script."""

    endpoint_id: str = Field(..., description="ID of the endpoint")
    name: str = Field(..., description="Script name")
    script_type: str = Field(..., description="Type of script")
    validation_code: str = Field(..., description="Validation code")
    description: str = Field(..., description="Script description")
    constraint_id: Optional[str] = Field(None, description="Related constraint ID")


class ValidationScriptResponse(BaseModel):
    """Response model for a validation script."""

    id: str
    endpoint_id: Optional[str] = None
    name: str
    script_type: str
    validation_code: str
    description: str
    constraint_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_script(cls, script: ValidationScript) -> "ValidationScriptResponse":
        """Convert ValidationScript to ValidationScriptResponse."""
        return cls(
            id=script.id,
            endpoint_id=script.endpoint_id,
            name=script.name,
            script_type=script.script_type,
            validation_code=script.validation_code,
            description=script.description,
            constraint_id=script.constraint_id,
            created_at=script.created_at,
            updated_at=script.updated_at,
        )


class ValidationScriptListResponse(BaseModel):
    """Response model for a list of validation scripts."""

    scripts: List[ValidationScriptResponse]
    total: int


class GenerateScriptsRequest(BaseModel):
    """Request for generating validation scripts for an endpoint."""

    endpoint_id: str = Field(
        ..., description="ID of the endpoint to generate scripts for"
    )


class GenerateScriptsResponse(BaseModel):
    """Response from generating validation scripts."""

    endpoint_id: str
    scripts: List[ValidationScriptResponse]
    total_scripts: int

    @classmethod
    def from_generator_output(
        cls, output, endpoint_id: str
    ) -> "GenerateScriptsResponse":
        """Convert TestScriptGeneratorOutput to GenerateScriptsResponse."""
        return cls(
            endpoint_id=endpoint_id,
            scripts=[
                ValidationScriptResponse.from_script(s)
                for s in output.validation_scripts
            ],
            total_scripts=len(output.validation_scripts),
        )
