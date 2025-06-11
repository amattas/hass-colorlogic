"""Config flow for Hayward ColorLogic integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # Check if the switch entity exists
    switch_entity_id = data[CONF_ENTITY_ID]
    if not hass.states.get(switch_entity_id):
        raise ValueError("switch_not_found")
    
    # Check if it's actually a switch
    if not switch_entity_id.startswith("switch."):
        raise ValueError("not_a_switch")
    
    # Return info to store in the config entry
    return {"title": data.get(CONF_NAME, "ColorLogic Light")}


class ColorLogicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hayward ColorLogic."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ValueError as err:
                if str(err) == "switch_not_found":
                    errors["base"] = "switch_not_found"
                elif str(err) == "not_a_switch":
                    errors["base"] = "not_a_switch"
                else:
                    errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured for this switch
                await self.async_set_unique_id(user_input[CONF_ENTITY_ID])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input
                )

        # Show form
        data_schema = vol.Schema({
            vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Optional(CONF_NAME, default="ColorLogic Light"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return ColorLogicOptionsFlow(config_entry)


class ColorLogicOptionsFlow(config_entries.OptionsFlow):
    """Handle options for ColorLogic."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Optional(
                CONF_NAME,
                default=self.config_entry.data.get(CONF_NAME, "ColorLogic Light")
            ): str,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )