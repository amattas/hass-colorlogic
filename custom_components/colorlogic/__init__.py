"""The Hayward ColorLogic integration."""
import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "colorlogic"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hayward ColorLogic component."""
    
    # Store our light entities
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
    
    # Register the services
    hass.services.async_register(DOMAIN, "set_mode", handle_set_mode)
    hass.services.async_register(DOMAIN, "reset", handle_reset)
    
    return True
