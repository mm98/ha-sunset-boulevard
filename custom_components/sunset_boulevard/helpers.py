"""Shared location helpers for the Sunset Boulevard integration.

Used by both the sensor platform and the dynamic zone so they resolve the
tracker position and the nearest restaurant identically.
"""

from __future__ import annotations

from homeassistant.const import STATE_HOME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util.location import distance

from .locations import SunsetBoulevardLocation


def tracker_coordinates(
    hass: HomeAssistant, entity_id: str
) -> tuple[float, float] | None:
    """Return the tracker's position, or home for zone-only trackers."""
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None

    latitude = state.attributes.get("latitude")
    longitude = state.attributes.get("longitude")
    if latitude is not None and longitude is not None:
        return float(latitude), float(longitude)

    # Router-based trackers have no GPS attributes but do report "home".
    if state.state == STATE_HOME:
        return hass.config.latitude, hass.config.longitude
    return None


def closest_location(
    locations: list[SunsetBoulevardLocation],
    coordinates: tuple[float, float],
) -> tuple[SunsetBoulevardLocation | None, float | None]:
    """Return the nearest location to ``coordinates`` and its distance (m)."""
    closest: SunsetBoulevardLocation | None = None
    closest_distance: float | None = None
    for location in locations:
        meters = distance(
            coordinates[0],
            coordinates[1],
            location.latitude,
            location.longitude,
        )
        if meters is None:
            continue
        if closest_distance is None or meters < closest_distance:
            closest = location
            closest_distance = meters
    return closest, closest_distance
