# ConsultEase System

## Overview

ConsultEase is a student-faculty interaction system designed to facilitate consultation scheduling and availability tracking. The system consists of two main components:

1. **Central System (Raspberry Pi)**: The core system that manages the database, user interface, and communication with Faculty Desk Units.
2. **Faculty Desk Unit (ESP32)**: A hardware device placed at faculty desks that displays consultation requests and indicates faculty availability.

## System Architecture

### Central System
- **Hardware**: Raspberry Pi
- **Framework**: PyQt5 for the user interface
- **Database**: PostgreSQL/SQLite
- **Communication**: MQTT for real-time messaging
- **Authentication**: RFID for student and faculty authentication

### Faculty Desk Unit
- **Hardware**: ESP32 microcontroller with TFT display
- **Connectivity**: WiFi for MQTT communication, BLE for presence detection
- **Interface**: TFT display, buttons for user interaction
- **Power Management**: Power saving modes to extend battery life

## Implementation Phases

The implementation of the ConsultEase system has been divided into four phases:

1. **Phase 1** (High Priority): Core functionality implementation (hardware integration, basic UI, MQTT, BLE)
2. **Phase 2** (High Priority): Security enhancements (MQTT TLS, secure configuration)
3. **Phase 3** (Medium Priority): Code organization improvements (modular design, manager classes)
4. **Phase 4** (Low Priority): Testing and simulation (unit tests, integration tests, simulation mode)

## Project Structure

```
ConsultEaseProMax/
├── central_system/           # Central System components
│   ├── controllers/          # Business logic
│   ├── models/               # Database models
│   ├── views/                # UI components
│   ├── services/             # Service components (MQTT, RFID)
│   └── utils/                # Utility functions
├── faculty_desk_unit/        # Faculty Desk Unit firmware
│   ├── faculty_desk_unit.ino # Main Arduino sketch
│   ├── display_manager.h     # Display management
│   ├── network_manager.h     # WiFi and MQTT management
│   ├── ble_manager.h         # BLE scanning and presence detection
│   ├── consultation_manager.h # Consultation request handling
│   ├── button_manager.h      # Button interaction
│   ├── power_manager.h       # Power management
│   ├── config.h              # Configuration parameters
│   ├── faculty_constants.h   # Faculty-specific constants
│   └── test/                 # Testing framework
│       ├── framework/        # Core testing utilities
│       ├── mocks/            # Mock objects for hardware components
│       ├── unit/             # Unit tests
│       ├── integration/      # Integration tests
│       └── simulation/       # Simulation mode
└── docs/                     # Documentation
```

## Testing Framework

### Overview
The ConsultEase Faculty Desk Unit includes a comprehensive testing framework to ensure reliable operation. The framework includes:

- **Unit Tests**: Individual tests for each manager class
- **Integration Tests**: Tests for interactions between components
- **Mock Objects**: Mock implementations of hardware-dependent components
- **Assertion Macros**: Rich set of test assertions for various conditions
- **Memory Testing**: Detection of memory leaks and performance issues

### Running Tests
To run the unit tests:

1. Connect the ESP32 to your computer
2. Flash the test runner: `faculty_desk_unit/test/test_runner.cpp`
3. Monitor the serial output at 115200 baud
4. Results will be displayed with pass/fail status and timing information

## Simulation Mode

### Overview
The simulation mode allows testing the Faculty Desk Unit without actual hardware. It simulates various scenarios to validate system behavior under different conditions.

### Features
- Complete system simulation without hardware
- Scenario-based testing (normal operation, WiFi disconnection, etc.)
- Time-based progression through scenarios
- Manual scenario triggering via serial commands
- Visual representation of display content

### Running Simulation
To run the simulation mode:

1. Connect the ESP32 to your computer
2. Flash the simulation runner: `faculty_desk_unit/test/simulation/simulation_runner.cpp`
3. Monitor the serial output at 115200 baud
4. Simulation will progress automatically through scenarios
5. Send commands 1-5 via serial to manually trigger specific scenarios
6. Send 'q' to quit the simulation

## Configuration

The Faculty Desk Unit is configured through the `config.h` and `faculty_constants.h` files. Key configuration parameters include:

- WiFi credentials
- MQTT broker settings
- TLS security options
- Faculty information
- BLE scanning parameters
- Display settings
- Power management options

## Development Setup

### Prerequisites
- Arduino IDE 1.8.x or higher
- ESP32 board support
- Required libraries:
  - Adafruit GFX
  - Adafruit ST7789
  - NimBLE-Arduino
  - PubSubClient
  - ArduinoJson

### Installing Dependencies
Use the Arduino Library Manager to install the required libraries:

1. Open Arduino IDE
2. Go to Sketch -> Include Library -> Manage Libraries
3. Search for and install the required libraries

### Building and Flashing
To build and flash the Faculty Desk Unit firmware:

1. Open `faculty_desk_unit.ino` in Arduino IDE
2. Select your ESP32 board from Tools -> Board
3. Select the correct port from Tools -> Port
4. Click Upload

## Contributing

Contributions to the ConsultEase project are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests to ensure functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.