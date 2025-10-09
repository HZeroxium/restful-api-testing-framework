"""
Router for verification endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from common.logger import LoggerFactory, LoggerType, LogLevel
from infra.di.container import verification_service_dependency
from application.services.verification_service import VerificationService
from app.api.dto.verification_dto import (
    VerifyTestDataRequest,
    VerifyTestDataResponse,
    VerifyRequestResponseRequest,
    VerifyRequestResponseResponse,
)

router = APIRouter(prefix="/verify", tags=["verification"])
logger = LoggerFactory.get_logger(
    name="router.verification",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.INFO,
)


@router.post(
    "/test-data/by-endpoint-name/{endpoint_name}",
    response_model=VerifyTestDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify test data for an endpoint",
    description="Verify test data against validation scripts for request parameters and request body",
)
async def verify_test_data(
    endpoint_name: str,
    request: VerifyTestDataRequest,
    service: VerificationService = verification_service_dependency,
):
    """Verify test data for a specific endpoint by name."""
    logger.info(f"POST /verify/test-data/by-endpoint-name/{endpoint_name}")

    try:
        result = await service.verify_test_data(endpoint_name, request)
        logger.info(
            f"Successfully verified {len(request.test_data_items)} test data items for endpoint '{endpoint_name}'"
        )
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Failed to verify test data for endpoint '{endpoint_name}': {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify test data: {str(e)}",
        )


@router.post(
    "/request-response/{endpoint_name}",
    response_model=VerifyRequestResponseResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify request-response pairs for an endpoint",
    description="Verify request-response pairs against validation scripts for response properties and request-response validation",
)
async def verify_request_response(
    endpoint_name: str,
    request: VerifyRequestResponseRequest,
    service: VerificationService = verification_service_dependency,
):
    """Verify request-response pairs for a specific endpoint by name."""
    logger.info(f"POST /verify/request-response/{endpoint_name}")

    try:
        result = await service.verify_request_response(endpoint_name, request)
        logger.info(
            f"Successfully verified {len(request.request_response_pairs)} request-response pairs for endpoint '{endpoint_name}'"
        )
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Failed to verify request-response pairs for endpoint '{endpoint_name}': {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify request-response pairs: {str(e)}",
        )
