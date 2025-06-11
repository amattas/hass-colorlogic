"""Hayward ColorLogic Button Component for Home Assistant."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Optional(CONF_NAME, default="ColorLogic Light"): cv.string,
})


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Hayward ColorLogic Button platform."""
    entity_id = config[CONF_ENTITY_ID]
    name = config[CONF_NAME]
    
    async_add_entities([HaywardColorLogicResetButton(hass, name, entity_id)], True)


class HaywardColorLogicResetButton(ButtonEntity):
    """Representation of a Hayward ColorLogic Reset Button."""

    def __init__(self, hass: HomeAssistant, name: str, light_entity_id: str) -> None:
        """Initialize the button."""
        self.hass = hass
        self._name = f"{name} Reset"
        self._light_entity_id = light_entity_id
        self._is_resetting = False

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for the button."""
        return f"colorlogic_reset_{self._light_entity_id}"

    @property
    def icon(self) -> str:
        """Return the icon to use for the button."""
        return "mdi:restart"
    
    @property
    def available(self) -> bool:
        """Return if button is available."""
        return not self._is_resetting
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "in_progress": self._is_resetting,
            "description": "Resets light to mode 1. Takes about 3 minutes to complete."
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        if self._is_resetting:
            _LOGGER.warning("Reset already in progress for %s", self._light_entity_id)
            return
            
        _LOGGER.info("Starting reset of ColorLogic light %s to mode 1", self._light_entity_id)
        self._is_resetting = True
        self.async_write_ha_state()
        
        try:
            # Get the light entity
            light_entity = self.hass.states.get(self._light_entity_id)
            if not light_entity:
                _LOGGER.error("Light entity %s not found", self._light_entity_id)
                return
            
            # Use the service to reset the light
            await self.hass.services.async_call(
                DOMAIN, "reset", {"entity_id": self._light_entity_id}, blocking=True
            )
        finally:
            self._is_resetting = False
            self.async_write_ha_state()
            _LOGGER.info("Reset complete for %s", self._light_entity_id)