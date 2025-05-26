# ConsultEase - Technical Context

## Technologies Used

### Central System (Raspberry Pi)

#### Hardware
- **Raspberry Pi 4** (Bookworm 64-bit)
- **10.1-inch touchscreen** (1024x600 resolution)
- **USB RFID IC Reader** (VID/PID configurable via `config.json`)

#### Software
- **Python 3.9+** (Primary programming language)
- **PyQt5** (GUI framework)
- **PostgreSQL** (Production Database) or **SQLite** (Development Database)
- **Paho MQTT** (MQTT client library)
- **SQLAlchemy** (ORM for database operations)
- **evdev** (Linux input device library for RFID reader)
- **bcrypt** (Library for admin password hashing)
- **Virtual Keyboards**: The system uses a `KeyboardManager` to integrate with on-screen keyboards. These are configured via `config.json` (see `keyboard.preferred` and `keyboard.fallback`). Supported and commonly used options include:
    - **Squeekboard** (often preferred for Wayland/touch-centric environments)
    - **Matchbox-keyboard** (a lightweight X11 keyboard)
    - **Onboard** (a feature-rich X11 keyboard)
    - **Florence** (another X11 virtual keyboard)
    *(Note: These keyboards need to be installed on the system separately. KeyboardManager selects from installed and configured options.)*

### Faculty Desk Unit (ESP32)

#### Hardware
- **ESP32 microcontroller**
- **2.4-inch TFT SPI Screen** (ST7789)

#### Software
- **Arduino IDE** (Development environment)
- **ESP32 Arduino Core** (ESP32 support for Arduino)
- **TFT_eSPI** (Display library)
- **NimBLE-Arduino** (BLE library)
- **PubSubClient** (MQTT client library)
- **ArduinoJson** (JSON parsing)

## Configuration Management
- **Central Configuration**: System behavior is primarily controlled by `central_system/config.py`, which loads settings from:
    1.  `config.json` (primary user-configurable file)
    2.  Environment variables (can override `config.json`)
    3.  Default values defined in `config.py` (if not found in `config.json` or env vars).
- **Key Configuration Areas**:
    - Database connection (type, host, port, user, password, name)
    - MQTT broker details (host, port, credentials, TLS settings, client ID base)
    - RFID service (VID, PID, simulation mode)
    - Logging levels and file settings
    - UI settings (theme, transition durations, fullscreen)
    - Keyboard preferences (preferred, fallback)
    - System behavior flags (e.g., `ensure_test_faculty_available`)
- **`settings.ini`**: This file has been **removed**. All its previous functionality is now handled by `config.py` and `config.json`.

## Development Setup

### Central System
1. **OS Configuration**
   - Raspberry Pi OS (Bookworm 64-bit)
   - Desktop environment configured for touchscreen
   - Auto-start application on boot (configurable)

2. **Dependencies**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python and pip
   sudo apt install python3 python3-pip -y
   
   # Install PyQt5
   sudo apt install python3-pyqt5 -y
   
   # Install PostgreSQL (for production)
   sudo apt install postgresql postgresql-contrib -y

   # Install SQLite (for development, usually pre-installed with Python)
   sudo apt install sqlite3 -y 
   
   # Install Python libraries
   # (Consider using a requirements.txt file)
   pip3 install paho-mqtt sqlalchemy psycopg2-binary evdev bcrypt
   
   # Install virtual keyboard (e.g., squeekboard)
   sudo apt install squeekboard -y 
   # or matchbox-keyboard
   # sudo apt install matchbox-keyboard -y
   ```

3. **Database Setup (PostgreSQL Example)**
   ```bash
   # Create database and user (adjust per config.json)
   sudo -u postgres psql -c "CREATE DATABASE consultease_db;"
   sudo -u postgres psql -c "CREATE USER consultease_user WITH PASSWORD 'your_password';"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE consultease_db TO consultease_user;"
   ```
   For SQLite, the database file will be created automatically based on the path in `config.json`.

### Faculty Desk Unit
1. **Arduino IDE Setup**
   - Arduino IDE 2.0+
   - ESP32 board manager URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`

2. **Libraries**
   - TFT_eSPI
   - NimBLE-Arduino
   - PubSubClient
   - ArduinoJson

3. **ESP32 Configuration**
   - Flash with 4MB of program storage
   - PSRAM enabled (if available on the board)

## Communication Protocols

### MQTT
- **Broker**: Mosquitto MQTT broker (or any standard MQTT broker) running on Raspberry Pi or accessible network location. Configured via `config.json`.
- **TLS**: Supported and configurable via `config.json` (ca_certs, certfile, keyfile). Additional options like `tls_version` (e.g., "TLSv1.2", "CLIENT_DEFAULT") and `tls_cert_reqs` (e.g., "CERT_REQUIRED", "CERT_OPTIONAL") are also configurable to fine-tune TLS behavior.
- **Topics** (defined in `central_system/utils/mqtt_topics.py`):
    - `consultease/faculty/{faculty_id}/status` - Faculty status updates (ESP32 publishes here).
    - `consultease/faculty/{faculty_id}/request` - Consultation requests (Central system publishes here, ESP32 subscribes).
    - `consultease/faculty/{faculty_id}/display` - Messages for ESP32 display (Central system publishes, ESP32 subscribes).
    - `consultease/system/heartbeat` - Optional system heartbeat.
- **Legacy Topic `MQTTTopics.LEGACY_FACULTY_STATUS`**: This topic is **no longer used** by the central system. ESP32 firmware confirmed to use the new specific topic.

### Database Schema (SQLAlchemy Models in `central_system/models/`)
```
# models/admin.py
admins
  id (PK, Integer)
  username (String, unique, nullable=False)
  password_hash (String, nullable=False) # bcrypt hash
  salt (String) # Kept for potential SHA256 fallback, bcrypt includes its own.
  is_active (Boolean, default=True)
  failed_login_attempts (Integer, default=0)
  last_failed_login_at (DateTime, nullable=True)
  account_locked_until (DateTime, nullable=True)
  created_at (DateTime, default=func.now())
  updated_at (DateTime, default=func.now(), onupdate=func.now())

# models/faculty.py
faculty
  id (PK, Integer)
  name (String, nullable=False)
  department (String)
  email (String, unique)
  ble_id (String, unique, nullable=True) # For BLE presence
  status (String, default='Unavailable') # e.g., 'Available', 'Unavailable', 'Busy'
  image_path (String, nullable=True)
  is_active (Boolean, default=True)
  created_at (DateTime, default=func.now())
  updated_at (DateTime, default=func.now(), onupdate=func.now())

# models/student.py
students
  id (PK, Integer)
  name (String, nullable=False)
  student_id_number (String, unique, nullable=False) # Official student ID
  department (String)
  rfid_uid (String, unique, nullable=True)
  is_active (Boolean, default=True)
  created_at (DateTime, default=func.now())
  updated_at (DateTime, default=func.now(), onupdate=func.now())

# models/consultation.py
consultations
  id (PK, Integer)
  student_id (FK -> students.id, nullable=False)
  faculty_id (FK -> faculty.id, nullable=False)
  request_message (Text, nullable=True)
  status (String, default='Pending') # Enum: Pending, Approved, Rejected, Completed, Cancelled
  created_at (DateTime, default=func.now())
  updated_at (DateTime, default=func.now(), onupdate=func.now())
  # Relationships defined for student and faculty
```

### BLE Protocol
- **Scanning interval**: Configurable on ESP32 firmware.
- **Service UUID**: Custom UUID for faculty identification, configured in ESP32 firmware.
- **Detection threshold**: RSSI > -80dBm (example, configurable in ESP32 firmware).

## Technical Constraints

1. **Power Considerations**
   - ESP32 should operate on USB power or battery
   - Raspberry Pi requires stable power supply
   - BLE beacons require regular battery maintenance (2-3 week battery life)

2. **Network Requirements**
   - Wi-Fi network available for both devices
   - MQTT broker accessible on local network (or internet if configured)
   - Network ports open for MQTT communication (default: 1883 for non-TLS, 8883 for TLS - configurable)
   - All devices must be on the same logical network to reach the broker

3. **Security Considerations**
   - Admin authentication required for admin dashboard access
   - Admin account lockout mechanism planned (DB fields added to `Admin` model)
   - Secured database connection (credentials in `config.json`)
   - Encrypted MQTT communication (TLS support enhanced with more detailed configuration options).
   - Secure storage of credentials (primarily in `config.json`, ensure file permissions are restricted)
   - Logging uses `RotatingFileHandler` configured via `config.json` for `max_size` and `backup_count` to manage log file growth.

4. **Performance Requirements**
   - UI response time < 500ms
   - MQTT message delivery < 1 second
   - BLE detection latency < 10 seconds
   - System should support up to 50 simultaneous users
   - Database backups should be performed weekly
   - System should maintain >99% uptime

5. **Maintenance Requirements**
   - Regular backups of database data (UI for this is placeholder, use `pg_dump` or `sqlite3 .backup`)
   - Configuration management via `config.json`

## UI Theme and Styling

1. **Color Scheme**
   - Background: White (#ffffff)
   - Primary accent: Navy blue (#0d3b66) for buttons, selection highlighting, and headings
   - Secondary accent: Gold (#ffc233) for primary buttons, tab headers, and subheadings
   - Text: Dark gray (#333333) for optimal readability
   - Status indicators: Green (#28a745) for available, Red (#e63946) for unavailable

2. **Styling Approach**
   - Modern, clean design with consistent spacing
   - Touch-optimized element sizing (minimum 48x48px touch targets)
   - Cohesive styling through centralized stylesheet.py
   - Light theme with high contrast for readability
   - Custom styling for faculty cards and interactive elements

3. **Theme Configuration**
   - Default theme set in `config.py` defaults, can be overridden by `config.json` or `CONSULTEASE_THEME` environment variable

4. **Virtual Keyboard**
   - Managed by the `KeyboardManager` service (see `systemPatterns.md` for architectural details).
   - `KeyboardManager` attempts to use the `preferred` keyboard (e.g., `squeekboard`, `matchbox-keyboard`) as defined in `config.json` (`keyboard.preferred`), with a `keyboard.fallback` option if the preferred one is not available or fails.
   - Installation of the actual keyboard programs (like `squeekboard`) is a system setup step (see `deployment_guide.md`).

5. **QTableWidget Layout Challenges**
   - Achieving consistent and balanced column widths in `QTableWidget` (e.g., for the consultation history) often requires a careful combination of `setSectionResizeMode`, `setColumnWidth`, and `setMinimumSectionSize` on the `QHeaderView` and `QTableWidget` itself. Using `ResizeToContents` for columns with custom widgets (like styled `QLabel` for status badges) or multiple buttons needs to be balanced with fixed or interactive widths for other columns to prevent overly cramped or excessively wide layouts.

## Development Workflow
1. Feature branch development
2. Local testing on development hardware/simulators
3. Integration testing with both components
4. Deployment to production hardware 