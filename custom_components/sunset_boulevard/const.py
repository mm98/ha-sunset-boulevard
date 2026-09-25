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

CONF_DEVICE_TRACKER: Final = "device_tracker"

# Entries either follow a tracker (the original kind, which has no entry type)
# or put every restaurant on the map. Only one entry of the second kind exists.
CONF_ENTRY_TYPE: Final = "entry_type"
ENTRY_TYPE_ALL_RESTAURANTS: Final = "all_restaurants"

UPDATE_INTERVAL: Final = timedelta(hours=24)

# Radius in meters of the dynamic "closest restaurant" zone: the tracker
# counts as inside it once within this distance of the nearest restaurant.
ZONE_RADIUS: Final = 100
