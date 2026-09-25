"""Dynamic "closest restaurant" zone for the Sunset Boulevard integration.

Home Assistant has no zone *entity platform* for integrations to add to, so
this writes a ``zone.*`` state directly to the state machine and keeps it
centered on the nearest restaurant to the configured tracker.

What this supports and what it does not:

* Honored by ``zone`` automation triggers/conditions and rendered on the map
  (it exposes ``latitude``/``longitude``/``radius`` like any zone).
* It does NOT rename a person's state to the zone: that is reserved for zones
  the ``zone`` integration itself manages, and this is not one of them. Use a
  ``zone`` trigger on this zone instead.

One zone is created per config entry, so each tracked person gets their own
"closest" zone rather than sharing a single global one.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import slugify

from .const import CONF_DEVICE_TRACKER, DOMAIN, ZONE_RADIUS
from .helpers import closest_location, tracker_coordinates

if TYPE_CHECKING:
    from . import SunsetBoulevardCoordinator

_LOGGER = logging.getLogger(__name__)


class ClosestLocationZone:
    """Maintains a ``zone.*`` state on the nearest restaurant to the tracker."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: SunsetBoulevardCoordinator,
    ) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._tracker_entity_id: str = entry.data[CONF_DEVICE_TRACKER]
        # Unique per tracker so multiple config entries don't collide.
        tracker_object_id = self._tracker_entity_id.split(".", 1)[-1]
        self.entity_id = "zone." + slugify(f"{DOMAIN}_closest_{tracker_object_id}")
        self._unsubscribe: list[Callable[[], None]] = []
        self._written = False

    @callback
    def async_start(self) -> None:
        """Begin tracking and write the initial zone state."""
        self._unsubscribe.append(
            self._coordinator.async_add_listener(self._async_update)
        )
        self._unsubscribe.append(
            async_track_state_change_event(
                self.hass, [self._tracker_entity_id], self._async_tracker_changed
            )
        )
        self._async_update()

    @callback
    def async_stop(self) -> None:
        """Stop tracking and remove the zone from the state machine."""
        while self._unsubscribe:
            self._unsubscribe.pop()()
        self._async_remove()

    @callback
    def _async_tracker_changed(self, event: Event) -> None:
        self._async_update()

    @callback
    def _async_update(self) -> None:
        coordinates = tracker_coordinates(self.hass, self._tracker_entity_id)
        closest = None
        distance_m: float | None = None
        if coordinates is not None:
            closest, distance_m = closest_location(
                self._coordinator.data or [], coordinates
            )

        if closest is None:
            # No fix or no data — drop the zone rather than leave a stale pin.
            self._async_remove()
            return

        inside = distance_m is not None and distance_m <= ZONE_RADIUS
        self.hass.states.async_set(
            self.entity_id,
            # A zone's state is the number of trackers inside it; we follow one.
            1 if inside else 0,
            {
                "hidden": False,
                "latitude": closest.latitude,
                "longitude": closest.longitude,
                "radius": ZONE_RADIUS,
                "passive": False,
                "editable": False,
                "icon": "mdi:french-fries",
                "friendly_name": "Closest Sunset Boulevard",
                "restaurant": closest.name,
            },
        )
        self._written = True

    @callback
    def _async_remove(self) -> None:
        if self._written:
            self.hass.states.async_remove(self.entity_id)
            self._written = False
