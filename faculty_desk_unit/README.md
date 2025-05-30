# ConsultEase - Faculty Desk Unit

This is the firmware for the Faculty Desk Unit component of the ConsultEase system. This unit is installed at each faculty member's desk and shows consultation requests from students while automatically detecting the faculty's presence via BLE.

## Overview
The Faculty Desk Unit is an ESP32-based device that provides a physical interface for faculty members to receive and respond to student consultation requests. It features BLE-based presence detection, a TFT display, and two buttons for acknowledging or declining consultation requests.

## Key Features
- **Grace Period BLE System**: Enhanced BLE scanning with a 1-minute grace period to prevent false absence detection
- **Adaptive BLE Scanning**: Intelligent scanning frequency adjustments based on presence status
- **MQTT Communication**: Real-time updates to and from the central system
- **TFT Display**: Visual interface for viewing requests and status
- **Responsive Buttons**: Blue (Acknowledge) and Red (Busy) buttons for responding to requests

## Hardware Requirements

- ESP32 Development Board (ESP32-WROOM-32 or similar)
- 2.4" TFT Display (ST7789 SPI interface)
- BLE Beacon (can be another ESP32 or dedicated BLE beacon)
- Power supply (USB or wall adapter)
- Two tactile buttons

## Pin Connections

### Display Connections (SPI)
| TFT Display Pin | ESP32 Pin |
|-----------------|-----------|
| MOSI/SDA        | GPIO 23   |
| MISO            | GPIO 19   |
| SCK/CLK         | GPIO 18   |
| CS              | GPIO 5    |
| DC              | GPIO 21   |
| RST             | GPIO 22   |
| VCC             | 3.3V      |
| GND             | GND       |

## Software Dependencies

The following libraries need to be installed via the Arduino Library Manager:

- WiFi
- PubSubClient (by Nick O'Leary)
- BLEDevice
- BLEServer
- BLEUtils
- BLE2902
- SPI
- Adafruit_GFX
- Adafruit_ST7789
- time
- NimBLE-Arduino (for BLE beacon)

## Setup and Configuration

1. Install the required libraries in Arduino IDE
2. Open `faculty_desk_unit.ino` in Arduino IDE
3. Update the configuration in `config.h`:
   - WiFi credentials (`WIFI_SSID` and `WIFI_PASSWORD`)
   - MQTT broker IP address (`MQTT_SERVER`)
   - Faculty ID and name (`FACULTY_ID` and `FACULTY_NAME`)
   - BLE settings (including always-on option)
4. Compile and upload to your ESP32

## Testing

To test the faculty desk unit, you can use the new BLE test script:

1. Make sure the central system is running
2. Make sure the MQTT broker is running
3. Run the BLE test script:
   ```bash
   python scripts/test_ble_connection.py test
   ```

This script will:
1. Simulate a BLE beacon
2. Simulate a faculty desk unit
3. Test MQTT communication between components
4. Verify proper status updates

You can also use the older test scripts in the `test_scripts` directory:
- On Windows: `test_scripts\test_faculty_desk_unit.bat`
- On Linux/macOS: `bash test_scripts/test_faculty_desk_unit.sh`

## Usage

1. The unit will automatically connect to WiFi and the MQTT broker
2. It will act as a BLE server waiting for BLE client connections
3. When a BLE client (faculty keychain) connects, the faculty status is set to "Available"
4. When the BLE client disconnects, the faculty status is set to "Unavailable"
5. Consultation requests from students will appear on the display

### BLE Always-Available Feature (Optional)

The faculty desk unit includes an optional "Always Available" mode that can be enabled in the config.h file:

```cpp
// Set to true to make faculty always appear as available regardless of BLE connection
#define ALWAYS_AVAILABLE true
```

When this feature is enabled:
- The faculty status is always shown as "Available" in the central system regardless of BLE connection
- The unit will still accept real BLE client connections, but won't change status when they disconnect
- Every 5 minutes, the unit sends a "keychain_connected" message to ensure the faculty remains available
- This feature is useful for faculty members who want to be always available for consultations

By default, this feature is disabled (set to `false`), meaning the faculty status will accurately reflect the actual BLE connection status.

### Database Integration

The central system has been updated to support the always-on BLE client feature:
- A new "always_available" field has been added to the Faculty model
- Faculty members with this flag set will always be shown as available
- The admin dashboard has been updated to allow setting this flag
- The Jeysibn faculty member is set to always available by default

To update an existing database with the new schema, run:
```
python scripts/update_faculty_schema.py
python scripts/update_jeysibn_faculty.py
```

## Manual Testing

You can also test the faculty desk unit manually:

1. Create a faculty member:
   ```
   python test_scripts/create_jeysibn_faculty.py
   ```

2. Simulate BLE beacon connected event:
   ```
   python test_scripts/simulate_ble_connection.py --broker <mqtt_broker_ip> --connect
   ```

3. Send a consultation request:
   ```
   python test_scripts/send_consultation_request.py
   ```

4. Simulate BLE beacon disconnected event:
   ```
   python test_scripts/simulate_ble_connection.py --broker <mqtt_broker_ip> --disconnect
   ```

Replace `<mqtt_broker_ip>` with the IP address of your MQTT broker.

## Troubleshooting

### MQTT Connection Issues

If the faculty desk unit is not connecting to the MQTT broker:
- Make sure the MQTT broker IP address is correct
- Make sure the MQTT broker is running
- Make sure the ESP32 is connected to the WiFi network

### BLE Issues

The faculty desk unit is configured to always report as connected, but if you want to connect a real BLE client:
- Make sure the BLE client (keychain) is powered on
- Make sure the BLE client is within range of the ESP32
- Check the serial output for BLE-related messages
- Note that disconnecting a real BLE client will not change the faculty status (it will remain "Available")

### Display Issues

If the display is not working:
- Check the wiring connections
- Make sure the display is powered on
- Try running the test screen function to verify the display is working

## Integration with Central System

### MQTT Communication
The desk unit communicates with the central system using MQTT with the following topics:

| Topic Type | Description |
|------------|-------------|
| `consultease/faculty/{id}/status` | Status updates (availability, grace period) |
| `consultease/faculty/{id}/request` | Incoming consultation requests |
| `consultease/faculty/{id}/response` | Responses to consultation requests |
| `consultease/faculty/{id}/heartbeat` | System health monitoring |

For backward compatibility, legacy topics (`faculty/1/status`, etc.) are also supported.

### Status Messages
Status messages include the following information:
```json
{
  "faculty_id": 1,
  "faculty_name": "Dave Jomillo",
  "present": true,
  "status": "AVAILABLE",
  "department": "Helpdesk",
  "timestamp": "1621234567890",
  "in_grace_period": false
}
```

When in grace period mode, additional fields are included:
```json
{
  "in_grace_period": true,
  "grace_period_remaining": 45000
}
```

### Response Messages
When responding to consultation requests, the desk unit sends:
```json
{
  "faculty_id": 1,
  "faculty_name": "Dave Jomillo",
  "response_type": "ACKNOWLEDGE", // or "BUSY"
  "message_id": "1621234567890_1234",
  "original_message": "Student consultation request",
  "timestamp": "1621234567890",
  "status": "Professor acknowledges the request and will respond accordingly"
}
```

## Configuration

### Software Requirements
- Arduino IDE
- Required Libraries:
  - WiFi
  - PubSubClient
  - BLEDevice/BLEScan/BLEAdvertisedDevice
  - Adafruit_GFX
  - Adafruit_ST7789
  - SPI

### Configuration Files
- `config.h`: Main configuration (faculty info, MQTT, BLE, display)
- `mqtt_topics.h`: MQTT topic definitions matching central system

## Installation and Setup

1. Clone the repository
2. Update `config.h` with appropriate values:
   - Faculty information
   - WiFi credentials
   - MQTT broker details
   - BLE beacon MAC address
3. Upload the code to the ESP32
4. Ensure the central system is configured to recognize the faculty desk unit

## Grace Period System

The enhanced BLE detection system includes a 1-minute grace period for disconnections, which helps prevent false absence detections due to temporary BLE signal issues. When a faculty member's BLE beacon disconnects, the system:

1. Enters a grace period state
2. Maintains "AVAILABLE" status during the grace period
3. Makes multiple reconnection attempts at specified intervals
4. Only changes to "AWAY" if the grace period expires without reconnection

This feature significantly improves reliability in real-world environments where BLE signals can be temporarily obstructed or interfered with.

## Troubleshooting

- **LED Indicators**: Green LED for available status, Red LED for unavailable
- **Serial Debugging**: Connect via USB and monitor the serial output at 115200 baud
- **Status Panel**: The bottom section of the display shows WiFi, MQTT, and BLE connection status