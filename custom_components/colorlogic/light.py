"""Hayward ColorLogic Light Component for Home Assistant."""
import logging
import asyncio
from datetime import timedelta
from typing import Any, Optional

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Optional(CONF_NAME, default="ColorLogic Light"): cv.string,
})

# ColorLogic modes mapping
COLORLOGIC_MODES = {
    1: {"name": "voodoo_lounge", "type": "show"},
    2: {"name": "deep_blue_sea", "type": "fixed", "rgb": (0, 0, 255)},
    3: {"name": "royal_blue", "type": "fixed", "rgb": (65, 105, 225)},
    4: {"name": "afternoon_skies", "type": "fixed", "rgb": (135, 206, 235)},
    5: {"name": "aqua_green", "type": "fixed", "rgb": (0, 255, 212)},
    6: {"name": "emerald", "type": "fixed", "rgb": (0, 201, 87)},
    7: {"name": "cloud_white", "type": "fixed", "rgb": (255, 255, 255)},
    8: {"name": "warm_red", "type": "fixed", "rgb": (255, 0, 0)},
    9: {"name": "flamingo", "type": "fixed", "rgb": (255, 192, 203)},
    10: {"name": "vivid_violet", "type": "fixed", "rgb": (138, 43, 226)},
    11: {"name": "sangria", "type": "fixed", "rgb": (146, 0, 10)},
    12: {"name": "twilight", "type": "show"},
    13: {"name": "tranquility", "type": "show"},
    14: {"name": "gemstone", "type": "show"},
    15: {"name": "usa", "type": "show"},
    16: {"name": "mardi_gras", "type": "show"},
    17: {"name": "cool_cabaret", "type": "show"},
}

# Reverse mapping for quick lookups
MODE_NAME_TO_NUMBER = {v["name"]: k for k, v in COLORLOGIC_MODES.items()}

# Create effect name to mode number mapping
EFFECT_TO_MODE = {}
for mode_num, mode_info in COLORLOGIC_MODES.items():
    effect_name = mode_info["name"].replace("_", " ").title()
    EFFECT_TO_MODE[effect_name] = mode_num


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Hayward ColorLogic Light platform."""
    entity_id = config[CONF_ENTITY_ID]
    name = config[CONF_NAME]
    
    async_add_entities([HaywardColorLogicLight(hass, name, entity_id)], True)


class HaywardColorLogicLight(LightEntity, RestoreEntity):
    """Representation of a Hayward ColorLogic Light."""

    def __init__(self, hass: HomeAssistant, name: str, switch_entity_id: str) -> None:
        """Initialize the light."""
        self.hass = hass
        self._name = name
        self._switch_entity_id = switch_entity_id
        self._is_on = False
        self._current_mode = 7  # Default to white
        self._rgb_color = COLORLOGIC_MODES[7]["rgb"]
        self._is_changing_mode = False
        
    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state is not None:
            # Restore the previous mode
            if "current_mode_number" in last_state.attributes:
                self._current_mode = last_state.attributes["current_mode_number"]
                mode_info = COLORLOGIC_MODES.get(self._current_mode, {})
                if "rgb" in mode_info:
                    self._rgb_color = mode_info["rgb"]
                _LOGGER.debug(
                    "Restored ColorLogic mode %s for %s",
                    self._current_mode,
                    self.entity_id
                )
        
        # Track switch state changes
        async_track_state_change_event(
            self.hass, [self._switch_entity_id], self._async_switch_changed
        )
        
        # Get initial state
        switch_state = self.hass.states.get(self._switch_entity_id)
        if switch_state:
            self._is_on = switch_state.state == "on"

    @callback
    def _async_switch_changed(self, event) -> None:
        """Handle switch state changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return
            
        # Update our state if we're not currently changing modes
        if not self._is_changing_mode:
            self._is_on = new_state.state == "on"
            self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for the light."""
        return f"colorlogic_{self._switch_entity_id}"

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.RGB

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {ColorMode.RGB}
    
    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        return LightEntityFeature.EFFECT

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return the rgb color value."""
        return self._rgb_color
    
    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        effects = []
        for mode_info in COLORLOGIC_MODES.values():
            effects.append(mode_info["name"].replace("_", " ").title())
        return sorted(effects)
    
    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        mode_info = COLORLOGIC_MODES.get(self._current_mode, {})
        if mode_info:
            return mode_info.get("name", "").replace("_", " ").title()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        mode_info = COLORLOGIC_MODES.get(self._current_mode, {})
        return {
            "current_mode_number": self._current_mode,
            "current_mode_name": mode_info.get("name", "unknown"),
            "mode_type": mode_info.get("type", "unknown"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        self._is_on = True
        
        # Check if effect is specified
        if ATTR_EFFECT in kwargs:
            effect_name = kwargs[ATTR_EFFECT]
            if effect_name in EFFECT_TO_MODE:
                target_mode = EFFECT_TO_MODE[effect_name]
                await self._change_to_mode(target_mode)
        # If RGB color is specified, find closest mode
        elif ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
            closest_mode = self._find_closest_color_mode(rgb)
            await self._change_to_mode(closest_mode)
        else:
            # Just turn on the switch
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self._switch_entity_id}
            )
        
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._is_on = False
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._switch_entity_id}
        )
        self.async_write_ha_state()

    def _find_closest_color_mode(self, target_rgb: tuple[int, int, int]) -> int:
        """Find the closest ColorLogic mode for a given RGB color."""
        min_distance = float('inf')
        closest_mode = 7  # Default to white
        
        for mode_num, mode_info in COLORLOGIC_MODES.items():
            if mode_info["type"] != "fixed":
                continue
                
            mode_rgb = mode_info["rgb"]
            # Calculate Euclidean distance
            distance = sum((a - b) ** 2 for a, b in zip(target_rgb, mode_rgb)) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_mode = mode_num
                
        return closest_mode

    async def _change_to_mode(self, target_mode: int) -> None:
        """Change to a specific ColorLogic mode."""
        if target_mode == self._current_mode:
            return
            
        self._is_changing_mode = True
        
        try:
            # Determine if we should reset or cycle forward
            cycles_forward = target_mode - self._current_mode
            if cycles_forward < 0:
                cycles_forward += 17
                
            # If it's more efficient to reset, do that
            if cycles_forward > 10 or self._current_mode == 0:
                await self._reset_to_mode_1()
                cycles_forward = target_mode - 1
            
            # Cycle to the target mode
            await self._cycle_forward(cycles_forward)
            
            # Update our state
            self._current_mode = target_mode
            mode_info = COLORLOGIC_MODES.get(target_mode, {})
            if "rgb" in mode_info:
                self._rgb_color = mode_info["rgb"]
                
            # Save the mode
            await self._save_mode()
            
            # Update Home Assistant state to persist
            self.async_write_ha_state()
            
        finally:
            self._is_changing_mode = False

    async def _cycle_forward(self, cycles: int) -> None:
        """Cycle forward through modes."""
        for _ in range(cycles):
            # Turn off
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": self._switch_entity_id}
            )
            await asyncio.sleep(1)
            
            # Turn on
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self._switch_entity_id}
            )
            await asyncio.sleep(1)

    async def _reset_to_mode_1(self) -> None:
        """Reset the light to mode 1."""
        for _ in range(3):
            # Turn off for 13 seconds
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": self._switch_entity_id}
            )
            await asyncio.sleep(13)
            
            # Turn on for 2 seconds
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self._switch_entity_id}
            )
            await asyncio.sleep(2)
            
        self._current_mode = 1
        self.async_write_ha_state()

    async def _save_mode(self) -> None:
        """Save the current mode by turning off for 2+ seconds."""
        # Turn off
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._switch_entity_id}
        )
        await asyncio.sleep(2.5)
        
        # Turn back on
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self._switch_entity_id}
        )

    async def set_mode_by_name(self, mode_name: str) -> None:
        """Set mode by name (for use in services)."""
        if mode_name in MODE_NAME_TO_NUMBER:
            await self._change_to_mode(MODE_NAME_TO_NUMBER[mode_name])
            self.async_write_ha_state()
