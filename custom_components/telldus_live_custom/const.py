"""Constants for the Telldus Live custom integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "telldus_live_custom"

# API endpoints
API_HOST = "https://pa-api.telldus.com"
API_REQUEST_TOKEN_URL = f"{API_HOST}/oauth/requestToken"
API_AUTHORIZE_URL = f"{API_HOST}/oauth/authorize"
API_ACCESS_TOKEN_URL = f"{API_HOST}/oauth/accessToken"
API_BASE = f"{API_HOST}/json"

# Config entry keys
CONF_PUBLIC_KEY = "public_key"
CONF_PRIVATE_KEY = "private_key"
CONF_TOKEN = "token"
CONF_TOKEN_SECRET = "token_secret"
CONF_REQUEST_TOKEN = "request_token"
CONF_REQUEST_TOKEN_SECRET = "request_token_secret"

# Update interval. Telldus sensor values update every 5–15 minutes at the source,
# so polling faster than this just burns rate limit without getting newer data.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=180)

# Back-off config used when Telldus responds with 429/503.
RETRY_BACKOFF_SECONDS = (5, 15, 45)  # exponential-ish, caps at ~1 min extra per cycle
RETRYABLE_STATUSES = {429, 503}

# Telldus supported-method bitmask values
METHOD_TURNON = 1
METHOD_TURNOFF = 2
METHOD_BELL = 4
METHOD_TOGGLE = 8
METHOD_DIM = 16
METHOD_LEARN = 32
METHOD_EXECUTE = 64
METHOD_UP = 128
METHOD_DOWN = 256
METHOD_STOP = 512

# Full mask used when listing devices so the API returns all methods we care about.
SUPPORTED_METHODS_MASK = (
    METHOD_TURNON
    | METHOD_TURNOFF
    | METHOD_TOGGLE
    | METHOD_DIM
    | METHOD_UP
    | METHOD_DOWN
    | METHOD_STOP
)

# Sensor "name" values returned by the API and how we map them.
# See https://api.telldus.com/documentation/constMethods
SENSOR_KIND_TEMP = "temp"
SENSOR_KIND_HUMIDITY = "humidity"
SENSOR_KIND_WATT = "watt"
SENSOR_KIND_LUM = "lum"
SENSOR_KIND_RAINRATE = "rrate"
SENSOR_KIND_RAINTOTAL = "rtot"
SENSOR_KIND_WINDDIR = "wdir"
SENSOR_KIND_WINDAVG = "wavg"
SENSOR_KIND_WINDGUST = "wgust"
SENSOR_KIND_UV = "uv"
SENSOR_KIND_BAROMETRIC = "barpress"
SENSOR_KIND_DEW = "dewp"

PLATFORMS = ["sensor", "switch"]
