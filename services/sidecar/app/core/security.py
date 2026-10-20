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

OPEN_PATHS = {"/health"}
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "testserver"}


class TokenAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ALLOWED_HOSTS:
            # Blocks DNS-rebinding: a web page can't reach us via evil.example -> 127.0.0.1
            return JSONResponse({"detail": "bad host"}, status_code=403)
        if request.method == "OPTIONS" or request.url.path in OPEN_PATHS:
            return await call_next(request)
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not self._token or not hmac.compare_digest(supplied, self._token):
            return JSONResponse({"detail": "unauthorised"}, status_code=401)
        return await call_next(request)
