"""Fail-closed SDK behavior tests."""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from sel_v3.client import SELBlockedError, SELClient


def test_fail_closed_blocks_after_timeout() -> None:
    client = SELClient(
        gateway_url="http://127.0.0.1:59999",
        agent_id="autonomous_ops_worker",
        master_secret="test-master-secret-key-32bytes!!",
    )

    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(SELBlockedError):
            client.authorize("execute_web_scrape", {"depth_limit": 1})

    assert client.is_blocked

    with pytest.raises(SELBlockedError, match="fail-closed"):
        client.authorize("execute_web_scrape", {"depth_limit": 1})


def test_http_error_does_not_block_client() -> None:
    client = SELClient(
        gateway_url="http://127.0.0.1:8787",
        agent_id="autonomous_ops_worker",
        master_secret="test-master-secret-key-32bytes!!",
    )

    mock_response = MagicMock()
    mock_response.read.return_value = b'{"error":"CAPABILITY_NOT_PERMITTED"}'
    http_error = urllib.error.HTTPError(
        url="http://127.0.0.1:8787/v1/authorize",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=mock_response,
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        from sel_v3.client import SELAuthorizationError

        with pytest.raises(SELAuthorizationError):
            client.authorize("execute_web_scrape", {"depth_limit": 1})

    assert not client.is_blocked
