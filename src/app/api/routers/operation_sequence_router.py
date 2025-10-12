# app/api/routers/operation_sequence_router.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas.core.pagination import PaginationParams
from schemas.tools.operation_sequencer import OperationSequence
from application.services.operation_sequence_service import OperationSequenceService
from app.api.dto.operation_sequence_dto import (
    GenerateSequencesRequest,
    GenerateSequencesResponse,
    OperationSequenceResponse,
    OperationSequenceListResponse,
    DependencyGraphResponse,
    UpdateSequenceRequest,
    SequenceStatisticsResponse,
    SequenceValidationResponse,
)
from infra.di.container import operation_sequence_service_dependency

router = APIRouter(prefix="/api/v1/operation-sequences", tags=["Operation Sequences"])


@router.post(
    "/generate/by-dataset-id/{dataset_id}",
    response_model=GenerateSequencesResponse,
    summary="Generate operation sequences for a dataset",
)
async def generate_sequences_for_dataset(
    dataset_id: str,
    request: GenerateSequencesRequest,
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Generate operation sequences by analyzing endpoint dependencies."""
    try:
        result = await service.generate_sequences_for_dataset(
            dataset_id=dataset_id, override_existing=request.override_existing
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result["error"]
            )

        # Get saved sequences
        sequences, _ = await service.get_sequences_by_dataset_id(dataset_id)

        return GenerateSequencesResponse(
            dataset_id=result["dataset_id"],
            total_endpoints=result["total_endpoints"],
            sequences_generated=result["sequences_generated"],
            analysis_method=result["analysis_method"],
            graph=result.get("graph"),
            sequences=[
                OperationSequenceResponse.from_sequence(seq) for seq in sequences
            ],
            result=result.get("result", {}),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/by-dataset-id/{dataset_id}",
    response_model=OperationSequenceListResponse,
    summary="Get operation sequences for a dataset",
)
async def get_sequences_by_dataset(
    dataset_id: str,
    pagination: PaginationParams = Depends(),
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Retrieve all operation sequences for a dataset."""
    try:
        sequences, total = await service.get_sequences_by_dataset_id(
            dataset_id, pagination.limit, pagination.offset
        )

        from schemas.core.pagination import PaginationMetadata

        pagination_metadata = PaginationMetadata.create(
            pagination.offset, pagination.limit, total
        )

        return OperationSequenceListResponse(
            sequences=[
                OperationSequenceResponse.from_sequence(seq) for seq in sequences
            ],
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{sequence_id}",
    response_model=OperationSequenceResponse,
    summary="Get a specific operation sequence",
)
async def get_sequence_by_id(
    sequence_id: str,
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Retrieve a specific operation sequence by ID."""
    try:
        sequence = await service.get_sequence_by_id(sequence_id)
        if not sequence:
            raise HTTPException(status_code=404, detail="Sequence not found")

        return OperationSequenceResponse.from_sequence(sequence)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/graph/by-dataset-id/{dataset_id}",
    response_model=DependencyGraphResponse,
    summary="Get dependency graph for a dataset",
)
async def get_dependency_graph(
    dataset_id: str,
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Get the dependency graph representation for visualization."""
    try:
        # Get sequences for dataset
        sequences, total = await service.get_sequences_by_dataset_id(dataset_id)

        if not sequences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No sequences found for dataset",
            )

        # Build graph from sequences
        graph = service.build_graph_from_sequences(sequences)

        return DependencyGraphResponse(
            nodes=[node.model_dump() for node in graph.nodes],
            edges=[edge.model_dump() for edge in graph.edges],
            metadata=graph.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put(
    "/{sequence_id}",
    response_model=OperationSequenceResponse,
    summary="Update a specific operation sequence",
)
async def update_sequence(
    sequence_id: str,
    request: UpdateSequenceRequest,
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Update a specific operation sequence."""
    try:
        # Get existing sequence
        existing_sequence = await service.get_sequence_by_id(sequence_id)
        if not existing_sequence:
            raise HTTPException(status_code=404, detail="Sequence not found")

        # Update fields
        updated_sequence = OperationSequence(
            id=sequence_id,
            name=request.name if request.name is not None else existing_sequence.name,
            description=(
                request.description
                if request.description is not None
                else existing_sequence.description
            ),
            operations=(
                request.operations
                if request.operations is not None
                else existing_sequence.operations
            ),
            dependencies=existing_sequence.dependencies,  # Dependencies not updatable via this endpoint
            sequence_type=(
                request.sequence_type
                if request.sequence_type is not None
                else existing_sequence.sequence_type
            ),
            priority=(
                request.priority
                if request.priority is not None
                else existing_sequence.priority
            ),
            estimated_duration=(
                request.estimated_duration
                if request.estimated_duration is not None
                else existing_sequence.estimated_duration
            ),
            metadata=(
                request.metadata
                if request.metadata is not None
                else existing_sequence.metadata
            ),
        )

        # Save updated sequence
        result = await service.update_sequence(sequence_id, updated_sequence)
        if not result:
            raise HTTPException(status_code=404, detail="Sequence not found")

        return OperationSequenceResponse.from_sequence(result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete(
    "/by-dataset-id/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all sequences for a dataset",
)
async def delete_sequences_by_dataset(
    dataset_id: str,
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Delete all operation sequences for a dataset."""
    try:
        deleted_count = await service.delete_sequences_by_dataset_id(dataset_id)
        return {"deleted_count": deleted_count}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete(
    "/{sequence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific sequence",
)
async def delete_sequence(
    sequence_id: str,
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Delete a specific operation sequence."""
    try:
        success = await service.delete_sequence(sequence_id)
        if not success:
            raise HTTPException(status_code=404, detail="Sequence not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/type/{sequence_type}",
    response_model=OperationSequenceListResponse,
    summary="Get sequences by type",
)
async def get_sequences_by_type(
    sequence_type: str,
    pagination: PaginationParams = Depends(),
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Get sequences filtered by type."""
    try:
        sequences, total = await service.get_sequences_by_type(
            sequence_type, pagination.limit, pagination.offset
        )

        from schemas.core.pagination import PaginationMetadata

        pagination_metadata = PaginationMetadata.create(
            pagination.offset, pagination.limit, total
        )

        return OperationSequenceListResponse(
            sequences=[
                OperationSequenceResponse.from_sequence(seq) for seq in sequences
            ],
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/statistics/overview",
    response_model=SequenceStatisticsResponse,
    summary="Get sequence statistics",
)
async def get_sequence_statistics(
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Get comprehensive statistics about sequences."""
    try:
        stats = await service.get_sequence_statistics()
        return SequenceStatisticsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/validate",
    response_model=SequenceValidationResponse,
    summary="Validate a sequence",
)
async def validate_sequence(
    sequence: OperationSequence,
    service: OperationSequenceService = operation_sequence_service_dependency,
):
    """Validate a sequence for completeness and correctness."""
    try:
        validation_result = await service.validate_sequence(sequence)
        return SequenceValidationResponse(**validation_result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
