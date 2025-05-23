# ConsultEase

A comprehensive system for enhanced student-faculty interaction, featuring RFID-based authentication, real-time faculty availability, and streamlined consultation requests.

**This system has recently undergone significant refactoring to improve stability, maintainability, and configurability.**

## Components

### Central System (Raspberry Pi)
- PyQt5 user interface for student interaction
- RFID-based authentication (student data cached for performance, VID/PID configurable)
- Real-time faculty availability display
- Consultation request management with improved UI
- Secure admin interface with bcrypt password hashing and account lockout fields
- Touch-optimized UI with on-screen keyboard support (managed by `KeyboardManager`, configurable)
- Smooth UI transitions and animations
- **Centralized configuration** via `config.py` and `config.json`
- **Singleton controllers** for all major system components

### Faculty Desk Unit (ESP32)
- 2.4" TFT Display for consultation requests
- BLE-based presence detection (configurable always-available mode)
- MQTT communication with Central System (supports TLS)
- Real-time status updates
- Improved reliability and error handling

## Requirements

### Central System
- Raspberry Pi 4 (Bookworm 64-bit)
- 10.1-inch touchscreen (1024x600 resolution)
- USB RFID IC Reader (VID/PID must be specified in `config.json`)
- Python 3.9+
- PostgreSQL database (for production) or SQLite (for development)

### Faculty Desk Unit
- ESP32 microcontroller
- 2.4-inch TFT SPI Screen (ST7789)
- Arduino IDE 2.0+

## Recent Major Refactoring

The system has recently undergone substantial architectural improvements:

- **Centralized Configuration**: All settings are now managed through `config.py` loading from `config.json` and environment variables
- **Singleton Controllers**: All controllers (`AdminController`, `FacultyController`, `ConsultationController`, `RFIDController`, and `StudentController`) are now singletons
- **Improved Database Session Management**: Using `@db_operation_with_retry` decorator and consistent `try/finally close_db()` patterns
- **RFID Performance**: Added student data caching in `RFIDService` to reduce database queries
- **Enhanced Security**: Added bcrypt password hashing and account lockout fields for admin users
- **Unified Keyboard Management**: Consolidated into `KeyboardManager`, removing `direct_keyboard.py`
- **MQTT TLS Support**: Added structure for secure MQTT communication
- **Standardized Error Handling and Logging**: Removed redundant initialization, centralized logging setup
- **Better Maintainability**: Removed legacy code and made development/testing features configurable

## Installation

### Central System

1. **Create configuration file**:
   Copy the example configuration and adjust it for your environment:
   ```bash
   cp central_system/config.example.json central_system/config.json
   # Edit config.json with your specific settings
   ```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up database (PostgreSQL example - adjust based on your `config.json`):
```bash
# Create database and user (names should match your config.json)
sudo -u postgres psql -c "CREATE DATABASE consultease_db;"
sudo -u postgres psql -c "CREATE USER consultease_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE consultease_db TO consultease_user;"
```

4. Install and configure virtual keyboard:
```bash
# Either squeekboard (preferred) or matchbox-keyboard
sudo apt install squeekboard -y
# OR
sudo apt install matchbox-keyboard -y

# Update the keyboard preferences in config.json after installation
```

5. Run the application:
```bash
python central_system/main.py
```

The system will initialize the database on first run and create default records if needed.

### Faculty Desk Unit

1. Install the Arduino IDE and required libraries:
   - TFT_eSPI
   - NimBLE-Arduino
   - PubSubClient
   - ArduinoJson

2. Configure TFT_eSPI for your display

3. Update the configuration in faculty_desk_unit/faculty_desk_unit.ino:
   - Set the faculty ID and name
   - Configure WiFi credentials
   - Set MQTT broker IP address
   - Configure BLE settings

4. Upload the sketch to your ESP32

5. Test the faculty desk unit using the unified test utility

## Development

### Project Structure
```
consultease/
├── central_system/           # Raspberry Pi application
│   ├── config.json           # Main configuration file (must be created)
│   ├── config.example.json   # Example configuration template
│   ├── config.py             # Configuration loading logic
│   ├── models/               # Database models (SQLAlchemy)
│   ├── views/                # PyQt UI components
│   ├── controllers/          # Application logic (all Singletons)
│   ├── services/             # External services (MQTT, RFID)
│   ├── resources/            # UI resources (icons, stylesheets)
│   └── utils/                # Utility functions (incl. KeyboardManager)
├── faculty_desk_unit/        # ESP32 firmware
│   └── faculty_desk_unit.ino # Main firmware file with configuration
├── scripts/                  # Utility scripts
├── tests/                    # Test suite
├── memory-bank/              # Project documentation for AI development
└── docs/                     # Documentation
```

## Configuration (`config.json`)

The system is now driven by a centralized configuration system. The main settings include:

- **Database**: Type (sqlite/postgresql), connection details
- **MQTT**: Broker details, credentials, TLS settings, client ID
- **RFID**: VID/PID for USB reader, simulation mode
- **UI**: Theme, transition durations, fullscreen mode
- **Keyboard**: Preferred/fallback virtual keyboards
- **Logging**: Levels, file paths, rotation settings
- **System**: Feature flags like `ensure_test_faculty_available`

## Touchscreen Features

ConsultEase includes several features to enhance usability on touchscreen devices:

- **Auto-popup keyboard**: Virtual keyboard appears automatically when text fields receive focus, managed by `KeyboardManager`
- **Fullscreen mode**: Configurable via `config.json` or toggled with F11 key
- **Touch-friendly UI**: Larger buttons and input elements optimized for touch interaction
- **Smooth transitions**: Enhanced UI transitions between screens for better user experience
- **Improved consultation panel**: Better readability and user feedback in the consultation interface

## RFID Configuration

RFID configuration now happens in `config.json`:

```json
{
  "rfid_reader": {
    "vid": "0xVID_HERE",  // e.g., "0xFFFF"
    "pid": "0xPID_HERE",  // e.g., "0x0035"
    "simulation_mode": false
  }
}
```

For automatic detection or troubleshooting, you can still use:

```bash
sudo ./scripts/fix_rfid.sh
```

The script will help you determine the correct VID/PID values to set in your configuration.

## License
[MIT](LICENSE)