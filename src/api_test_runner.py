# src/api_test_runner.py

import asyncio
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

from .tools.core.test_reporter import TestReporterTool
from .tools.core.test_collection_generator import TestCollectionGeneratorTool
from .tools.core.test_executor import TestExecutorTool
from .utils.rest_api_caller_factory import RestApiCallerFactory

from .schemas.tools.openapi_parser import EndpointInfo
from .schemas.tools.test_collection_generator import (
    TestCollectionGeneratorInput,
    TestCollectionGeneratorOutput,
    TestCollection,
)
from .schemas.tools.test_executor import TestExecutorInput, TestExecutorOutput
from .schemas.tools.test_reporter import (
    TestReporterInput,
    TestCaseResult,
    ValidationResult,
    TestStatus,
)
from .utils.demo_utils import (
    parse_openapi_spec,
    select_endpoints,
    create_timestamped_output_dir,
    save_summary_file,
    validate_file_exists,
    get_default_spec_path,
    get_user_test_preferences,
    setup_api_factory,
    get_server_url_from_api_info,
)
from .common.logger import LoggerFactory, LoggerType, LogLevel


async def simplified_testing_pipeline(
    api_name: str,
    api_version: str,
    endpoints: List[EndpointInfo],
    base_url: str,
    report_output_dir: str,
    test_case_count: int = 2,
    include_invalid_data: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute the simplified testing pipeline using only TestCollectionGeneratorTool.

    This pipeline follows the correct architecture:
    1. Uses TestCollectionGeneratorTool as the main wrapper
    2. TestCollectionGeneratorTool uses TestSuiteGeneratorTool for each endpoint
    3. TestSuiteGeneratorTool handles the complete pipeline for each endpoint:
       - Mines constraints (once per endpoint)
       - Generates test data (once per endpoint)
       - Generates validation scripts (once per endpoint)
       - Verifies test data to filter mismatches
       - Creates test cases with appropriate validation scripts
       - Assembles the complete test suite
    4. Executes all test suites
    5. Generates comprehensive reports

    This eliminates duplicate LLM calls and follows proper separation of concerns.
    """

    # Initialize logger
    log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
    logger = LoggerFactory.get_logger(
        name="api-test-runner.simplified-pipeline",
        logger_type=LoggerType.STANDARD,
        level=log_level,
    )

    logger.info(f"Starting simplified testing pipeline for {api_name} v{api_version}")
    logger.add_context(
        api_name=api_name,
        api_version=api_version,
        endpoints_count=len(endpoints),
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
        base_url=base_url,
        output_dir=report_output_dir,
    )

    try:
        # Step 1: Generate complete test collection (this handles everything!)
        logger.info("Step 1: Generating complete test collection")
        test_collection_generator = TestCollectionGeneratorTool(verbose=verbose)

        collection_input = TestCollectionGeneratorInput(
            api_name=api_name,
            api_version=api_version,
            endpoints=endpoints,
            test_case_count=test_case_count,
            include_invalid_data=include_invalid_data,
        )

        collection_output: TestCollectionGeneratorOutput = (
            await test_collection_generator.execute(collection_input)
        )
        test_collection: TestCollection = collection_output.test_collection

        logger.info(
            f"Generated test collection with {len(test_collection.test_suites)} test suites"
        )

        # Calculate total test cases
        total_test_cases = sum(
            len(suite.test_cases) for suite in test_collection.test_suites
        )
        logger.info(f"Total test cases generated: {total_test_cases}")

        # Step 2: Execute all test suites
        logger.info("Step 2: Executing test suites")
        test_executor = TestExecutorTool(verbose=verbose)

        executor_input = TestExecutorInput(
            test_suites=test_collection.test_suites,
            base_url=base_url,
            timeout=30,
            parallel_execution=True,
            max_concurrent_requests=10,
        )

        executor_output: TestExecutorOutput = await test_executor.execute(
            executor_input
        )
        test_suite_results = executor_output.test_suite_results

        logger.info(f"Executed {len(test_suite_results)} test suites")

        # Step 3: Generate comprehensive reports
        logger.info("Step 3: Generating test reports")
        test_reporter = TestReporterTool(verbose=verbose)

        # Generate reports for each test suite separately
        all_reports = []
        all_test_case_results = []

        for i, suite_result in enumerate(test_suite_results):
            if len(suite_result.test_case_results) == 0:
                logger.warning(
                    f"Test suite {i+1} has no test case results, skipping report generation"
                )
                continue

            # Find corresponding test suite from collection for endpoint info
            corresponding_suite = (
                test_collection.test_suites[i]
                if i < len(test_collection.test_suites)
                else None
            )

            if not corresponding_suite:
                logger.warning(f"Could not find corresponding test suite for index {i}")
                continue

            # Convert validation results to reporter format
            test_case_results = []
            for case_result in suite_result.test_case_results:
                validation_results = []
                for validation_result in case_result.validation_results:
                    validation_results.append(
                        ValidationResult(
                            script_id=validation_result["script_id"],
                            script_name=validation_result["script_name"],
                            status=(
                                TestStatus.PASS
                                if validation_result["passed"]
                                else TestStatus.FAIL
                            ),
                            message=validation_result.get("result", ""),
                            validation_code="",  # Not needed for reporting
                            script_type=None,  # Will be determined from script name
                        )
                    )

                test_case_results.append(
                    TestCaseResult(
                        test_case_id=case_result.test_case_id,
                        test_case_name=case_result.test_case_name,
                        status=(
                            TestStatus.PASS if case_result.passed else TestStatus.FAIL
                        ),
                        elapsed_time=case_result.response_time,
                        request=case_result.request_details,
                        response={
                            "status_code": case_result.status_code,
                            "body": case_result.response_body,
                            "headers": case_result.response_headers,
                        },
                        validation_results=validation_results,
                    )
                )

            # Generate individual report for this endpoint
            if test_case_results:
                reporter_input = TestReporterInput(
                    api_name=api_name,
                    api_version=api_version,
                    endpoint_name=corresponding_suite.endpoint_info.name
                    or corresponding_suite.endpoint_info.path,
                    endpoint_path=corresponding_suite.endpoint_info.path,
                    endpoint_method=corresponding_suite.endpoint_info.method,
                    test_case_results=test_case_results,
                    started_at=datetime.now(),  # Approximate
                    finished_at=datetime.now(),  # Approximate
                )

                reporter_output = await test_reporter.execute(reporter_input)

                # Save the report to a file
                safe_endpoint_name = (
                    (
                        corresponding_suite.endpoint_info.name
                        or corresponding_suite.endpoint_info.path
                    )
                    .replace("/", "_")
                    .replace("{", "")
                    .replace("}", "")
                )
                filename = f"{api_name}_{safe_endpoint_name}.json"
                report_path = os.path.join(report_output_dir, filename)

                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                with open(report_path, "w") as f:
                    json.dump(
                        reporter_output.report.model_dump(), f, indent=2, default=str
                    )

                # Add the report to our collection
                report_data = reporter_output.report.model_dump()
                report_data["report_path"] = report_path
                all_reports.append(report_data)
                all_test_case_results.extend(test_case_results)

                logger.info(f"Test report saved to: {report_path}")

        # Create overall summary
        total_test_cases = len(all_test_case_results)
        passed_tests = sum(
            1 for result in all_test_case_results if result.status == TestStatus.PASS
        )
        failed_tests = sum(
            1 for result in all_test_case_results if result.status == TestStatus.FAIL
        )

        summary = {
            "total_suites": len(test_collection.test_suites),
            "total_cases": total_test_cases,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": 0,  # Not tracked separately in current format
            "skipped": 0,  # Not tracked separately in current format
            "success_rate": (
                (passed_tests / total_test_cases * 100) if total_test_cases > 0 else 0.0
            ),
            "reports": all_reports,
        }

        # Save summary
        summary_path = os.path.join(report_output_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info("Pipeline completed successfully")
        logger.add_context(
            total_test_suites=len(test_collection.test_suites),
            total_test_cases=total_test_cases,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=round(summary["success_rate"], 1),
            summary_path=summary_path,
        )

        return summary
    except Exception as e:
        logger.error(f"Error during testing pipeline: {str(e)}")
        raise e


async def generate_and_execute_test_collection(
    api_name: str,
    api_version: str,
    endpoints: List[EndpointInfo],
    factory: RestApiCallerFactory,
    report_output_dir: str,
    test_case_count: int = 2,
    include_invalid_data: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Generate a test collection, execute tests, and generate reports using the updated pipeline.

    Args:
        api_name: Name of the API
        api_version: Version of the API
        endpoints: List of endpoints to test
        factory: Factory for creating endpoint-specific tools (used for base_url extraction)
        report_output_dir: Directory to save test reports
        test_case_count: Number of test cases per endpoint
        include_invalid_data: Whether to include invalid test data
        verbose: Enable verbose logging

    Returns:
        Summary of test results
    """
    # Extract base URL from factory
    base_url = factory.server_url

    # Use the new simplified testing pipeline
    return await simplified_testing_pipeline(
        api_name=api_name,
        api_version=api_version,
        endpoints=endpoints,
        base_url=base_url,
        report_output_dir=report_output_dir,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
        verbose=verbose,
    )


async def main():
    """Demo showcasing the complete API testing workflow using the new component structure."""
    parser = argparse.ArgumentParser(description="Execute API tests")
    parser.add_argument(
        "--spec",
        type=str,
        default=get_default_spec_path(),
        help="Path to OpenAPI specification file",
    )
    parser.add_argument(
        "--endpoints",
        type=str,
        help="Comma-separated list of endpoint indices to test (e.g., '1,2,3' or '43')",
    )
    parser.add_argument(
        "--test-cases",
        type=int,
        help="Number of test cases per endpoint",
    )
    parser.add_argument(
        "--invalid",
        action="store_true",
        help="Include invalid test data for negative testing",
    )
    parser.add_argument(
        "--no-invalid",
        action="store_true",
        help="Exclude invalid test data",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Initialize main logger
    log_level = LogLevel.DEBUG if args.verbose else LogLevel.INFO
    logger = LoggerFactory.get_logger(
        name="api-test-runner-main",
        logger_type=LoggerType.STANDARD,
        level=log_level,
    )

    logger.info("Starting API test runner")
    logger.add_context(
        spec_file=args.spec,
        verbose=args.verbose,
        test_cases=args.test_cases,
        include_invalid=args.invalid,
        exclude_invalid=args.no_invalid,
    )

    # Validate input file
    if not validate_file_exists(args.spec):
        logger.error(f"Specification file not found: {args.spec}")
        return

    # Create timestamped output directory for test reports
    report_output_dir = create_timestamped_output_dir("output", "test_reports")
    logger.add_context(output_directory=report_output_dir)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=False)

    if not api_info["endpoints"]:
        logger.error("No endpoints found in the OpenAPI specification.")
        return

    api_name = api_info["title"]
    api_version = api_info["version"]
    server_url = get_server_url_from_api_info(api_info)

    logger.info(f"API: {api_name} v{api_version}")
    logger.info(f"Server URL: {server_url}")
    logger.add_context(
        api_name=api_name,
        api_version=api_version,
        server_url=server_url,
        total_endpoints=len(api_info["endpoints"]),
    )

    # Create factory for endpoint-specific tools
    factory = setup_api_factory(server_url, verbose=args.verbose)

    # Select endpoints to test
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to test (comma-separated, or 'all'): ",
        pre_selected_indices=args.endpoints,
    )

    logger.info(f"Selected {len(selected_endpoints)} endpoints for testing")

    # Get test configuration
    if args.test_cases is not None:
        test_case_count = args.test_cases
        # Validate test case count
        if test_case_count < 1:
            test_case_count = 1
            logger.warning("Test case count must be at least 1, using 1.")
        elif test_case_count > 10:
            test_case_count = 10
            logger.warning("Maximum test case count is 10, using 10.")
    else:
        test_case_count = None

    if args.invalid:
        include_invalid_data = True
    elif args.no_invalid:
        include_invalid_data = False
    else:
        include_invalid_data = None

    # Get user input if not provided via command line
    if test_case_count is None or include_invalid_data is None:
        user_test_case_count, user_include_invalid = get_user_test_preferences()
        if test_case_count is None:
            test_case_count = user_test_case_count
        if include_invalid_data is None:
            include_invalid_data = user_include_invalid

    logger.add_context(
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
    )

    # Generate test collection, execute tests, and create reports
    summary = await generate_and_execute_test_collection(
        api_name=api_name,
        api_version=api_version,
        endpoints=selected_endpoints,
        factory=factory,
        report_output_dir=report_output_dir,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
        verbose=args.verbose,
    )

    # Save summary
    summary_data = {
        "endpoints_tested": len(selected_endpoints),
        "test_case_count": test_case_count,
        "include_invalid_data": include_invalid_data,
        **summary,
    }

    summary_path = save_summary_file(report_output_dir, api_info, summary_data)

    logger.info("Test execution completed successfully")
    logger.add_context(
        summary_path=summary_path,
        tests_passed=summary["passed"],
        total_tests=summary["total_cases"],
        success_rate=round(summary["success_rate"], 1),
    )

    # Final summary
    print(f"\nTest execution completed. Reports saved to: {report_output_dir}")
    print(f"Summary saved to: {summary_path}")
    print(
        f"Summary: {summary['passed']}/{summary['total_cases']} tests passed ({summary['success_rate']:.1f}%)"
    )


if __name__ == "__main__":
    asyncio.run(main())
