# tools/rest_api_caller.py

import time
from typing import Optional

import httpx

from core import BaseTool
from schemas.tools.rest_api_caller import (
    RESTAPICallerInput,
    RESTAPICallerOutput,
    RESTRequest,
    RESTResponse,
)


class RESTAPICallerTool(BaseTool):
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
            input_schema=RESTAPICallerInput,
            output_schema=RESTAPICallerOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        # You can accept config overrides for timeouts, retries, etc.
        self._timeout = config.get("timeout", 10.0) if config else 10.0

    async def _execute(self, inp: RESTAPICallerInput) -> RESTAPICallerOutput:
        req: RESTRequest = inp.request  # already validated by Pydantic
        start = time.perf_counter()

        # Use a shared AsyncClient for connection pooling :contentReference[oaicite:6]{index=6}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            # Dynamically choose the HTTP method
            response = await client.request(
                method=req.method.upper(),
                url=req.url,
                headers=req.headers or {},
                params=req.params or {},
                json=req.json,
            )

        elapsed = time.perf_counter() - start

        # Wrap into our Response schema
        resp_model = RESTResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=(
                response.json()
                if "application/json" in response.headers.get("content-type", "")
                else response.text
            ),
        )

        return RESTAPICallerOutput(response=resp_model, elapsed=elapsed)

    async def cleanup(self) -> None:
        # Nothing to clean up here
        pass
