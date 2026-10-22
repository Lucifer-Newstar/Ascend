"""Review L12: /health proves the server knows this launch's token, without revealing it."""

from __future__ import annotations

import hashlib
import hmac

from tests.conftest import TOKEN


def test_health_carries_an_hmac_of_the_token(client) -> None:
    body = client.get("/health").json()
    want = hmac.new(TOKEN.encode(), b"ascend-sidecar-health", hashlib.sha256).hexdigest()
    assert body["proof"] == want
    assert TOKEN not in body.values()
