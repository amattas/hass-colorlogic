"""Hayward ColorLogic Light Component for Home Assistant."""
import logging
import asyncio
import time
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
from homeassistant.config_entries import ConfigEntry
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
    2: {"name": "deep_blue_sea", "type": "fixed", "rgb": (20, 76, 135)},
    3: {"name": "royal_blue", "type": "fixed", "rgb": (7, 112, 174)},
    4: {"name": "afternoon_skies", "type": "fixed", "rgb": (36, 190, 235)},
    5: {"name": "aqua_green", "type": "fixed", "rgb": (20, 185, 187)},
    6: {"name": "emerald", "type": "fixed", "rgb": (5, 161, 85)},
    7: {"name": "cloud_white", "type": "fixed", "rgb": (228, 242, 251)},
    8: {"name": "warm_red", "type": "fixed", "rgb": (233, 36, 50)},
    9: {"name": "flamingo", "type": "fixed", "rgb": (240, 90, 124)},
    10: {"name": "vivid_violet", "type": "fixed", "rgb": (170, 82, 130)},
    11: {"name": "sangria", "type": "fixed", "rgb": (124, 74, 149)},
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
    """Set up the Hayward ColorLogic Light platform from YAML."""
    entity_id = config[CONF_ENTITY_ID]
    name = config[CONF_NAME]
    
    async_add_entities([HaywardColorLogicLight(hass, name, entity_id)], True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hayward ColorLogic Light platform from config entry."""
    entity_id = config_entry.data[CONF_ENTITY_ID]
    name = config_entry.data[CONF_NAME]
    
    # Create RGB light with _rgb suffix
    rgb_light = HaywardColorLogicLight(hass, f"{name} RGB", entity_id, config_entry.entry_id)
    
    # Create simple on/off light
    from .switch import HaywardColorLogicPowerLight
    power_light = HaywardColorLogicPowerLight(hass, name, entity_id, config_entry.entry_id)
    
    async_add_entities([rgb_light, power_light], True)


class HaywardColorLogicLight(LightEntity, RestoreEntity):
    """Representation of a Hayward ColorLogic Light."""

    def __init__(self, hass: HomeAssistant, name: str, switch_entity_id: str, entry_id: str | None = None) -> None:
        """Initialize the light."""
        self.hass = hass
        self._name = name
        self._switch_entity_id = switch_entity_id
        self._entry_id = entry_id
        self._is_on = False
        self._current_mode = 1  # Default to voodoo_lounge (show mode)
        self._rgb_color = None  # No RGB for show modes
        self._is_changing_mode = False
        self._last_on_time = None
        self._last_off_time = None
        self._manual_changes_count = 0
        
    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Register this entity with the domain
        if DOMAIN in self.hass.data and "entities" in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["entities"][self.entity_id] = self
            _LOGGER.debug("Registered ColorLogic entity: %s", self.entity_id)
        
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
        old_state = event.data.get("old_state")
        if new_state is None:
            return
            
        current_time = time.time()
        is_on = new_state.state == "on"
        
        # Update our state if we're not currently changing modes programmatically
        if not self._is_changing_mode:
            was_on = self._is_on
            self._is_on = is_on
            
            if not was_on and is_on:
                # Light turned on
                if self._last_off_time and (current_time - self._last_off_time) < 2:
                    # This was a quick off/on cycle - manual mode change
                    self._manual_changes_count += 1
                    
                    # Advance to next mode
                    self._current_mode = (self._current_mode % 17) + 1
                    
                    _LOGGER.info("Manual mode change detected (cycle #%d) - new mode: %d (%s)", 
                                self._manual_changes_count, self._current_mode, 
                                COLORLOGIC_MODES.get(self._current_mode, {}).get("name", "unknown"))
                    
                    # Update RGB if it's a fixed color mode
                    mode_info = COLORLOGIC_MODES.get(self._current_mode, {})
                    if "rgb" in mode_info:
                        self._rgb_color = mode_info["rgb"]
                else:
                    # Normal turn on - reset manual change counter
                    self._manual_changes_count = 0
                    _LOGGER.debug("Light turned on normally, starting 60-second timer")
                
                # Always set the on time for protection
                self._last_on_time = current_time
                
            elif was_on and not is_on:
                # Light turned off
                self._last_off_time = current_time
                
                # Check if this might be part of a mode change sequence
                if self._last_on_time and (current_time - self._last_on_time) < 2:
                    # Quick on/off - could be start of manual mode change
                    _LOGGER.debug("Quick off detected, possible manual mode change incoming")
                else:
                    # Normal off - clear the on timer
                    self._last_on_time = None
                    
                    # If off for more than 2 seconds, it might be a save operation
                    if self._manual_changes_count > 0:
                        _LOGGER.info("Mode saved after %d manual changes", self._manual_changes_count)
                        self._manual_changes_count = 0
                    
            self.async_write_ha_state()
        else:
            # We're in the middle of a programmatic change, just update internal state
            self._is_on = is_on

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for the light."""
        if self._entry_id:
            return f"{self._entry_id}_light"
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
    def brightness(self) -> None:
        """Return the brightness of the light (always None as it's not dimmable)."""
        return None
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Light is unavailable while changing modes or resetting
        if self._is_changing_mode:
            return False
            
        # Light is unavailable for 60 seconds after being turned on
        if self._last_on_time and self._is_on:
            elapsed = time.time() - self._last_on_time
            if elapsed < 60:
                return False
                
        return True
    
    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        return LightEntityFeature.EFFECT
    
    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value [float, float]."""
        # Convert RGB to HS to ensure color wheel shows exact colors
        if self._rgb_color:
            from homeassistant.util import color as color_util
            return color_util.color_RGB_to_hs(*self._rgb_color)
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        # Return None for show modes, RGB for fixed color modes
        mode_info = COLORLOGIC_MODES.get(self._current_mode, {})
        if mode_info.get("type") == "fixed":
            return self._rgb_color
        return None
    
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
        attrs = {
            "current_mode_number": self._current_mode,
            "current_mode_name": mode_info.get("name", "unknown"),
            "mode_type": mode_info.get("type", "unknown"),
            "is_changing_mode": self._is_changing_mode,
        }
        
        # Add hex color code for fixed color modes
        if mode_info.get("type") == "fixed" and "rgb" in mode_info:
            r, g, b = mode_info["rgb"]
            attrs["color_hex"] = f"#{r:02X}{g:02X}{b:02X}"
        
        # Add startup timer info
        if self._last_on_time and self._is_on:
            elapsed = time.time() - self._last_on_time
            if elapsed < 60:
                attrs["startup_timer_remaining"] = max(0, int(60 - elapsed))
                attrs["can_change_mode"] = False
            else:
                attrs["can_change_mode"] = True
        
        # Add manual change tracking
        if self._manual_changes_count > 0:
            attrs["manual_changes_detected"] = self._manual_changes_count
        
        # Add supported colors for UI
        supported_colors = []
        for mode_num, mode_data in COLORLOGIC_MODES.items():
            if mode_data["type"] == "fixed":
                r, g, b = mode_data["rgb"]
                supported_colors.append({
                    "name": mode_data["name"].replace("_", " ").title(),
                    "rgb": [r, g, b],
                    "hex": f"#{r:02X}{g:02X}{b:02X}"
                })
        attrs["supported_colors"] = supported_colors
        
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Check if we're already changing modes
        if self._is_changing_mode:
            _LOGGER.warning("Cannot change color/mode while already changing modes")
            return
        
        # Check if light is available (handles both mode changes and startup timer)
        if not self.available:
            _LOGGER.warning("Light is not available for changes")
            return
        
        # If light is being turned on (not already on), record the time
        if not self._is_on:
            self._last_on_time = time.time()
            self._is_on = True
            # Just turn on the switch first
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self._switch_entity_id}
            )
            self.async_write_ha_state()
            
            # If color/effect change requested, we need to wait or reject
            if ATTR_EFFECT in kwargs or ATTR_RGB_COLOR in kwargs:
                _LOGGER.warning("Cannot change color/mode within 60 seconds of turning on")
                return
        else:
            # Light is already on, check if we can change modes
            if self._last_on_time:
                elapsed = time.time() - self._last_on_time
                if elapsed < 60:
                    _LOGGER.warning("Cannot change color/mode within 60 seconds of turning on (%.1f seconds elapsed)", elapsed)
                    return
            
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
                
                # Log the color mapping for user feedback
                mode_info = COLORLOGIC_MODES.get(closest_mode, {})
                if mode_info and "rgb" in mode_info:
                    selected_hex = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
                    mapped_rgb = mode_info["rgb"]
                    mapped_hex = f"#{mapped_rgb[0]:02X}{mapped_rgb[1]:02X}{mapped_rgb[2]:02X}"
                    _LOGGER.info(
                        "Color %s mapped to %s (%s)", 
                        selected_hex, 
                        mode_info["name"].replace("_", " ").title(),
                        mapped_hex
                    )
                
                await self._change_to_mode(closest_mode)
        
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._is_on = False
        self._last_on_time = None  # Clear the timer when turning off
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._switch_entity_id}
        )
        self.async_write_ha_state()

    def _find_closest_color_mode(self, target_rgb: tuple[int, int, int]) -> int:
        """Find the closest ColorLogic mode for a given RGB color."""
        min_distance = float('inf')
        closest_mode = 7  # Default to cloud_white if no match found
        
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
        
        # Double-check we're not already changing
        if self._is_changing_mode:
            _LOGGER.warning("Already changing modes, ignoring request")
            return
            
        self._is_changing_mode = True
        
        try:
            # Calculate cycles needed to reach target mode
            cycles_forward = target_mode - self._current_mode
            if cycles_forward < 0:
                cycles_forward += 17
                
            # Reset is NEVER faster due to the long delays (3+ minutes)
            # Only reset if we're in an unknown state (mode 0)
            if self._current_mode == 0:
                await self._reset_to_mode_1()
                cycles_forward = target_mode - 1
            
            # Cycle to the target mode
            await self._cycle_forward(cycles_forward)
            
            # Update our state
            self._current_mode = target_mode
            mode_info = COLORLOGIC_MODES.get(target_mode, {})
            if "rgb" in mode_info:
                self._rgb_color = mode_info["rgb"]
                          
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
        # Step 1: Turn on if not already on
        if not self._is_on:
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self._switch_entity_id}
            )
            self._is_on = True
        
        self._is_changing_mode = True  # Prevent state updates during reset
        
        # Step 2: Wait 60 seconds to ensure light has been on long enough
        _LOGGER.info("Waiting 60 seconds before reset sequence...")
        await asyncio.sleep(60)
        
        # Step 3: Turn off for 11-13 seconds
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._switch_entity_id}
        )
        await asyncio.sleep(12)  # Middle of 11-13 range
        
        # Step 4: Turn back on immediately
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self._switch_entity_id}
        )
        
        # Step 5: Wait for confirmation (give it a moment to register)
        await asyncio.sleep(2)
        
        # Step 6: Turn off for 2 minutes (light shouldn't respond during this time)
        _LOGGER.info("Turning off for 2 minutes to complete reset...")
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._switch_entity_id}
        )
        await asyncio.sleep(120)  # 2 minutes
        
        # Reset complete
        self._current_mode = 1
        self._is_on = False
        self._is_changing_mode = False
        _LOGGER.info("Reset complete. Light is now at mode 1.")
        self.async_write_ha_state()

    async def set_mode_by_name(self, mode_name: str) -> None:
        """Set mode by name (for use in services)."""
        if self._is_changing_mode:
            _LOGGER.warning("Cannot change mode while already changing modes")
            return
        
        # Check 60-second startup timer
        if self._last_on_time and self._is_on:
            elapsed = time.time() - self._last_on_time
            if elapsed < 60:
                _LOGGER.warning("Cannot change mode within 60 seconds of turning on (%.1f seconds elapsed)", elapsed)
                return
            
        if mode_name in MODE_NAME_TO_NUMBER:
            await self._change_to_mode(MODE_NAME_TO_NUMBER[mode_name])
            self.async_write_ha_state()
    
    async def reset_to_mode_1(self) -> None:
        """Public method to reset the light to mode 1."""
        if self._is_changing_mode:
            _LOGGER.warning("Cannot reset while already changing modes")
            return
        
        # Check 60-second startup timer
        if self._last_on_time and self._is_on:
            elapsed = time.time() - self._last_on_time
            if elapsed < 60:
                _LOGGER.warning("Cannot reset within 60 seconds of turning on (%.1f seconds elapsed)", elapsed)
                return
            
        await self._reset_to_mode_1()
        self.async_write_ha_state()
    
    async def next_mode(self) -> None:
        """Advance to the next ColorLogic mode."""
        if self._is_changing_mode:
            _LOGGER.warning("Cannot advance mode while already changing modes")
            return
        
        if not self.available:
            _LOGGER.warning("Light is not available for changes")
            return
        
        # Check 60-second startup timer
        if self._last_on_time and self._is_on:
            elapsed = time.time() - self._last_on_time
            if elapsed < 60:
                _LOGGER.warning("Cannot change mode within 60 seconds of turning on (%.1f seconds elapsed)", elapsed)
                return
        
        # Calculate next mode
        next_mode = (self._current_mode % 17) + 1
        await self._change_to_mode(next_mode)
        self.async_write_ha_state()
