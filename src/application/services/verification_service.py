"""
Service for verification operations using validation scripts.
"""

import time
from typing import List, Dict, Any, Optional
from common.logger import LoggerFactory, LoggerType, LogLevel
from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.test_script_generator import ValidationScript
from schemas.tools.test_data_generator import TestData
from application.services.endpoint_service import EndpointService
from application.services.validation_script_service import ValidationScriptService
from tools.core.test_data_verifier import TestDataVerifierTool
from tools.core.code_executor import CodeExecutorTool
from utils.code_script_utils import prepare_validation_script
from schemas.tools.test_data_verifier import (
    TestDataVerifierInput,
    TestDataVerifierOutput,
)
from schemas.tools.code_executor import CodeExecutorInput
from app.api.dto.verification_dto import (
    VerifyTestDataRequest,
    VerifyTestDataResponse,
    TestDataItem,
    TestDataVerificationResult,
    VerificationResult,
    VerifyRequestResponseRequest,
    VerifyRequestResponseResponse,
    RequestResponsePair,
    RequestResponseVerificationResult,
    ValidationScriptResult,
)


class VerificationService:
    """Service for verification operations."""

    def __init__(
        self,
        endpoint_service: EndpointService,
        validation_script_service: ValidationScriptService,
        test_data_verifier: TestDataVerifierTool,
        code_executor: CodeExecutorTool,
    ):
        self.endpoint_service = endpoint_service
        self.validation_script_service = validation_script_service
        self.test_data_verifier = test_data_verifier
        self.code_executor = code_executor
        self.logger = LoggerFactory.get_logger(
            name="service.verification",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

    async def verify_test_data(
        self, endpoint_name: str, request: VerifyTestDataRequest
    ) -> VerifyTestDataResponse:
        """Verify test data against validation scripts."""
        self.logger.info(f"Verifying test data for endpoint: {endpoint_name}")

        # Find endpoint by name
        endpoint = await self.endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise ValueError(f"Endpoint '{endpoint_name}' not found")

        # Get validation scripts for request_param and request_body types
        all_scripts = await self.validation_script_service.get_scripts_by_endpoint_id(
            endpoint.id
        )
        relevant_scripts = [
            script
            for script in all_scripts
            if script.script_type in ["request_param", "request_body"]
        ]

        if not relevant_scripts:
            self.logger.warning(
                f"No relevant validation scripts found for endpoint '{endpoint_name}'"
            )
            return VerifyTestDataResponse(
                endpoint_name=endpoint_name,
                endpoint_id=endpoint.id,
                total_test_data_items=len(request.test_data_items),
                overall_passed=True,  # No scripts to validate against
                verification_results=[],
                total_execution_time=0.0,
            )

        # Convert test data items to TestData objects
        test_data_list = []
        for i, item in enumerate(request.test_data_items):
            test_data = TestData(
                id=f"test_data_{i}",
                name=f"Test Data {i+1}",
                description=f"Test data item {i+1} for {endpoint_name}",
                endpoint_id=endpoint.id,
                request_params=item.request_params or {},
                request_headers=item.request_headers or {},
                request_body=item.request_body,
                expected_status_code=item.expected_status_code or 200,
            )
            test_data_list.append(test_data)

        # Use TestDataVerifierTool to verify
        verifier_input = TestDataVerifierInput(
            test_data_collection=test_data_list,
            verification_scripts=relevant_scripts,
            timeout=request.timeout or 30,
        )

        start_time = time.time()
        verifier_output = await self.test_data_verifier.execute(verifier_input)
        total_time = time.time() - start_time

        # Convert results to response format
        verification_results = []
        for i, result in enumerate(verifier_output.verification_results):
            script_results = []
            # Extract script results from verification_details
            script_results_data = result.verification_details.get("script_results", [])
            for script_result in script_results_data:
                # Determine error message and execution details
                error_message = None
                script_output = script_result.get("raw_result")

                if not script_result.get("success", False):
                    error_message = script_result.get(
                        "error", "Script execution failed"
                    )

                verification_result = VerificationResult(
                    script_id=script_result.get("script_id", ""),
                    script_type=script_result.get("script_type", ""),
                    passed=script_result.get("result", False),
                    error_message=error_message,
                    execution_time=None,  # Not available in current structure
                    script_output=script_output,
                )
                script_results.append(verification_result)

            test_data_result = TestDataVerificationResult(
                test_data_index=i,
                overall_passed=result.is_valid,
                results=script_results,
                total_execution_time=None,  # Not available in current structure
            )
            verification_results.append(test_data_result)

        overall_passed = all(result.overall_passed for result in verification_results)

        return VerifyTestDataResponse(
            endpoint_name=endpoint_name,
            endpoint_id=endpoint.id,
            total_test_data_items=len(request.test_data_items),
            overall_passed=overall_passed,
            verification_results=verification_results,
            total_execution_time=total_time,
        )

    async def verify_request_response(
        self, endpoint_name: str, request: VerifyRequestResponseRequest
    ) -> VerifyRequestResponseResponse:
        """Verify request-response pairs against validation scripts."""
        self.logger.info(
            f"Verifying request-response pairs for endpoint: {endpoint_name}"
        )

        # Find endpoint by name
        endpoint = await self.endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise ValueError(f"Endpoint '{endpoint_name}' not found")

        # Get validation scripts for response_property and request_response types
        all_scripts = await self.validation_script_service.get_scripts_by_endpoint_id(
            endpoint.id
        )
        relevant_scripts = [
            script
            for script in all_scripts
            if script.script_type in ["response_property", "request_response"]
        ]

        if not relevant_scripts:
            self.logger.warning(
                f"No relevant validation scripts found for endpoint '{endpoint_name}'"
            )
            return VerifyRequestResponseResponse(
                endpoint_name=endpoint_name,
                endpoint_id=endpoint.id,
                total_pairs=len(request.request_response_pairs),
                overall_passed=True,  # No scripts to validate against
                verification_results=[],
                total_execution_time=0.0,
            )

        # Execute validation scripts for each request-response pair
        verification_results = []
        overall_start_time = time.time()

        for pair_index, pair in enumerate(request.request_response_pairs):
            pair_start_time = time.time()
            script_results = []
            pair_passed = True

            # Normalize request/response with sensible defaults to simplify front-end payloads
            req_obj = dict(pair.request or {})
            # Default method and containers
            if "method" not in req_obj:
                req_obj["method"] = "GET"
            req_obj.setdefault("params", req_obj.get("query") or {})
            req_obj.setdefault("headers", {})

            # response may be just a body; default status_code and headers
            raw_resp = pair.response or {}
            if isinstance(raw_resp, dict) and "body" in raw_resp:
                resp_body = raw_resp.get("body")
                resp_status = raw_resp.get("status_code", 200)
                resp_headers = raw_resp.get("headers", {})
            else:
                # If front-end provided bare body, wrap it
                resp_body = raw_resp
                resp_status = 200
                resp_headers = {}

            resp_obj = {
                "status_code": resp_status,
                "headers": resp_headers,
                "body": resp_body,
            }

            # Prepare context variables in the format expected by scripts
            context_vars = {"request": req_obj, "response": resp_obj}

            # Execute each validation script
            for script in relevant_scripts:
                try:
                    script_start_time = time.time()

                    # Prepare the script for execution
                    prepared_script = prepare_validation_script(script.validation_code)

                    # Execute the script
                    script_input = CodeExecutorInput(
                        code=prepared_script,
                        context_variables=context_vars,
                        timeout=request.timeout or 30,
                    )

                    script_output = await self.code_executor.execute(script_input)
                    script_execution_time = time.time() - script_start_time

                    # Parse the result
                    passed = self._parse_script_result(script_output)
                    if not passed:
                        pair_passed = False

                    # Determine error message
                    error_message = None
                    if not script_output.success:
                        error_message = script_output.error or "Script execution failed"
                    elif not passed:
                        error_message = (
                            f"Validation failed: {script_output.stdout or 'No output'}"
                        )

                    script_result = ValidationScriptResult(
                        script_id=script.id,
                        script_type=script.script_type,
                        passed=passed,
                        error_message=error_message,
                        execution_time=script_execution_time,
                        script_output=script_output.stdout,
                    )
                    script_results.append(script_result)

                except Exception as e:
                    self.logger.error(
                        f"Error executing validation script {script.id}: {e}"
                    )
                    script_result = ValidationScriptResult(
                        script_id=script.id,
                        script_type=script.script_type,
                        passed=False,
                        error_message=str(e),
                        execution_time=0.0,
                        script_output=None,
                    )
                    script_results.append(script_result)
                    pair_passed = False

            pair_execution_time = time.time() - pair_start_time

            pair_result = RequestResponseVerificationResult(
                pair_index=pair_index,
                overall_passed=pair_passed,
                results=script_results,
                total_execution_time=pair_execution_time,
            )
            verification_results.append(pair_result)

        total_time = time.time() - overall_start_time
        overall_passed = all(result.overall_passed for result in verification_results)

        return VerifyRequestResponseResponse(
            endpoint_name=endpoint_name,
            endpoint_id=endpoint.id,
            total_pairs=len(request.request_response_pairs),
            overall_passed=overall_passed,
            verification_results=verification_results,
            total_execution_time=total_time,
        )

    def _parse_script_result(self, script_output) -> bool:
        """Parse script execution result to determine if validation passed."""
        try:
            # Get result from stdout
            result_text = script_output.stdout or ""

            if not result_text:
                return False

            # Clean the result text
            result_text = result_text.strip().lower()

            # Check for common boolean representations
            if result_text in ["true", "1", "yes", "pass", "passed", "success"]:
                return True
            elif result_text in ["false", "0", "no", "fail", "failed", "error"]:
                return False

            # Try to parse as boolean
            try:
                return bool(eval(result_text))
            except:
                # If evaluation fails, check if it's a non-empty string
                return bool(result_text)

        except Exception as e:
            self.logger.error(f"Error parsing script result: {e}")
            return False
