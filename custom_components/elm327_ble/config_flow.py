"""Config flow: add a dongle by its Bluetooth address and car profile."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import CONF_PROFILE, DOMAIN
from .profiles import PROFILES


class ObdConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for a name, the dongle's Bluetooth address and the car."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the only step."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={**user_input, CONF_ADDRESS: address},
            )
        profiles = [
            SelectOptionDict(value=key, label=profile.name)
            for key, profile in PROFILES.items()
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_ADDRESS): str,
                vol.Required(CONF_PROFILE): SelectSelector(
                    SelectSelectorConfig(options=profiles)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
