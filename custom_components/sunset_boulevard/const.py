"""Constants for the Sunset Boulevard integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "sunset_boulevard"
LOCATIONS_URL: Final = "https://sunset-boulevard.dk/restauranter/"

# The site's firewall rejects requests (HTTP 455/454) unless they carry both
# a realistic browser User-Agent and an Accept-Language header.
FETCH_HEADERS: Final = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "da,en;q=0.9",
}

# The logo shipped in brand/, served without login so map markers can show it.
# The brands API under /api/brands needs a login, which gives a 403 in a browser.
LOGO_URL: Final = f"/{DOMAIN}/logo.png"

CONF_DEVICE_TRACKER: Final = "device_tracker"

UPDATE_INTERVAL: Final = timedelta(hours=24)

# Radius in meters of the dynamic "closest restaurant" zone: the tracker
# counts as inside it once within this distance of the nearest restaurant.
ZONE_RADIUS: Final = 100
