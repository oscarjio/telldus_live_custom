"""Async OAuth1 client for the Telldus Live API.

OAuth1 is signed with HMAC-SHA1 over a normalized parameter string. We use
oauthlib to build the signed request, then dispatch it with aiohttp so the
Home Assistant event loop is never blocked.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import parse_qs

import aiohttp
from oauthlib.oauth1 import Client as OAuth1Client

from .const import (
    API_ACCESS_TOKEN_URL,
    API_BASE,
    API_REQUEST_TOKEN_URL,
    API_AUTHORIZE_URL,
    SUPPORTED_METHODS_MASK,
)

_LOGGER = logging.getLogger(__name__)


class TelldusAuthError(Exception):
    """Raised when authentication to Telldus fails."""


class TelldusApiError(Exception):
    """Raised when an API call to Telldus fails."""


class TelldusLiveClient:
    """Thin async wrapper around the Telldus Live OAuth1 API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        public_key: str,
        private_key: str,
        token: str | None = None,
        token_secret: str | None = None,
    ) -> None:
        self._session = session
        self._public_key = public_key
        self._private_key = private_key
        self._token = token
        self._token_secret = token_secret

    # ------------------------------------------------------------------
    # OAuth1 dance
    # ------------------------------------------------------------------
    async def async_fetch_request_token(self) -> tuple[str, str, str]:
        """Step 1: fetch a request token + build the authorize URL."""
        body = await self._signed_request(
            "GET",
            API_REQUEST_TOKEN_URL,
            token=None,
            token_secret=None,
            as_text=True,
        )
        parsed = parse_qs(body)
        try:
            req_token = parsed["oauth_token"][0]
            req_secret = parsed["oauth_token_secret"][0]
        except (KeyError, IndexError) as err:
            raise TelldusAuthError(
                f"Unexpected request-token response: {body!r}"
            ) from err
        authorize_url = f"{API_AUTHORIZE_URL}?oauth_token={req_token}"
        return req_token, req_secret, authorize_url

    async def async_fetch_access_token(
        self, request_token: str, request_token_secret: str
    ) -> tuple[str, str]:
        """Step 3: swap an authorized request token for an access token."""
        body = await self._signed_request(
            "GET",
            API_ACCESS_TOKEN_URL,
            token=request_token,
            token_secret=request_token_secret,
            as_text=True,
        )
        parsed = parse_qs(body)
        try:
            access_token = parsed["oauth_token"][0]
            access_secret = parsed["oauth_token_secret"][0]
        except (KeyError, IndexError) as err:
            raise TelldusAuthError(
                f"Access-token exchange failed. Make sure you clicked "
                f"'Yes' on the authorize page before continuing. "
                f"Server said: {body!r}"
            ) from err
        self._token = access_token
        self._token_secret = access_secret
        return access_token, access_secret

    # ------------------------------------------------------------------
    # Resource calls
    # ------------------------------------------------------------------
    async def async_get_sensors(self) -> list[dict[str, Any]]:
        data = await self._json_get(
            f"{API_BASE}/sensors/list",
            {"includeValues": 1, "includeScale": 1, "includeUnit": 1},
        )
        return list(data.get("sensor", []))

    async def async_get_sensor(self, sensor_id: str) -> dict[str, Any]:
        return await self._json_get(
            f"{API_BASE}/sensor/info",
            {"id": sensor_id},
        )

    async def async_get_devices(self) -> list[dict[str, Any]]:
        data = await self._json_get(
            f"{API_BASE}/devices/list",
            {"supportedMethods": SUPPORTED_METHODS_MASK},
        )
        return list(data.get("device", []))

    async def async_turn_on(self, device_id: str) -> dict[str, Any]:
        return await self._json_get(
            f"{API_BASE}/device/turnOn", {"id": device_id}
        )

    async def async_turn_off(self, device_id: str) -> dict[str, Any]:
        return await self._json_get(
            f"{API_BASE}/device/turnOff", {"id": device_id}
        )

    async def async_dim(self, device_id: str, level: int) -> dict[str, Any]:
        # Telldus dim level is 0-255
        return await self._json_get(
            f"{API_BASE}/device/dim", {"id": device_id, "level": level}
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _json_get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._token or not self._token_secret:
            raise TelldusAuthError("Client has no access token yet")
        # Encode the query string into the URL so oauthlib signs it correctly.
        query = "&".join(f"{k}={v}" for k, v in params.items())
        full = f"{url}?{query}" if query else url
        data = await self._signed_request(
            "GET",
            full,
            token=self._token,
            token_secret=self._token_secret,
            as_text=False,
        )
        if isinstance(data, dict) and "error" in data:
            raise TelldusApiError(str(data["error"]))
        return data  # type: ignore[return-value]

    async def _signed_request(
        self,
        method: str,
        url: str,
        *,
        token: str | None,
        token_secret: str | None,
        as_text: bool,
    ) -> Any:
        """Sign with oauthlib in a thread, then perform the request with aiohttp."""
        uri, headers, body = await asyncio.to_thread(
            self._sign,
            method,
            url,
            token,
            token_secret,
        )
        try:
            async with self._session.request(
                method, uri, headers=headers, data=body, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise TelldusApiError(
                        f"{method} {url} -> HTTP {resp.status}: {text[:200]}"
                    )
                if as_text:
                    return text
                # Telldus occasionally returns empty body on success; guard against that.
                if not text.strip():
                    return {}
                try:
                    import json
                    return json.loads(text)
                except ValueError as err:
                    raise TelldusApiError(
                        f"Invalid JSON from {url}: {text[:200]}"
                    ) from err
        except aiohttp.ClientError as err:
            raise TelldusApiError(f"Network error contacting Telldus: {err}") from err

    def _sign(
        self,
        method: str,
        url: str,
        token: str | None,
        token_secret: str | None,
    ) -> tuple[str, dict[str, str], Any]:
        client = OAuth1Client(
            client_key=self._public_key,
            client_secret=self._private_key,
            resource_owner_key=token,
            resource_owner_secret=token_secret,
        )
        return client.sign(url, http_method=method)
