"""DataUpdateCoordinator for Telldus Live."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TelldusApiError, TelldusLiveClient, TelldusRateLimitError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TelldusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /sensors/list and /devices/list on a single cadence."""

    def __init__(self, hass: HomeAssistant, client: TelldusLiveClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            sensors = await self.client.async_get_sensors()
            devices = await self.client.async_get_devices()
        except TelldusRateLimitError as err:
            # 429 survived our in-client retries. Keep whatever we had last
            # cycle instead of flagging every entity as unavailable.
            _LOGGER.warning(
                "Telldus rate-limited us (%s). Keeping stale data this cycle.",
                err,
            )
            if self.data:
                return self.data
            raise UpdateFailed(str(err)) from err
        except TelldusApiError as err:
            raise UpdateFailed(str(err)) from err
        return {
            "sensors": {str(s["id"]): s for s in sensors if "id" in s},
            "devices": {str(d["id"]): d for d in devices if "id" in d},
        }
