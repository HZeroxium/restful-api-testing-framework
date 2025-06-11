# tools/test_execution_reporter.py

from typing import Dict, Optional
import uuid

from core.base_tool import BaseTool
from schemas.tools.test_execution_reporter import (
    TestExecutionReporterInput,
    TestExecutionReporterOutput,
    TestReport,
    TestSummary,
    TestStatus,
)
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestExecutionReporterTool(BaseTool):
    """
    Tool for generating test reports for API endpoint tests.
    This tool collects test results and generates human-readable reports.
    """

    def __init__(
        self,
        *,
        name: str = "test_report",
        description: str = "Generates test reports for API endpoint tests",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestExecutionReporterInput,
            output_schema=TestExecutionReporterOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    async def _execute(
        self, inp: TestExecutionReporterInput
    ) -> TestExecutionReporterOutput:
        """Generate a test report for the given test results."""
        self.logger.info(
            f"Generating test report for {inp.endpoint_method.upper()} {inp.endpoint_path}"
        )

        # Calculate summary statistics
        total = len(inp.test_case_results)
        passed = sum(1 for r in inp.test_case_results if r.status == TestStatus.PASS)
        failed = sum(1 for r in inp.test_case_results if r.status == TestStatus.FAIL)
        errors = sum(1 for r in inp.test_case_results if r.status == TestStatus.ERROR)
        skipped = sum(
            1 for r in inp.test_case_results if r.status == TestStatus.SKIPPED
        )
        success_rate = (passed / total) * 100 if total > 0 else 0

        self.logger.add_context(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            error_tests=errors,
            skipped_tests=skipped,
            success_rate=round(success_rate, 2),
        )

        summary = TestSummary(
            total_tests=total,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            success_rate=success_rate,
        )

        total_time = (inp.finished_at - inp.started_at).total_seconds()

        # Generate a unique ID for the report
        report_id = str(uuid.uuid4())

        # Create test report
        report = TestReport(
            id=report_id,  # Add the generated ID
            api_name=inp.api_name,
            api_version=inp.api_version,
            endpoint_name=inp.endpoint_name,
            endpoint_path=inp.endpoint_path,
            endpoint_method=inp.endpoint_method,
            summary=summary,
            test_case_results=inp.test_case_results,
            started_at=inp.started_at,
            finished_at=inp.finished_at,
            total_time=total_time,
        )

        self.logger.info(
            f"Test report generated successfully for {inp.endpoint_method.upper()} {inp.endpoint_path}"
        )
        self.logger.debug(f"Report ID: {report_id}, Total time: {total_time:.2f}s")

        # Return the report without saving to file
        return TestExecutionReporterOutput(report=report)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        self.logger.debug("Cleaning up TestExecutionReporterTool resources")
