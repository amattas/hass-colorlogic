"""Hayward ColorLogic Button Component for Home Assistant."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_state_change_event

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
    """Set up the Hayward ColorLogic Button platform from YAML."""
    entity_id = config[CONF_ENTITY_ID]
    name = config[CONF_NAME]
    
    async_add_entities([
        HaywardColorLogicResetButton(hass, name, entity_id),
        HaywardColorLogicNextColorButton(hass, name, entity_id)
    ], True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hayward ColorLogic Button platform from config entry."""
    # The button references the light entity that was created
    light_entity_id = f"light.{config_entry.data[CONF_NAME].lower().replace(' ', '_')}"
    name = config_entry.data[CONF_NAME]
    
    async_add_entities([
        HaywardColorLogicResetButton(hass, name, light_entity_id),
        HaywardColorLogicNextColorButton(hass, name, light_entity_id)
    ], True)


class HaywardColorLogicResetButton(ButtonEntity):
    """Representation of a Hayward ColorLogic Reset Button."""

    def __init__(self, hass: HomeAssistant, name: str, light_entity_id: str) -> None:
        """Initialize the button."""
        self.hass = hass
        self._name = f"{name} Reset"
        self._light_entity_id = light_entity_id
        self._is_resetting = False
    
    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Track light state changes to update availability
        async_track_state_change_event(
            self.hass, [self._light_entity_id], self._async_light_changed
        )
    
    @callback
    def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        self.async_write_ha_state()

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
        if self._is_resetting:
            return False
            
        # Check if the light is available and can accept mode changes
        light_state = self.hass.states.get(self._light_entity_id)
        if light_state:
            if light_state.state == "unavailable":
                return False
            # Check if light is in a state where it can accept changes
            attrs = light_state.attributes
            if attrs.get("is_changing_mode", False):
                return False
            if not attrs.get("can_change_mode", True):
                return False
        return True
    
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


class HaywardColorLogicNextColorButton(ButtonEntity):
    """Representation of a Hayward ColorLogic Next Color Button."""

    def __init__(self, hass: HomeAssistant, name: str, light_entity_id: str) -> None:
        """Initialize the button."""
        self.hass = hass
        self._name = f"{name} Next Color"
        self._light_entity_id = light_entity_id
    
    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Track light state changes to update availability
        async_track_state_change_event(
            self.hass, [self._light_entity_id], self._async_light_changed
        )
    
    @callback
    def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for the button."""
        return f"colorlogic_next_{self._light_entity_id}"

    @property
    def icon(self) -> str:
        """Return the icon to use for the button."""
        return "mdi:skip-next"
    
    @property
    def available(self) -> bool:
        """Return if button is available."""
        # Check if the light is available and can accept mode changes
        light_state = self.hass.states.get(self._light_entity_id)
        if light_state:
            if light_state.state == "unavailable":
                return False
            # Check if light is in a state where it can accept changes
            attrs = light_state.attributes
            if attrs.get("is_changing_mode", False):
                return False
            if not attrs.get("can_change_mode", True):
                return False
            return True
        return False
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "description": "Advances to the next ColorLogic mode"
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Advancing ColorLogic light %s to next mode", self._light_entity_id)
        
        # Get the light entity
        light_entity = self.hass.states.get(self._light_entity_id)
        if not light_entity:
            _LOGGER.error("Light entity %s not found", self._light_entity_id)
            return
        
        # Use the service to advance the light
        await self.hass.services.async_call(
            DOMAIN, "next_mode", {"entity_id": self._light_entity_id}, blocking=True
        )