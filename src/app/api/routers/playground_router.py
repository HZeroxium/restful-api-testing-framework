from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict
import time
import httpx

from app.api.dto.playground_dto import (
    PlaygroundExecuteRequest,
    PlaygroundExecuteResponse,
)


router = APIRouter(prefix="/api/v1/playground", tags=["Playground"])


async def _execute_http(req: PlaygroundExecuteRequest) -> PlaygroundExecuteResponse:
    method = req.method.upper()
    base = req.base_url.rstrip("/")
    path = (req.path or "").lstrip("/")
    url = f"{base}/{path}" if path else base

    timeout = httpx.Timeout(req.timeout or 15.0)
    transport = httpx.AsyncHTTPTransport(retries=req.retries or 2)

    start = time.time()
    async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
        try:
            resp = await client.request(
                method=method,
                url=url,
                params=req.params or None,
                headers=req.headers or None,
                json=req.body if method in {"POST", "PUT", "PATCH"} else None,
            )

            elapsed_ms = (time.time() - start) * 1000.0

            # Truncate very large bodies to keep UI responsive
            body: Any
            try:
                body = resp.json()
            except Exception:
                body = resp.text
                if body and len(body) > 200_000:
                    body = body[:200_000] + "\n/* truncated */"

            return PlaygroundExecuteResponse(
                url=str(resp.request.url),
                status_code=resp.status_code,
                headers=dict(resp.headers),
                body=body,
                elapsed_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000.0
            return PlaygroundExecuteResponse(
                url=url,
                status_code=0,
                headers={},
                body=None,
                elapsed_ms=elapsed_ms,
                error=str(e),
            )


@router.post(
    "/execute",
    response_model=PlaygroundExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute an HTTP request",
)
async def execute(req: PlaygroundExecuteRequest) -> PlaygroundExecuteResponse:
    return await _execute_http(req)
