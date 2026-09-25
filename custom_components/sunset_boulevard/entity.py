"""Shared entity base for Sunset Boulevard entities.

Both the sensors and the device tracker follow a configured tracker and, on
every move or feed refresh, recompute the nearest restaurant. That common
behavior lives here so each platform only adds its own presentation.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SunsetBoulevardCoordinator
from .const import CONF_DEVICE_TRACKER, DOMAIN
from .helpers import closest_location, tracker_coordinates
from .locations import SunsetBoulevardLocation


class ClosestLocationEntity(CoordinatorEntity[SunsetBoulevardCoordinator]):
    """Base for entities that follow the restaurant closest to a tracker."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SunsetBoulevardCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._tracker_entity_id: str = entry.data[CONF_DEVICE_TRACKER]
        self._closest: SunsetBoulevardLocation | None = None
        self._distance_m: float | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Sunset Boulevard",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://sunset-boulevard.dk/",
        )

    async def async_added_to_hass(self) -> None:
        """Recompute on tracker moves in addition to coordinator refreshes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._tracker_entity_id], self._async_tracker_changed
            )
        )
        self._recompute()

    @callback
    def _async_tracker_changed(self, event: Event) -> None:
        self._recompute()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._recompute()
        super()._handle_coordinator_update()

    @callback
    def _recompute(self) -> None:
        coordinates = tracker_coordinates(self.hass, self._tracker_entity_id)
        if coordinates is None:
            self._closest = None
            self._distance_m = None
            return
        self._closest, self._distance_m = closest_location(
            self.coordinator.data or [], coordinates
        )
