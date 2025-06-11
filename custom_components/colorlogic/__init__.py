"""The Hayward ColorLogic integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "colorlogic"
PLATFORMS = [Platform.LIGHT, Platform.BUTTON, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hayward ColorLogic component."""
    
    # Store our light entities
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}}
    
    async def handle_set_mode(call: ServiceCall) -> None:
        """Handle the set_mode service call."""
        entity_ids = call.data.get("entity_id")
        mode = call.data.get("mode")
        
        # Ensure entity_ids is a list
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        
        for entity_id in entity_ids:
            # Get the entity from our stored references
            entity = hass.data[DOMAIN]["entities"].get(entity_id)
            if entity and hasattr(entity, "set_mode_by_name"):
                await entity.set_mode_by_name(mode)
            else:
                _LOGGER.error("Entity %s not found or doesn't support set_mode_by_name", entity_id)
    
    async def handle_reset(call: ServiceCall) -> None:
        """Handle the reset service call."""
        entity_ids = call.data.get("entity_id")
        
        # Ensure entity_ids is a list
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        
        for entity_id in entity_ids:
            # Get the entity from our stored references
            entity = hass.data[DOMAIN]["entities"].get(entity_id)
            if entity and hasattr(entity, "reset_to_mode_1"):
                await entity.reset_to_mode_1()
            else:
                _LOGGER.error("Entity %s not found or doesn't support reset_to_mode_1", entity_id)
    
    async def handle_next_mode(call: ServiceCall) -> None:
        """Handle the next_mode service call."""
        entity_ids = call.data.get("entity_id")
        
        # Ensure entity_ids is a list
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        
        for entity_id in entity_ids:
            # Get the entity from our stored references
            entity = hass.data[DOMAIN]["entities"].get(entity_id)
            if entity and hasattr(entity, "next_mode"):
                await entity.next_mode()
            else:
                _LOGGER.error("Entity %s not found or doesn't support next_mode", entity_id)
    
    # Register the services only once
    if not hass.services.has_service(DOMAIN, "set_mode"):
        hass.services.async_register(DOMAIN, "set_mode", handle_set_mode)
        hass.services.async_register(DOMAIN, "reset", handle_reset)
        hass.services.async_register(DOMAIN, "next_mode", handle_next_mode)
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hayward ColorLogic from a config entry."""
    # Initialize domain data if needed
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}}
    
    # Store config entry data
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove config entry data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        
        # Clean up entities
        for entity_id in list(hass.data[DOMAIN]["entities"].keys()):
            if entity_id.startswith(f"{DOMAIN}_{entry.entry_id}"):
                hass.data[DOMAIN]["entities"].pop(entity_id, None)
    
    return unload_ok
