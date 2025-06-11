"""The Hayward ColorLogic integration."""
import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "colorlogic"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hayward ColorLogic component."""
    
    async def handle_set_mode(call: ServiceCall) -> None:
        """Handle the set_mode service call."""
        entity_id = call.data.get("entity_id")
        mode = call.data.get("mode")
        
        # Get the entity
        entity = hass.data.get("light", {}).get(entity_id)
        if entity and hasattr(entity, "set_mode_by_name"):
            await entity.set_mode_by_name(mode)
    
    # Register the service
    hass.services.async_register(DOMAIN, "set_mode", handle_set_mode)
    
    return True
