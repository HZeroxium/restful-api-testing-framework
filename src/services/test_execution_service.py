"""Service for managing test execution history."""

import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from schemas.test_collection import TestExecutionModel, TestSummary


class TestExecutionService:
    """Service for managing test execution history."""

    def __init__(self):
        """Initialize the test execution service."""
        self.executions_dir = "data/executions"
        os.makedirs(self.executions_dir, exist_ok=True)

    async def create_execution(
        self, collection_id: str, collection_name: str, reports: List[Dict[str, Any]]
    ) -> TestExecutionModel:
        """Create a new execution record.

        Args:
            collection_id: ID of the collection
            collection_name: Name of the collection
            reports: List of test reports

        Returns:
            Created execution record
        """
        # Calculate summary statistics from reports
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        total_skipped = 0

        for report in reports:
            if isinstance(report, dict) and "summary" in report:
                # If report is a dictionary
                summary = report["summary"]
                if isinstance(summary, dict):
                    total_tests += summary.get("total_tests", 0)
                    total_passed += summary.get("passed", 0)
                    total_failed += summary.get("failed", 0)
                    total_errors += summary.get("errors", 0)
                    total_skipped += summary.get("skipped", 0)
                else:
                    # If summary is an object with attributes
                    total_tests += getattr(summary, "total_tests", 0)
                    total_passed += getattr(summary, "passed", 0)
                    total_failed += getattr(summary, "failed", 0)
                    total_errors += getattr(summary, "errors", 0)
                    total_skipped += getattr(summary, "skipped", 0)
            elif hasattr(report, "summary"):
                # If report is an object with a summary attribute
                summary = report.summary
                if isinstance(summary, dict):
                    total_tests += summary.get("total_tests", 0)
                    total_passed += summary.get("passed", 0)
                    total_failed += summary.get("failed", 0)
                    total_errors += summary.get("errors", 0)
                    total_skipped += summary.get("skipped", 0)
                else:
                    total_tests += getattr(summary, "total_tests", 0)
                    total_passed += getattr(summary, "passed", 0)
                    total_failed += getattr(summary, "failed", 0)
                    total_errors += getattr(summary, "errors", 0)
                    total_skipped += getattr(summary, "skipped", 0)

        # Calculate success rate
        success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0

        # Create summary
        summary = TestSummary(
            total_tests=total_tests,
            passed=total_passed,
            failed=total_failed,
            errors=total_errors,
            skipped=total_skipped,
            success_rate=success_rate,
        )

        # Create execution model
        execution_id = str(uuid4())
        execution = TestExecutionModel(
            id=execution_id,
            collection_id=collection_id,
            collection_name=collection_name,
            timestamp=datetime.now(),
            reports=reports,
            summary=summary,
        )

        # Save the execution
        await self._save_execution(execution)

        return execution

    async def _save_execution(self, execution: TestExecutionModel) -> None:
        """Save an execution record to file.

        Args:
            execution: The execution record to save
        """
        filename = f"execution_{execution.collection_id}_{execution.id}.json"
        filepath = os.path.join(self.executions_dir, filename)

        # Convert to dict and save to file
        with open(filepath, "w") as f:
            json.dump(execution.model_dump(), f, indent=2, default=str)

    async def get_all_executions(self) -> List[TestExecutionModel]:
        """Get all execution records.

        Returns:
            List of all execution records
        """
        executions = []

        try:
            for filename in os.listdir(self.executions_dir):
                if filename.startswith("execution_") and filename.endswith(".json"):
                    filepath = os.path.join(self.executions_dir, filename)
                    try:
                        with open(filepath, "r") as f:
                            data = json.load(f)
                            # Convert timestamps from string to datetime
                            if "timestamp" in data and isinstance(
                                data["timestamp"], str
                            ):
                                try:
                                    data["timestamp"] = datetime.fromisoformat(
                                        data["timestamp"].replace("Z", "+00:00")
                                    )
                                except ValueError:
                                    # Fallback to current time if parsing fails
                                    data["timestamp"] = datetime.now()

                            # Ensure summary has all required fields
                            if "summary" not in data or not isinstance(
                                data["summary"], dict
                            ):
                                data["summary"] = {
                                    "total_tests": 0,
                                    "passed": 0,
                                    "failed": 0,
                                    "errors": 0,
                                    "skipped": 0,
                                    "success_rate": 0,
                                }
                            else:
                                summary = data["summary"]
                                # Add missing fields with default values
                                for field in [
                                    "total_tests",
                                    "passed",
                                    "failed",
                                    "errors",
                                    "skipped",
                                    "success_rate",
                                ]:
                                    if field not in summary:
                                        summary[field] = 0

                            execution = TestExecutionModel(**data)
                            executions.append(execution)
                    except Exception as e:
                        print(f"Error loading execution from {filepath}: {str(e)}")
        except Exception as e:
            print(f"Error accessing executions directory: {str(e)}")

        # Sort by timestamp (newest first)
        return sorted(executions, key=lambda x: x.timestamp, reverse=True)

    async def get_execution_by_id(
        self, execution_id: str
    ) -> Optional[TestExecutionModel]:
        """Get an execution record by ID.

        Args:
            execution_id: ID of the execution to retrieve

        Returns:
            The execution record if found, None otherwise
        """
        all_executions = await self.get_all_executions()
        for execution in all_executions:
            if execution.id == execution_id:
                return execution
        return None

    async def get_executions_by_collection_id(
        self, collection_id: str
    ) -> List[TestExecutionModel]:
        """Get all execution records for a collection.

        Args:
            collection_id: ID of the collection

        Returns:
            List of execution records for the collection
        """
        all_executions = await self.get_all_executions()
        return [
            execution
            for execution in all_executions
            if execution.collection_id == collection_id
        ]
