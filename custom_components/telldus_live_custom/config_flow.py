"""Config flow for the Telldus Live custom integration.

Three steps:
1. user           – collect application public/private keys.
2. authorize      – show the URL the user needs to visit + "Done" button.
3. (validate)     – swap the request token for a persistent access token.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TelldusApiError, TelldusAuthError, TelldusLiveClient
from .const import (
    CONF_PRIVATE_KEY,
    CONF_PUBLIC_KEY,
    CONF_REQUEST_TOKEN,
    CONF_REQUEST_TOKEN_SECRET,
    CONF_TOKEN,
    CONF_TOKEN_SECRET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PUBLIC_KEY): str,
        vol.Required(CONF_PRIVATE_KEY): str,
    }
)


class TelldusLiveCustomFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Telldus Live (custom)."""

    VERSION = 1

    def __init__(self) -> None:
        self._public_key: str | None = None
        self._private_key: str | None = None
        self._request_token: str | None = None
        self._request_token_secret: str | None = None
        self._authorize_url: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect application keys."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._public_key = user_input[CONF_PUBLIC_KEY].strip()
            self._private_key = user_input[CONF_PRIVATE_KEY].strip()

            session = async_get_clientsession(self.hass)
            client = TelldusLiveClient(session, self._public_key, self._private_key)
            try:
                (
                    self._request_token,
                    self._request_token_secret,
                    self._authorize_url,
                ) = await client.async_fetch_request_token()
            except TelldusAuthError as err:
                _LOGGER.warning("Telldus request-token failed: %s", err)
                errors["base"] = "invalid_keys"
            except TelldusApiError as err:
                _LOGGER.warning("Telldus network error: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return await self.async_step_authorize()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={
                "keys_url": "[pa-api.telldus.com/keys/index](https://pa-api.telldus.com/keys/index)"
            },
        )

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the authorize URL and wait for the user to confirm."""
        errors: dict[str, str] = {}
        assert self._authorize_url is not None

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = TelldusLiveClient(
                session, self._public_key or "", self._private_key or ""
            )
            try:
                token, token_secret = await client.async_fetch_access_token(
                    self._request_token or "", self._request_token_secret or ""
                )
            except TelldusAuthError as err:
                _LOGGER.warning("Telldus access-token exchange failed: %s", err)
                errors["base"] = "not_authorized"
            except TelldusApiError as err:
                _LOGGER.warning("Telldus network error during auth: %s", err)
                errors["base"] = "cannot_connect"
            else:
                # Anchor uniqueness on the public key + token so the same
                # Telldus user can't be configured twice.
                await self.async_set_unique_id(f"{self._public_key}:{token}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Telldus Live",
                    data={
                        CONF_PUBLIC_KEY: self._public_key,
                        CONF_PRIVATE_KEY: self._private_key,
                        CONF_TOKEN: token,
                        CONF_TOKEN_SECRET: token_secret,
                        CONF_REQUEST_TOKEN: self._request_token,
                        CONF_REQUEST_TOKEN_SECRET: self._request_token_secret,
                    },
                )

        return self.async_show_form(
            step_id="authorize",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "authorize_url": f"[Open the Telldus authorization page]({self._authorize_url})"
            },
        )
