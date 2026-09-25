"""Sensor platform for the Sunset Boulevard integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
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
    """Set up the Sunset Boulevard sensors."""
    data: SunsetBoulevardData = hass.data[DOMAIN][entry.entry_id]
    coordinator = data.coordinator
    async_add_entities(
        [
            ClosestLocationSensor(coordinator, entry),
            DistanceSensor(coordinator, entry),
        ]
    )


class SunsetBoulevardSensor(ClosestLocationEntity, SensorEntity):
    """Base sensor tracking the restaurant closest to the configured tracker."""


class ClosestLocationSensor(SunsetBoulevardSensor):
    """Address of the closest restaurant, with its position as attributes."""

    _attr_translation_key = "closest_location"
    _attr_icon = "mdi:french-fries"

    def __init__(
        self, coordinator: SunsetBoulevardCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_closest_location"

    @property
    def native_value(self) -> str | None:
        return self._closest.address if self._closest else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._closest is None:
            return None
        attributes: dict[str, Any] = {
            "name": self._closest.name,
            "latitude": self._closest.latitude,
            "longitude": self._closest.longitude,
            "source": self._tracker_entity_id,
        }
        if self._closest.venue:
            attributes["venue"] = self._closest.venue
        if self._closest.street:
            attributes["street"] = self._closest.street
        if self._closest.postal:
            attributes["postal"] = self._closest.postal
        if self._closest.city:
            attributes["city"] = self._closest.city
        if self._closest.link:
            attributes["link"] = self._closest.link
        if self._distance_m is not None:
            attributes["distance_km"] = round(self._distance_m / 1000, 2)
        return attributes


class DistanceSensor(SunsetBoulevardSensor):
    """Distance to the closest restaurant in kilometers."""

    _attr_translation_key = "distance"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator: SunsetBoulevardCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_distance"

    @property
    def native_value(self) -> float | None:
        if self._distance_m is None:
            return None
        return round(self._distance_m / 1000, 3)
