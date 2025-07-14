# Crestron Home (OS 4) Integration for Home Assistant

A custom Home Assistant integration that connects to Crestron Home systems, allowing you to control lights and monitor occupancy sensors directly from Home Assistant.

This repo was coded almost entirely by Claude Code. I didn't really review it at all, but it worked to connect my Crestron lights and sensors to my Home Assistant setup.

## Features

- **Light Control**: Control Crestron Home lights including dimmers and switches
- **Occupancy Sensors**: Monitor room occupancy through Crestron occupancy sensors
- **Photo Sensors**: Access light level data from Crestron photo sensors
- **Local Polling**: Direct local communication with your Crestron Home system
- **Configuration UI**: Easy setup through Home Assistant's configuration interface

## Supported Devices

### Lights
- Dimmer controls with brightness adjustment
- Switch controls (on/off)

### Sensors
- Occupancy sensors (binary sensor)
- Photo sensors (light level monitoring)

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=me1000&repository=home-assistant-crestron-home&category=integration)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add the repository URL: `https://github.com/me1000/home-assistant-crestron-home`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Crestron Home" in HACS
8. Click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/me1000/home-assistant-crestron-home/releases)
2. Extract the files to your Home Assistant `custom_components` directory:
   ```
   custom_components/crestron_home/
   ```
3. Restart Home Assistant

## Configuration

### Prerequisites

- Crestron Home system accessible on your network
- API Token from your Crestron Home system
- IP address or hostname of your Crestron Home system

### Setup

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **Add Integration**
3. Search for "Crestron Home"
4. Enter your configuration:
   - **Host**: IP address or hostname of your Crestron Home system
   - **API Token**: Your Crestron Home API token
   - **Polling Interval**: How often to update device states (default: 30 seconds, but I'd suggest 5 seconds if you're controlling lights with occupancy sensors)
   - **Poll Sensors**: Enable sensor state polling (optional)

### Finding Your API Token

Your Crestron Home API token can typically be found in your Crestron Home system's web interface under API settings. Consult your Crestron documentation for specific instructions.

## Usage

Once configured, your Crestron Home devices will appear in Home Assistant:

- **Lights** will be available in the Lights section and can be controlled through the UI or automations
- **Occupancy Sensors** will appear as binary sensors showing occupied/unoccupied states
- **Photo Sensors** will show current light levels

### Automation Example

```yaml
automation:
  - alias: "Turn on lights when room is occupied"
    trigger:
      platform: state
      entity_id: binary_sensor.living_room_occupancy
      to: "on"
    action:
      service: light.turn_on
      entity_id: light.living_room_lights
      data:
        brightness: 255
```

## Development

This integration polls your Crestron Home system using the local REST API. The polling interval can be adjusted in the configuration options.

### API Endpoints Used

- `/api/login` - Authentication
- `/api/devices` - Device discovery
- `/api/sensors` - Sensor data (when enabled)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

