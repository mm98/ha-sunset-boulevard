"""Device tracker platform for the Sunset Boulevard integration.

Publishes an entity positioned at the restaurant closest to the configured
tracker. Unlike the dynamic zone, this is a proper entity on the integration's
device: it shows on the map natively and its state resolves against your zones
(so it reads ``home`` if a restaurant ever falls inside your home zone,
otherwise ``not_home``).
"""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SunsetBoulevardCoordinator, SunsetBoulevardData
from .const import DOMAIN
from .entity import ClosestLocationEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sunset Boulevard device tracker."""
    data: SunsetBoulevardData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ClosestLocationTracker(data.coordinator, entry)])


class ClosestLocationTracker(ClosestLocationEntity, TrackerEntity):
    """A tracker positioned at the closest restaurant."""

    _attr_translation_key = "closest_location"
    _attr_icon = "mdi:french-fries"

    def __init__(
        self, coordinator: SunsetBoulevardCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_closest_tracker"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self._closest.latitude if self._closest else None

    @property
    def longitude(self) -> float | None:
        return self._closest.longitude if self._closest else None
