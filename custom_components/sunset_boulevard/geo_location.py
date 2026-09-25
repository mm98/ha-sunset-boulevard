"""Every restaurant on the map, once, however many people are followed."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE, Platform, UnitOfLength
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import slugify
from homeassistant.util.hass_dict import HassKey
from homeassistant.util.location import distance

from . import SunsetBoulevardConfigEntry
from .const import DOMAIN
from .locations import SunsetBoulevardLocation

# Nothing is polled per entity, the coordinator pushes every update.
PARALLEL_UPDATES = 0


class RestaurantFeed:
	"""Picks the one loaded entry that shows the restaurants.

	Every entry follows a person, but the restaurants are the same for all of
	them. The first entry shows them, and when it unloads the next one takes
	over. The entities keep their registry entries, so their ids, names and
	hidden state carry over.
	"""

	def __init__(self) -> None:
		"""Start with no entry showing the restaurants."""
		self.provider: str | None = None
		self._waiting: dict[str, Callable[[], None]] = {}

	@callback
	def async_join(self, entry_id: str, start: Callable[[], None]) -> None:
		"""Show the restaurants from this entry, or wait until it is its turn."""
		if self.provider is None:
			self.provider = entry_id
			start()
		else:
			self._waiting[entry_id] = start

	@callback
	def async_leave(self, hass: HomeAssistant, entry_id: str) -> None:
		"""Hand the restaurants to the next entry when this one unloads."""
		self._waiting.pop(entry_id, None)
		if self.provider != entry_id:
			return
		self.provider = None
		if hass.is_stopping or not self._waiting:
			return
		self.provider = next(iter(self._waiting))
		self._waiting.pop(self.provider)()


DATA_FEED: HassKey[RestaurantFeed] = HassKey(f"{DOMAIN}_restaurant_feed")


def restaurant_key(location: SunsetBoulevardLocation) -> str:
	"""A stable id for a restaurant: the name of its page, else its own name."""
	if location.link and (page := location.link.rstrip("/").rsplit("/", 1)[-1]):
		return slugify(page)
	return slugify(location.name)


async def async_setup_entry(
	hass: HomeAssistant,
	entry: SunsetBoulevardConfigEntry,
	async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
	"""Show the restaurants, unless another entry already does."""
	feed = hass.data.setdefault(DATA_FEED, RestaurantFeed())

	@callback
	def _start() -> None:
		_async_show_restaurants(hass, entry, async_add_entities)

	@callback
	def _leave() -> None:
		feed.async_leave(hass, entry.entry_id)

	entry.async_on_unload(_leave)
	feed.async_join(entry.entry_id, _start)


@callback
def _async_show_restaurants(
	hass: HomeAssistant,
	entry: SunsetBoulevardConfigEntry,
	async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
	"""Add, update and remove restaurants as the list changes."""
	coordinator = entry.runtime_data.coordinator
	entities: dict[str, RestaurantLocation] = {}

	def _current() -> dict[str, SunsetBoulevardLocation]:
		restaurants: dict[str, SunsetBoulevardLocation] = {}
		for location in coordinator.data or []:
			restaurants.setdefault(restaurant_key(location), location)
		return restaurants

	# Registry entries are kept, so renamed or hidden restaurants stay that way.
	# Remove only those for restaurants that closed while Home Assistant was off.
	registry = er.async_get(hass)
	current = _current()
	for registry_entry in list(registry.entities.values()):
		if (
			registry_entry.platform == DOMAIN
			and registry_entry.domain == Platform.GEO_LOCATION
			and registry_entry.unique_id not in current
		):
			registry.async_remove(registry_entry.entity_id)

	@callback
	def _sync() -> None:
		# After a failed download the restaurants stay as they were.
		if not coordinator.last_update_success:
			return
		current = _current()
		for key in entities.keys() - current.keys():
			entities.pop(key).async_forget()
		new_entities: list[RestaurantLocation] = []
		for key, location in current.items():
			if (entity := entities.get(key)) is None:
				entities[key] = entity = RestaurantLocation(hass, key, location)
				new_entities.append(entity)
			else:
				entity.async_update_from(location)
		if new_entities:
			async_add_entities(new_entities)

	@callback
	def _home_moved(event: Event) -> None:
		for entity in entities.values():
			entity.async_update_distance()

	_sync()
	entry.async_on_unload(coordinator.async_add_listener(_sync))
	entry.async_on_unload(hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, _home_moved))


class RestaurantLocation(GeolocationEvent):
	"""A restaurant on the map, with its distance from home as state."""

	_attr_should_poll = False
	_attr_source = DOMAIN
	_attr_unit_of_measurement = UnitOfLength.KILOMETERS
	_attr_translation_key = "restaurant"
	# Set on the entity rather than in icons.json, so the state carries an icon
	# attribute that a map card can show with label_mode: icon.
	_attr_icon = "mdi:french-fries"

	def __init__(
		self, hass: HomeAssistant, key: str, location: SunsetBoulevardLocation
	) -> None:
		"""Create the entity from the restaurant list."""
		self._config = hass.config
		self._attr_unique_id = key
		self.entity_id = f"{Platform.GEO_LOCATION}.{DOMAIN}_{key}"
		self._location = location
		self._apply(location)

	def _apply(self, location: SunsetBoulevardLocation) -> None:
		self._attr_name = location.name
		self._attr_latitude = location.latitude
		self._attr_longitude = location.longitude
		self._attr_distance = self._distance_from_home()
		attributes: dict[str, Any] = {
			"address": location.address,
			"venue": location.venue,
			"street": location.street,
			"postal": location.postal,
			"city": location.city,
			"link": location.link,
		}
		self._attr_extra_state_attributes = {
			key: value for key, value in attributes.items() if value is not None
		}

	def _distance_from_home(self) -> float | None:
		meters = distance(
			self._config.latitude,
			self._config.longitude,
			self._location.latitude,
			self._location.longitude,
		)
		return None if meters is None else meters / 1000

	@callback
	def async_update_from(self, location: SunsetBoulevardLocation) -> None:
		"""Take a changed address or position from the restaurant list."""
		if location == self._location:
			return
		self._location = location
		self._apply(location)
		if self.hass is not None:
			self.async_write_ha_state()

	@callback
	def async_update_distance(self) -> None:
		"""Measure again after the home location changed."""
		self._attr_distance = self._distance_from_home()
		if self.hass is not None:
			self.async_write_ha_state()

	@callback
	def async_forget(self) -> None:
		"""Remove the entity and its registry entry once the restaurant is gone."""
		if self.hass is None:
			return
		registry = er.async_get(self.hass)
		if self.registry_entry is not None and registry.async_get(self.entity_id):
			# Removing the registry entry also removes the entity.
			registry.async_remove(self.entity_id)
		else:
			self.hass.async_create_task(self.async_remove(force_remove=True))
