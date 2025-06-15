# tools/rest_api_caller.py

import time
from typing import Optional

import httpx

from core import BaseTool
from schemas.tools.rest_api_caller import (
    RestApiCallerInput,
    RestApiCallerOutput,
    RestRequest,
    RestResponse,
)
from common.logger import LoggerFactory, LoggerType, LogLevel


class RestApiCallerTool(BaseTool):
    """
    A BaseTool that performs asynchronous REST calls via HTTPX.
    Strictly focuses on HTTP logic; I/O is external.
    """

    def __init__(
        self,
        *,
        name: str = "rest_api_caller",
        description: str = "Calls RESTful endpoints using httpx.AsyncClient",
        config: Optional[dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=RestApiCallerInput,
            output_schema=RestApiCallerOutput,
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

        # You can accept config overrides for timeouts, retries, etc.
        self._timeout = config.get("timeout", 10.0) if config else 10.0

    async def _execute(self, inp: RestApiCallerInput) -> RestApiCallerOutput:
        req: RestRequest = inp.request  # already validated by Pydantic

        self.logger.info(f"Making {req.method.upper()} request to {req.url}")
        self.logger.add_context(
            method=req.method.upper(),
            url=req.url,
            has_params=bool(req.params),
            has_headers=bool(req.headers),
            has_json=bool(req.json),
            timeout=self._timeout,
        )

        start = time.perf_counter()

        try:
            # Use a shared AsyncClient for connection pooling
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                self.logger.debug("Executing HTTP request")

                # Dynamically choose the HTTP method
                response = await client.request(
                    method=req.method.upper(),
                    url=req.url,
                    headers=req.headers or {},
                    params=req.params or {},
                    json=req.json,
                )

            elapsed = time.perf_counter() - start

            self.logger.info(
                f"Request completed: {response.status_code} in {elapsed:.3f}s"
            )
            self.logger.add_context(
                status_code=response.status_code,
                response_time=f"{elapsed:.3f}s",
                response_size=len(response.content) if response.content else 0,
            )

            # Wrap into our Response schema
            resp_model = RestResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=(
                    response.json()
                    if "application/json" in response.headers.get("content-type", "")
                    else response.text
                ),
            )

            return RestApiCallerOutput(
                request=req, response=resp_model, elapsed=elapsed
            )

        except httpx.TimeoutException as e:
            elapsed = time.perf_counter() - start
            self.logger.error(f"Request timed out after {self._timeout}s")
            raise
        except httpx.RequestError as e:
            elapsed = time.perf_counter() - start
            self.logger.error(f"Request error: {str(e)}")
            raise
        except Exception as e:
            elapsed = time.perf_counter() - start
            self.logger.error(f"Unexpected error during request: {str(e)}")
            raise

    async def cleanup(self) -> None:
        # Nothing to clean up here
        self.logger.debug("RestApiCallerTool cleanup completed")
