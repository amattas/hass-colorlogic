# hass-colorlogic
Home Assistant integration for Hayward ColorLogic pool lights

## Features
- Control ColorLogic lights through Home Assistant
- Support for all 17 ColorLogic modes (10 fixed colors + 7 light shows)
- Automatic mode tracking when manually toggling the switch
- Reset button to sync the light back to mode 1 (Voodoo Lounge)
- Protection timers to ensure reliable operation
- Default mode is Voodoo Lounge (show mode) when first powered on

## Installation

1. Copy the `custom_components/colorlogic` folder to your Home Assistant `config/custom_components/` directory
2. Add the configuration to your `configuration.yaml`
3. Restart Home Assistant

## Configuration

```yaml
# configuration.yaml
light:
  - platform: colorlogic
    entity_id: switch.pool_light_switch  # Your existing pool light switch
    name: "Pool Light"                   # This creates light.pool_light

button:
  - platform: colorlogic
    entity_id: light.pool_light  # References the light entity created above (NOT the switch)
    name: "Pool Light"           # This creates button.pool_light_reset
```

## Lovelace Card Configuration

### Option 1: Light Entity Card with Favorite Colors

To show only the 10 supported ColorLogic colors in the UI, add this to your Lovelace dashboard:

```yaml
type: light
entity: light.pool_light
favorite_colors:
  - rgb_color: [20, 76, 135]    # Deep Sea Blue
  - rgb_color: [7, 112, 174]    # Royal Blue
  - rgb_color: [36, 190, 235]   # Afternoon Skies
  - rgb_color: [20, 185, 187]   # Aqua Green
  - rgb_color: [5, 161, 85]     # Emerald
  - rgb_color: [228, 242, 251]  # Cloud White
  - rgb_color: [233, 36, 50]    # Warm Red
  - rgb_color: [240, 90, 124]   # Flamingo
  - rgb_color: [170, 82, 130]   # Vivid Violet
  - rgb_color: [124, 74, 149]   # Sangria
```

### Option 2: Entities Card with Color Buttons

For a more compact view with all controls:

```yaml
type: entities
entities:
  - entity: light.pool_light
    name: Pool Light
  - entity: button.pool_light_reset
    name: Reset to Voodoo Lounge
title: Pool Light Control
```

### Option 3: Custom Button Card (requires custom:button-card)

Create individual buttons for each color:

```yaml
type: grid
columns: 5
cards:
  - type: custom:button-card
    entity: light.pool_light
    name: Deep Blue
    tap_action:
      action: call-service
      service: light.turn_on
      service_data:
        entity_id: light.pool_light
        rgb_color: [20, 76, 135]
    styles:
      card:
        - background-color: 'rgb(20, 76, 135)'
        - color: white
  # Repeat for other colors...
```

## Supported Modes

### Fixed Colors
1. Deep Sea Blue (#144C87)
2. Royal Blue (#0770AE)
3. Afternoon Skies (#24BEEB)
4. Aqua Green (#14B9BB)
5. Emerald (#05A155)
6. Cloud White (#E4F2FB)
7. Warm Red (#E92432)
8. Flamingo (#F05A7C)
9. Vivid Violet (#AA5282)
10. Sangria (#7C4A95)

### Light Shows
1. Voodoo Lounge
2. Twilight
3. Tranquility
4. Gemstone
5. USA
6. Mardi Gras
7. Cool Cabaret

## Services

### colorlogic.set_mode
Set the light to a specific mode by name.

```yaml
service: colorlogic.set_mode
data:
  entity_id: light.pool_light
  mode: royal_blue
```

### colorlogic.reset
Reset the light to mode 1 (Voodoo Lounge). This process takes about 3 minutes.

```yaml
service: colorlogic.reset
data:
  entity_id: light.pool_light
```

## Important Notes

- The light cannot be dimmed (brightness control is not supported)
- Mode changes are blocked for 60 seconds after turning on to allow the controller to stabilize
- Manual switch toggles are detected and tracked automatically
- Any RGB color selected will map to the nearest supported ColorLogic color
- The default mode when first powered on or after a reset is Voodoo Lounge (mode 1), not a solid color