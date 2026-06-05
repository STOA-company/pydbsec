"""OAuth2 token management for DB Securities OpenAPI."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Any

import httpx

from .constants import BASE_URL, OAUTH_REVOKE_URL, OAUTH_TOKEN_URL
from .exceptions import TokenError

logger = logging.getLogger("pydbsec")

# Token is considered expiring if less than this many minutes remain
_TOKEN_REFRESH_MARGIN_MINUTES = 10
_MAX_TOKEN_RETRIES = 3
_RETRY_WAIT_SECONDS = 5


class TokenManager:
    """Manages OAuth2 token lifecycle for DB Securities API."""

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        *,
        base_url: str = BASE_URL,
        token: str | None = None,
        token_type: str | None = None,
        expires_at: datetime | None = None,
    ):
        self._app_key = app_key
        self._app_secret = app_secret
        self._base_url = base_url
        self._token = token
        self._token_type = token_type
        self._expires_at = expires_at
        self._lock = threading.Lock()

    @property
    def token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if not self._is_valid():
            with self._lock:
                if not self._is_valid():
                    self._request_token()
        return self._token  # type: ignore[return-value]

    @property
    def token_type(self) -> str | None:
        return self._token_type

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    @property
    def authorization(self) -> str:
        """Return the Authorization header value."""
        return f"{self._token_type} {self.token}"

    def _is_valid(self) -> bool:
        if not self._token or not self._token_type or not self._expires_at:
            return False
        return datetime.now() + timedelta(minutes=_TOKEN_REFRESH_MARGIN_MINUTES) < self._expires_at

    def refresh(self) -> None:
        """Force token refresh."""
        with self._lock:
            self._request_token()

    def _request_token(self) -> None:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self._app_key,
            "appsecretkey": self._app_secret,
            "scope": "oob",
        }

        last_error: Exception | None = None
        for attempt in range(1, _MAX_TOKEN_RETRIES + 1):
            try:
                logger.debug("Requesting access token (attempt %d/%d)", attempt, _MAX_TOKEN_RETRIES)
                response = httpx.post(f"{self._base_url}{OAUTH_TOKEN_URL}", headers=headers, data=data, timeout=30)
                response.raise_for_status()
                token_data: dict[str, Any] = response.json()

                self._token = token_data["access_token"]
                expires_in = int(token_data.get("expires_in", 86400))
                self._expires_at = datetime.now() + timedelta(seconds=expires_in)
                self._token_type = token_data.get("token_type", "Bearer")
                logger.info("Access token obtained, valid until %s", self._expires_at)
                return
            except httpx.HTTPStatusError as e:
                last_error = e
                body = _safe_json(e.response)
                logger.warning(
                    "Token request failed (attempt %d): status=%d body=%s",
                    attempt,
                    e.response.status_code,
                    body,
                )
                if 400 <= e.response.status_code < 500:
                    # 인증/요청 오류(4xx, 예: 잘못된 AppKey)는 재시도해도 동일하므로 즉시 전파.
                    # (재시도는 네트워크/5xx 같은 일시적 오류에만 의미가 있다)
                    raise TokenError(
                        "Token request rejected by DB Securities",
                        status_code=e.response.status_code,
                        response_body=body,
                    ) from e
            except httpx.HTTPError as e:
                last_error = e
                logger.warning("Token request failed (attempt %d): %s", attempt, e)

            if attempt < _MAX_TOKEN_RETRIES:
                import time

                time.sleep(_RETRY_WAIT_SECONDS * attempt)

        final_status_code = None
        final_body: dict[str, Any] | str | None = None
        if isinstance(last_error, httpx.HTTPStatusError):
            final_status_code = last_error.response.status_code
            final_body = _safe_json(last_error.response)

        raise TokenError(
            f"Failed to obtain access token after {_MAX_TOKEN_RETRIES} attempts",
            status_code=final_status_code,
            response_body=final_body,
        )

    def revoke(self) -> dict[str, Any]:
        """Revoke the current access token."""
        if not self._token:
            return {"code": 400, "message": "No token to revoke"}

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "appkey": self._app_key,
            "appsecretkey": self._app_secret,
            "token": self._token,
            "token_type_hint": "access_token",
        }
        response = httpx.post(f"{self._base_url}{OAUTH_REVOKE_URL}", headers=headers, data=data, timeout=30)
        response.raise_for_status()
        result: dict[str, Any] = response.json()

        if result.get("code") == 200:
            self._token = None
            self._token_type = None
            self._expires_at = None
            logger.info("Token revoked successfully")

        return result


def _safe_json(response: httpx.Response) -> dict[str, Any] | str:
    try:
        return response.json()  # type: ignore[no-any-return]
    except Exception:
        return response.text
