"""Config flow for the Sunset Boulevard integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_TRACKER,
    CONF_ENTRY_TYPE,
    DOMAIN,
    ENTRY_TYPE_ALL_RESTAURANTS,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_TRACKER): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["device_tracker", "person"])
        )
    }
)


class SunsetBoulevardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sunset Boulevard."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask whether to follow someone or to show every restaurant."""
        return self.async_show_menu(
            step_id="user", menu_options=["follow", ENTRY_TYPE_ALL_RESTAURANTS]
        )

    async def async_step_follow(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Follow a device tracker or person."""
        if user_input is not None:
            tracker_entity_id = user_input[CONF_DEVICE_TRACKER]
            await self.async_set_unique_id(tracker_entity_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Sunset Boulevard", data=user_input
            )

        return self.async_show_form(step_id="follow", data_schema=DATA_SCHEMA)

    async def async_step_all_restaurants(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Put every restaurant on the map, once."""
        if await self.async_set_unique_id(ENTRY_TYPE_ALL_RESTAURANTS):
            return self.async_abort(reason="all_restaurants_configured")

        return self.async_create_entry(
            title="All restaurants",
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_ALL_RESTAURANTS},
        )
