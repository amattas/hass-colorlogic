"""Hayward ColorLogic Switch Component for Home Assistant."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.switch import SwitchEntity, PLATFORM_SCHEMA
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
    """Set up the Hayward ColorLogic Switch platform from YAML."""
    entity_id = config[CONF_ENTITY_ID]
    name = config[CONF_NAME]
    
    async_add_entities([HaywardColorLogicSwitch(hass, name, entity_id)], True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hayward ColorLogic Switch platform from config entry."""
    # The switch references the light entity that was created
    light_entity_id = f"light.{config_entry.data[CONF_NAME].lower().replace(' ', '_')}"
    name = config_entry.data[CONF_NAME]
    
    async_add_entities([HaywardColorLogicSwitch(hass, name, light_entity_id)], True)


class HaywardColorLogicSwitch(SwitchEntity):
    """Representation of a Hayward ColorLogic Switch (on/off only)."""

    def __init__(self, hass: HomeAssistant, name: str, light_entity_id: str) -> None:
        """Initialize the switch."""
        self.hass = hass
        self._name = f"{name} Power"
        self._light_entity_id = light_entity_id
        self._is_on = False
        self._is_available = True

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Track light state changes
        async_track_state_change_event(
            self.hass, [self._light_entity_id], self._async_light_changed
        )
        
        # Get initial state
        light_state = self.hass.states.get(self._light_entity_id)
        if light_state:
            self._is_on = light_state.state == "on"
            self._is_available = light_state.state != "unavailable"

    @callback
    def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return
            
        self._is_on = new_state.state == "on"
        self._is_available = new_state.state != "unavailable"
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for the switch."""
        return f"colorlogic_switch_{self._light_entity_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on
    
    @property
    def available(self) -> bool:
        """Return if switch is available."""
        if not self._is_available:
            return False
            
        # Check if light is changing modes
        light_state = self.hass.states.get(self._light_entity_id)
        if light_state and light_state.attributes:
            if light_state.attributes.get("is_changing_mode", False):
                return False
                
        return True
    
    @property
    def icon(self) -> str:
        """Return the icon to use for the switch."""
        return "mdi:lightbulb"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        light_state = self.hass.states.get(self._light_entity_id)
        if light_state and light_state.attributes:
            # Pass through some attributes from the light
            attrs = {}
            if "is_changing_mode" in light_state.attributes:
                attrs["is_changing_mode"] = light_state.attributes["is_changing_mode"]
            if "startup_timer_remaining" in light_state.attributes:
                attrs["startup_timer_remaining"] = light_state.attributes["startup_timer_remaining"]
            if "can_change_mode" in light_state.attributes:
                attrs["can_change_mode"] = light_state.attributes["can_change_mode"]
            return attrs
        return {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.hass.services.async_call(
            "light", "turn_on", {"entity_id": self._light_entity_id}
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.hass.services.async_call(
            "light", "turn_off", {"entity_id": self._light_entity_id}
        )