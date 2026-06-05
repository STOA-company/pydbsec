"""Tests for OAuth2 token management."""

from datetime import datetime, timedelta

import pytest

from pydbsec.auth import TokenManager
from pydbsec.exceptions import TokenError


class TestTokenManager:
    def test_init_without_token(self):
        tm = TokenManager("key", "secret")
        assert tm._token is None
        assert tm._is_valid() is False

    def test_init_with_valid_token(self):
        tm = TokenManager(
            "key",
            "secret",
            token="test_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert tm._is_valid() is True
        assert tm.token == "test_token"
        assert tm.authorization == "Bearer test_token"

    def test_init_with_expired_token(self):
        tm = TokenManager(
            "key",
            "secret",
            token="expired_token",
            token_type="Bearer",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert tm._is_valid() is False

    def test_token_expiring_soon(self):
        """Token with less than 10 minutes remaining should be invalid."""
        tm = TokenManager(
            "key",
            "secret",
            token="expiring_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(minutes=5),
        )
        assert tm._is_valid() is False

    def test_token_request_success(self, httpx_mock):
        httpx_mock.add_response(
            url="https://openapi.dbsec.co.kr:8443/oauth2/token",
            method="POST",
            json={
                "access_token": "new_token_123",
                "expires_in": 86400,
                "token_type": "Bearer",
            },
        )
        tm = TokenManager("test_key", "test_secret")
        token = tm.token
        assert token == "new_token_123"
        assert tm.token_type == "Bearer"
        assert tm.expires_at is not None

    def test_token_request_failure_4xx_no_retry(self, httpx_mock):
        # 4xx(인증 오류)는 재시도하지 않고 즉시 실패한다 — 단일 응답만 등록(소비 검증).
        httpx_mock.add_response(
            url="https://openapi.dbsec.co.kr:8443/oauth2/token",
            method="POST",
            status_code=401,
            json={"error": "invalid_client", "error_description": "Invalid appkey"},
        )
        tm = TokenManager("bad_key", "bad_secret")
        with pytest.raises(TokenError) as exc_info:
            _ = tm.token
        assert exc_info.value.status_code == 401
        assert len(httpx_mock.get_requests()) == 1  # 재시도 없음

    def test_token_request_retries_on_5xx(self, httpx_mock, monkeypatch):
        # 5xx(일시적)는 재시도한다 — 3회 모두 실패하면 TokenError.
        monkeypatch.setattr("pydbsec.auth._RETRY_WAIT_SECONDS", 0)
        for _ in range(3):
            httpx_mock.add_response(
                url="https://openapi.dbsec.co.kr:8443/oauth2/token",
                method="POST",
                status_code=503,
                json={"error": "service_unavailable"},
            )
        tm = TokenManager("k", "s")
        with pytest.raises(TokenError):
            _ = tm.token
        assert len(httpx_mock.get_requests()) == 3  # 3회 재시도

    def test_revoke_token(self, httpx_mock):
        httpx_mock.add_response(
            url="https://openapi.dbsec.co.kr:8443/oauth2/revoke",
            method="POST",
            json={"code": 200, "message": "success"},
        )
        tm = TokenManager(
            "key",
            "secret",
            token="token_to_revoke",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        result = tm.revoke()
        assert result["code"] == 200
        assert tm._token is None

    def test_revoke_no_token(self):
        tm = TokenManager("key", "secret")
        result = tm.revoke()
        assert result["code"] == 400

    def test_custom_base_url(self, httpx_mock):
        """Token requests should use the custom base_url."""
        custom_url = "https://sandbox.dbsec.co.kr:8443"
        httpx_mock.add_response(
            url=f"{custom_url}/oauth2/token",
            method="POST",
            json={"access_token": "sandbox_token", "expires_in": 86400, "token_type": "Bearer"},
        )
        tm = TokenManager("key", "secret", base_url=custom_url)
        token = tm.token
        assert token == "sandbox_token"

    def test_revoke_uses_custom_base_url(self, httpx_mock):
        """Revoke should also use the custom base_url."""
        custom_url = "https://sandbox.dbsec.co.kr:8443"
        httpx_mock.add_response(
            url=f"{custom_url}/oauth2/revoke",
            method="POST",
            json={"code": 200, "message": "success"},
        )
        tm = TokenManager(
            "key",
            "secret",
            base_url=custom_url,
            token="tok",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        result = tm.revoke()
        assert result["code"] == 200
