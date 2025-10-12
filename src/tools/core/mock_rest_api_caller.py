"""
Mock REST API Caller Tool for offline testing.

This tool provides predefined responses without making real HTTP calls,
allowing for testing of the complete pipeline without external dependencies.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from tools.core.rest_api_caller import RestApiCallerTool
from schemas.tools.rest_api_caller import (
    RestApiCallerInput,
    RestApiCallerOutput,
    RestRequest,
    RestResponse,
)


class MockRestApiCallerTool(RestApiCallerTool):
    """Mock REST API caller for testing without real HTTP calls."""

    def __init__(
        self,
        mock_responses: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        **kwargs,
    ):
        """
        Initialize mock REST API caller.

        Args:
            mock_responses: Dictionary mapping URL patterns to mock responses
            verbose: Enable verbose logging
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(verbose=verbose, **kwargs)
        self.mock_responses = mock_responses or {}

        # Default responses for common endpoints
        self.default_responses = {
            "/brands": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {
                    "data": [
                        {
                            "id": "1",
                            "name": "Mock Brand 1",
                            "slug": "mock-brand-1",
                            "description": "A mock brand for testing",
                        },
                        {
                            "id": "2",
                            "name": "Mock Brand 2",
                            "slug": "mock-brand-2",
                            "description": "Another mock brand for testing",
                        },
                    ],
                    "total": 2,
                },
            },
            "/categories": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {
                    "data": [
                        {
                            "id": "1",
                            "name": "Mock Category 1",
                            "slug": "mock-category-1",
                        }
                    ]
                },
            },
            "/products": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {
                    "data": [
                        {
                            "id": "1",
                            "name": "Mock Product 1",
                            "price": 29.99,
                            "category_id": "1",
                        }
                    ]
                },
            },
        }

    def _find_mock_response(self, url: str) -> Dict[str, Any]:
        """
        Find the appropriate mock response for a URL.

        Args:
            url: The request URL

        Returns:
            Mock response data
        """
        # First check exact URL match in mock_responses
        if url in self.mock_responses:
            return self.mock_responses[url]

        # Then check path-based matching
        for pattern, response in self.mock_responses.items():
            if pattern in url:
                return response

        # Check default responses by path
        for path, response in self.default_responses.items():
            if path in url:
                return response

        # Return a generic default response
        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"message": "Mock response", "url": url, "timestamp": time.time()},
        }

    async def _execute(self, inp: RestApiCallerInput) -> RestApiCallerOutput:
        """
        Execute mock API call without making real HTTP requests.

        Args:
            inp: Input containing the request details

        Returns:
            Mock response data
        """
        req: RestRequest = inp.request

        self.logger.info(f"Mock API call: {req.method.upper()} {req.url}")
        self.logger.add_context(method=req.method.upper(), url=req.url, mock_mode=True)

        start = time.perf_counter()

        # Simulate some processing time
        await asyncio.sleep(0.001)

        # Find appropriate mock response
        mock_data = self._find_mock_response(req.url)

        elapsed = time.perf_counter() - start

        self.logger.info(f"Mock response: {mock_data['status_code']} in {elapsed:.3f}s")
        self.logger.add_context(
            status_code=mock_data["status_code"],
            response_time=f"{elapsed:.3f}s",
            mock_mode=True,
        )

        # Create response model
        resp_model = RestResponse(
            status_code=mock_data.get("status_code", 200),
            headers=mock_data.get("headers", {}),
            body=mock_data.get("body", {}),
        )

        return RestApiCallerOutput(request=req, response=resp_model, elapsed=elapsed)

    def add_mock_response(
        self, url_pattern: str, response_data: Dict[str, Any]
    ) -> None:
        """
        Add a mock response for a specific URL pattern.

        Args:
            url_pattern: URL pattern to match
            response_data: Mock response data
        """
        self.mock_responses[url_pattern] = response_data
        self.logger.info(f"Added mock response for pattern: {url_pattern}")

    def clear_mock_responses(self) -> None:
        """Clear all custom mock responses (keeps defaults)."""
        self.mock_responses.clear()
        self.logger.info("Cleared custom mock responses")
