"""Sensor platform — one entity per value on each Telldus sensor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_KIND_BAROMETRIC,
    SENSOR_KIND_DEW,
    SENSOR_KIND_HUMIDITY,
    SENSOR_KIND_LUM,
    SENSOR_KIND_RAINRATE,
    SENSOR_KIND_RAINTOTAL,
    SENSOR_KIND_TEMP,
    SENSOR_KIND_UV,
    SENSOR_KIND_WATT,
    SENSOR_KIND_WINDAVG,
    SENSOR_KIND_WINDDIR,
    SENSOR_KIND_WINDGUST,
)
from .coordinator import TelldusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


# (device_class, unit, state_class, nice name)
_KIND_META: dict[str, tuple[SensorDeviceClass | None, str | None, SensorStateClass | None, str]] = {
    SENSOR_KIND_TEMP: (
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
        "Temperature",
    ),
    SENSOR_KIND_HUMIDITY: (
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
        "Humidity",
    ),
    SENSOR_KIND_WATT: (
        SensorDeviceClass.POWER,
        UnitOfPower.WATT,
        SensorStateClass.MEASUREMENT,
        "Power",
    ),
    SENSOR_KIND_LUM: (
        SensorDeviceClass.ILLUMINANCE,
        "lx",
        SensorStateClass.MEASUREMENT,
        "Luminance",
    ),
    SENSOR_KIND_UV: (None, "UV", SensorStateClass.MEASUREMENT, "UV index"),
    SENSOR_KIND_RAINRATE: (None, "mm/h", SensorStateClass.MEASUREMENT, "Rain rate"),
    SENSOR_KIND_RAINTOTAL: (
        None,
        "mm",
        SensorStateClass.TOTAL_INCREASING,
        "Rain total",
    ),
    SENSOR_KIND_WINDDIR: (None, "°", SensorStateClass.MEASUREMENT, "Wind direction"),
    SENSOR_KIND_WINDAVG: (None, "m/s", SensorStateClass.MEASUREMENT, "Wind avg"),
    SENSOR_KIND_WINDGUST: (None, "m/s", SensorStateClass.MEASUREMENT, "Wind gust"),
    SENSOR_KIND_BAROMETRIC: (
        SensorDeviceClass.PRESSURE,
        "kPa",
        SensorStateClass.MEASUREMENT,
        "Pressure",
    ),
    SENSOR_KIND_DEW: (
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
        "Dew point",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TelldusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    known: set[tuple[str, str]] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[TelldusLiveSensor] = []
        for sensor_id, sensor in (coordinator.data or {}).get("sensors", {}).items():
            for value in sensor.get("data", []) or []:
                kind = value.get("name")
                if not kind:
                    continue
                key = (sensor_id, kind)
                if key in known:
                    continue
                known.add(key)
                new_entities.append(TelldusLiveSensor(coordinator, sensor_id, kind))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class TelldusLiveSensor(
    CoordinatorEntity[TelldusDataUpdateCoordinator], SensorEntity
):
    """One value ("temp", "humidity", ...) on a Telldus sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TelldusDataUpdateCoordinator,
        sensor_id: str,
        kind: str,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._kind = kind
        device_class, unit, state_class, pretty = _KIND_META.get(
            kind, (None, None, SensorStateClass.MEASUREMENT, kind)
        )
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_name = pretty
        self._attr_unique_id = f"telldus_sensor_{sensor_id}_{kind}"

    @property
    def _sensor(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get("sensors", {}).get(self._sensor_id)

    @property
    def _value_blob(self) -> dict[str, Any] | None:
        sensor = self._sensor
        if not sensor:
            return None
        for v in sensor.get("data", []) or []:
            if v.get("name") == self._kind:
                return v
        return None

    @property
    def available(self) -> bool:
        return super().available and self._value_blob is not None

    @property
    def native_value(self) -> float | int | str | None:
        blob = self._value_blob
        if not blob:
            return None
        raw = blob.get("value")
        if raw in (None, ""):
            return None
        try:
            # Most values come back as strings like "24.2".
            return float(raw)
        except (TypeError, ValueError):
            return raw

    @property
    def device_info(self) -> DeviceInfo:
        sensor = self._sensor or {}
        return DeviceInfo(
            identifiers={(DOMAIN, f"sensor:{self._sensor_id}")},
            name=sensor.get("name") or f"Telldus sensor {self._sensor_id}",
            manufacturer="Telldus",
            model=sensor.get("protocol") or sensor.get("sensorProtocol") or "Sensor",
            via_device=(DOMAIN, f"client:{sensor.get('clientName', 'telldus')}"),
        )
