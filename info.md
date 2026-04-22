# Telldus Live (custom)

Bring Telldus Live sensors and on/off devices into Home Assistant through the official OAuth1 API.

## Features

- Temperature, humidity, power, illuminance, wind, rain, UV, pressure and dew-point sensors as native HA entities with correct device classes and units.
- On/off switches for every Telldus device that supports `TURNON` / `TURNOFF`.
- Pure UI setup — paste public/private key, approve in the Telldus browser dialog, done.
- Single API poll shared across all entities via a `DataUpdateCoordinator`.

## Setup

1. Install through HACS.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → "Telldus Live (custom)"**.
4. Follow the on-screen steps.

Full setup guide: see [README](README.md).
