"""Utility functions for collection management."""

import asyncio
from core.services.test_collection_service import TestCollectionService
from core.services.test_execution_service import TestExecutionService
from ui.utils import get_summary_value  # Import from common location

# Initialize services
collection_service = TestCollectionService()
execution_service = TestExecutionService()


async def load_collections():
    """Load all collections from the service.

    Returns:
        List of collection objects
    """
    return await collection_service.get_all_collections()


async def load_execution_history():
    """Load all execution history from the service.

    Returns:
        List of execution history objects
    """
    return await execution_service.get_all_executions()
