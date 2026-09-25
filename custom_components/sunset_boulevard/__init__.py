"""The Sunset Boulevard integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, FETCH_HEADERS, LOCATIONS_URL, UPDATE_INTERVAL
from .locations import SunsetBoulevardLocation, load_postal_map, parse_locations

if TYPE_CHECKING:
    from .zone import ClosestLocationZone

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR]

# Persisted last-known-good copy of the list, shared by all entries (the list
# is identical for every tracker), so a broken page or a cold restart still
# has data to fall back on.
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_locations"


@dataclass
class SunsetBoulevardData:
    """Runtime data stored per config entry."""

    coordinator: SunsetBoulevardCoordinator
    zone: ClosestLocationZone


class SunsetBoulevardCoordinator(
    DataUpdateCoordinator[list[SunsetBoulevardLocation]]
):
    """Fetches and caches the restaurant list from the website."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )
        self._postal_by_city: dict[str, str] | None = None

    async def _async_update_data(self) -> list[SunsetBoulevardLocation]:
        if self._postal_by_city is None:
            try:
                self._postal_by_city = await self.hass.async_add_executor_job(
                    load_postal_map
                )
            except (OSError, ValueError) as err:
                _LOGGER.warning(
                    "Could not load bundled postal codes (%s); addresses"
                    " without one will be left as-is",
                    err,
                )
                self._postal_by_city = {}

        try:
            text = await self._fetch(LOCATIONS_URL)
            locations = parse_locations(text, self._postal_by_city)
        except (TimeoutError, ClientError) as err:
            reason = f"could not fetch the page ({err})"
            locations = []
        else:
            # An empty result means the firewall served a challenge page or the
            # page markup changed.
            reason = "no restaurant markers were found on the page"
            if locations:
                await self._async_save(locations)
                _LOGGER.debug("Loaded %d locations from the page", len(locations))
                return locations

        # Live source failed — fall back to the last saved copy if we have one.
        cached = await self._async_load_cached()
        if cached is not None:
            saved, locations = cached
            _LOGGER.warning(
                "Using the cached restaurant list saved %s; the live source"
                " failed: %s",
                saved,
                reason,
            )
            return locations

        raise UpdateFailed(
            f"Could not load the restaurant list and no saved copy is"
            f" available: {reason}"
        )

    async def _fetch(self, url: str) -> str:
        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(30):
            response = await session.get(url, headers=FETCH_HEADERS)
            response.raise_for_status()
            return await response.text()

    async def _async_save(self, locations: list[SunsetBoulevardLocation]) -> None:
        await self._store.async_save(
            {
                "saved": dt_util.utcnow().isoformat(),
                "locations": [asdict(location) for location in locations],
            }
        )

    async def _async_load_cached(
        self,
    ) -> tuple[str, list[SunsetBoulevardLocation]] | None:
        """Return the saved list and a human description of its age, or None."""
        data = await self._store.async_load()
        if not data or not data.get("locations"):
            return None
        try:
            locations = [
                SunsetBoulevardLocation(**item) for item in data["locations"]
            ]
        except TypeError:
            return None  # stored schema no longer matches the dataclass

        saved_raw = data.get("saved")
        saved = dt_util.parse_datetime(saved_raw or "")
        if saved is None:
            return "earlier", locations
        age_days = (dt_util.utcnow() - saved).days
        when = "today" if age_days < 1 else f"{age_days} day(s) ago"
        return when, locations


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sunset Boulevard from a config entry."""
    coordinator = SunsetBoulevardCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # Local import avoids a circular import (zone.py needs the coordinator type).
    from .zone import ClosestLocationZone

    zone = ClosestLocationZone(hass, entry, coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = SunsetBoulevardData(
        coordinator=coordinator, zone=zone
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    zone.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        data: SunsetBoulevardData = hass.data[DOMAIN].pop(entry.entry_id)
        data.zone.async_stop()
    return unload_ok
