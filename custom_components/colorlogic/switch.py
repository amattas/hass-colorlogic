"""Hayward ColorLogic Power Light Component for Home Assistant."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.light import LightEntity, PLATFORM_SCHEMA
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
    """Set up the Hayward ColorLogic Power Light platform from YAML."""
    entity_id = config[CONF_ENTITY_ID]
    name = config[CONF_NAME]
    
    async_add_entities([HaywardColorLogicPowerLight(hass, name, entity_id)], True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hayward ColorLogic Power Light platform from config entry."""
    # The power light references the main light entity that was created
    light_entity_id = f"light.{config_entry.data[CONF_NAME].lower().replace(' ', '_')}"
    name = config_entry.data[CONF_NAME]
    
    async_add_entities([HaywardColorLogicPowerLight(hass, name, light_entity_id)], True)


class HaywardColorLogicPowerLight(LightEntity):
    """Representation of a Hayward ColorLogic Power Light (on/off only)."""

    def __init__(self, hass: HomeAssistant, name: str, switch_entity_id: str, entry_id: str | None = None) -> None:
        """Initialize the power light."""
        self.hass = hass
        self._name = name  # Use the base name without suffix
        self._switch_entity_id = switch_entity_id
        self._entry_id = entry_id
        self._is_on = False
        self._is_available = True
        # Store the RGB light entity ID for tracking
        self._rgb_light_entity_id = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Determine the RGB light entity ID
        if self._entry_id:
            # For config entries, the RGB light will have _rgb suffix
            base_name = self._name.lower().replace(' ', '_')
            self._rgb_light_entity_id = f"light.{base_name}_rgb"
        else:
            # For YAML config, track the referenced entity
            self._rgb_light_entity_id = self._switch_entity_id
        
        # Track RGB light state changes
        if self._rgb_light_entity_id:
            async_track_state_change_event(
                self.hass, [self._rgb_light_entity_id], self._async_light_changed
            )
            
            # Get initial state
            light_state = self.hass.states.get(self._rgb_light_entity_id)
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
        """Return the name of the light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for the light."""
        if self._entry_id:
            return f"{self._entry_id}_power"
        return f"colorlogic_power_{self._switch_entity_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._is_on
    
    @property
    def available(self) -> bool:
        """Return if light is available."""
        if not self._is_available:
            return False
            
        # Check if RGB light is changing modes
        if self._rgb_light_entity_id:
            light_state = self.hass.states.get(self._rgb_light_entity_id)
            if light_state and light_state.attributes:
                if light_state.attributes.get("is_changing_mode", False):
                    return False
                
        return True
    
    @property
    def icon(self) -> str:
        """Return the icon to use for the light."""
        return "mdi:lightbulb"
    
    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        # This light only supports on/off, no color or brightness
        return 0
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {"rgb_light_entity": self._rgb_light_entity_id}
        
        if self._rgb_light_entity_id:
            light_state = self.hass.states.get(self._rgb_light_entity_id)
            if light_state and light_state.attributes:
                # Pass through some attributes from the RGB light
                if "is_changing_mode" in light_state.attributes:
                    attrs["is_changing_mode"] = light_state.attributes["is_changing_mode"]
                if "startup_timer_remaining" in light_state.attributes:
                    attrs["startup_timer_remaining"] = light_state.attributes["startup_timer_remaining"]
                if "can_change_mode" in light_state.attributes:
                    attrs["can_change_mode"] = light_state.attributes["can_change_mode"]
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Turn on the actual switch
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self._switch_entity_id}
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # Turn off the actual switch
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._switch_entity_id}
        )