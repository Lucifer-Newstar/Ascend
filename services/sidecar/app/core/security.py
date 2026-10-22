"""Localhost-only bearer-token auth.

Electron main generates a random token per launch and hands it to the sidecar
on stdin, so other local processes or web pages cannot call the API.
"""

from __future__ import annotations

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

# /health is polled before the token is in use; the API docs expose schema only, never data.
OPEN_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "testserver"}


HEALTH_PROOF_LABEL = b"ascend-sidecar-health"


def health_proof(token: str) -> str:
    """HMAC of a fixed label under this launch's token, returned by the open /health.
    Electron compares it with its own before it sends the token anywhere: a process that
    grabbed the port between freePort() and the sidecar's bind cannot produce it, so it
    never receives the token (review L12)."""
    return hmac.new(token.encode(), HEALTH_PROOF_LABEL, "sha256").hexdigest()


class TokenAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ALLOWED_HOSTS:
            # Blocks DNS-rebinding: a web page can't reach us via evil.example -> 127.0.0.1
            return JSONResponse({"detail": "bad host"}, status_code=403)
        if request.method == "OPTIONS" or request.url.path in OPEN_PATHS:
            return await call_next(request)
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        if (
            not self._token
            or scheme != "Bearer"
            or not hmac.compare_digest(supplied.strip(), self._token)
        ):
            return JSONResponse({"detail": "unauthorised"}, status_code=401)
        return await call_next(request)
