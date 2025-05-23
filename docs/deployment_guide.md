# ConsultEase Deployment Guide

This guide provides comprehensive instructions for deploying the complete ConsultEase system, including both the Central System (Raspberry Pi) and the Faculty Desk Units (ESP32). This guide incorporates all recent improvements to the system.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Central System Setup](#central-system-setup)
3. [Faculty Desk Unit Setup](#faculty-desk-unit-setup)
4. [BLE Beacon Setup](#ble-beacon-setup)
5. [Network Configuration](#network-configuration)
6. [Database Setup](#database-setup)
7. [System Testing](#system-testing)
8. [Troubleshooting](#troubleshooting)
9. [Touch Interface Setup](#touch-interface-setup)
10. [Performance Optimization](#performance-optimization)

## Hardware Requirements

### Central System (Raspberry Pi)
- Raspberry Pi 4 (4GB RAM recommended)
- 10.1-inch touchscreen (1024x600 resolution)
- USB RFID IC Reader
- 32GB+ microSD card
- Power supply (5V, 3A recommended)
- Case or mounting solution

### Faculty Desk Unit (per faculty member)
- ESP32 development board
- 2.4-inch TFT SPI Display (ST7789)
- Power supply (USB or wall adapter)
- Case or enclosure

### BLE Beacon (per faculty member)
- ESP32 development board (smaller form factor recommended)
- Small LiPo battery (optional for portable use)
- Case or enclosure

### Additional Requirements
- Local network with Wi-Fi access
- Ethernet cable (optional for Raspberry Pi)
- RFID cards for students

## Central System Setup

### 1. Operating System Installation
1. Download Raspberry Pi OS (64-bit, Bookworm) from the [official website](https://www.raspberrypi.org/software/operating-systems/)
2. Flash the OS to the microSD card using [Raspberry Pi Imager](https://www.raspberrypi.org/software/)
3. Insert the microSD card into the Raspberry Pi and connect the display, keyboard, and mouse
4. Power on the Raspberry Pi and complete the initial setup

### 2. Touchscreen Configuration
1. Connect the touchscreen to the Raspberry Pi
2. Update the system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
3. Configure the display resolution if needed:
   ```bash
   sudo nano /boot/config.txt
   ```
   Add these lines at the end:
   ```
   hdmi_group=2
   hdmi_mode=87
   hdmi_cvt=1024 600 60 6 0 0 0
   ```
4. Save and reboot the Raspberry Pi:
   ```bash
   sudo reboot
   ```

### 3. PostgreSQL Installation
1. Install PostgreSQL:
   ```bash
   sudo apt install postgresql postgresql-contrib -y
   ```
2. Start the PostgreSQL service:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

### 4. MQTT Broker Setup
1. Install Mosquitto MQTT broker:
   ```bash
   sudo apt install mosquitto mosquitto-clients -y
   ```
2. Configure Mosquitto:
   ```bash
   sudo nano /etc/mosquitto/conf.d/consultease.conf 
   # It's better to use a custom config file in conf.d
   ```
   Add basic lines for non-TLS setup:
   ```
   listener 1883
   allow_anonymous true 
   # For production, consider disabling anonymous access and setting up ACLs
   # allow_anonymous false
   # password_file /etc/mosquitto/passwd
   # acl_file /etc/mosquitto/aclfile
   ```
   
   **For TLS Setup (Recommended for Production):**
   If you plan to use TLS for MQTT (configured with `use_tls: true` in `config.json`):
     a. Ensure you have your CA certificate, server certificate, and server key.
     b. Update your Mosquitto configuration (`/etc/mosquitto/conf.d/consultease.conf`) to include:
        ```
        listener 8883 # Default TLS port
        cafile /path/to/your/certs/ca.crt
        certfile /path/to/your/certs/server.crt
        keyfile /path/to/your/certs/server.key
        # Optional: require client certificates if your clients are configured with them
        # require_certificate true 
        # tls_version tlsv1.2 tlsv1.3
        ```
     c. Ensure the paths to `cafile`, `certfile`, and `keyfile` are correct and Mosquitto has read access.
     d. Refer to the "MQTT TLS Configuration" section in `docs/configuration_guide.md` for more details on generating certificates.

3. (If using password file) Create a password file for MQTT users:
   ```bash
   # sudo mosquitto_passwd -c /etc/mosquitto/passwd your_mqtt_user
   ```
4. Start and enable the Mosquitto service:
   ```bash
   sudo systemctl restart mosquitto # Use restart to apply new config
   sudo systemctl enable mosquitto
   ```

### 5. Python Dependencies Installation
1. Install required packages:
   ```bash
   sudo apt install python3-pip python3-pyqt5 python3-evdev -y
   ```
2. Install PyQt5 WebEngine:
   ```bash
   sudo apt install python3-pyqt5.qtwebengine -y 
   # Note: PyQtWebEngine might not be strictly necessary for the core ConsultEase functionality if no web content is embedded. Verify if it's used.
   ```
3. Install Python libraries:
   ```bash
   pip3 install paho-mqtt sqlalchemy psycopg2-binary bcrypt
   # Consider creating and using a requirements.txt:
   # echo "paho-mqtt
sphinx
SQLAlchemy
psycopg2-binary
bcrypt
eventlet
greenlet" > requirements.txt 
   # pip3 install -r requirements.txt
   ```

### 6. ConsultEase Application Setup
1. Clone the ConsultEase repository:
   ```bash
   git clone https://github.com/yourusername/ConsultEase.git
   cd ConsultEase
   ```
2. Set up the database:
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE consultease;"
   sudo -u postgres psql -c "CREATE USER piuser WITH PASSWORD 'password';"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE consultease TO piuser;"
   ```
3. Create and configure `config.json`:
   ```bash
   cd central_system
   cp config.example.json config.json
   nano config.json
   ```
   
   Update the following sections in config.json:
   ```json
   {
     "database": {
       "type": "postgresql",
       "host": "localhost",
       "port": 5432,
       "name": "consultease",
       "user": "piuser",
       "password": "password",
       "sqlite_path": "consultease.db"
     },
     "mqtt": {
       "broker_host": "localhost",
       "broker_port": 1883,
       "client_id_base": "consultease_central",
       "username": "",
       "password": "",
       "use_tls": false,
       "tls_ca_certs": null,
       "tls_certfile": null,
       "tls_keyfile": null,
       "tls_insecure": false,
       "tls_version": "CLIENT_DEFAULT",
       "tls_cert_reqs": "CERT_REQUIRED"
     },
     "rfid_reader": {
       "vid": "0xFFFF",
       "pid": "0x0035",
       "simulation_mode": false,
       "refresh_interval": 300,
       "device_path": null
     },
     "keyboard": {
       "preferred": "squeekboard",
       "fallback": "matchbox-keyboard",
       "show_timeout": 0.5,
       "hide_timeout": 0.5
     },
     "system": {
       "ensure_test_faculty_available": false,
       "fullscreen": true,
       "log_level": "INFO",
       "log_file": "consultease.log",
       "log_max_size": 10485760,
       "log_backup_count": 5,
       "admin_lockout_attempts": 5,
       "admin_lockout_minutes": 30
     },
     "ui": {
       "theme": "light",
       "transition_duration": 300,
       "refresh_interval": 60
     }
   }
   ```
   
   **Important `config.json` Notes:**
   - **Paths:** For paths like `tls_ca_certs`, `tls_certfile`, `tls_keyfile`, and `log_file`, use **absolute paths** when running ConsultEase as a systemd service to avoid issues with relative path resolution.
   - **RFID VID/PID:** You can determine the VID/PID of your RFID reader using `lsusb` and then looking for your device, or by checking kernel messages (`dmesg`) when you plug it in. The `scripts/fix_rfid.sh` might also help identify it or set permissions.
   - **Permissions:** Ensure `config.json` has restricted read permissions for the user running the application (e.g., `chown pi:pi config.json && chmod 600 config.json`).
   - **Log Directory:** If `log_file` points to a directory like `/var/log/consultease/`, ensure this directory exists and the application user (`pi` in the service example) has write permissions to it.
     ```bash
     # sudo mkdir /var/log/consultease
     # sudo chown pi:pi /var/log/consultease
     ```

4. Run the application for testing:
   ```bash
   cd ..
   python3 central_system/main.py
   ```

### 7. Auto-start Configuration
1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/consultease.service
   ```
2. Add the following content:
   ```
   [Unit]
   Description=ConsultEase Central System
   After=network.target postgresql.service mosquitto.service

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/ConsultEase/central_system/main.py
   WorkingDirectory=/home/pi/ConsultEase
   StandardOutput=inherit
   StandardError=inherit
   Restart=always
   User=pi

   [Install]
   WantedBy=multi-user.target
   ```
3. Enable and start the service:
   ```bash
   sudo systemctl enable consultease.service
   sudo systemctl start consultease.service
   ```

## Faculty Desk Unit Setup

### 1. Arduino IDE Installation
1. Download and install the Arduino IDE from the [official website](https://www.arduino.cc/en/software)
2. Install the ESP32 board package:
   - In Arduino IDE, go to File > Preferences
   - Add this URL to the "Additional Boards Manager URLs" field:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to Tools > Board > Boards Manager
   - Search for ESP32 and install the latest version

### 2. Required Libraries Installation
Install the following libraries via the Arduino Library Manager (Tools > Manage Libraries):
- TFT_eSPI by Bodmer
- PubSubClient by Nick O'Leary
- ArduinoJson by Benoit Blanchon
- NimBLE-Arduino by h2zero

### 3. TFT_eSPI Configuration
1. Navigate to your Arduino libraries folder (usually in Documents/Arduino/libraries)
2. Find the TFT_eSPI folder
3. Replace the User_Setup.h file with the one from the ConsultEase repository
4. Alternatively, edit the file to match your display configuration

### 4. Faculty Desk Unit Firmware Upload
1. Open the `faculty_desk_unit.ino` file in Arduino IDE
2. Update the configuration section with your settings:
   - WiFi credentials
   - MQTT broker address (Raspberry Pi IP)
   - Faculty ID (matching database record)
   - Faculty name
   - BLE settings (including always-on option)
3. Connect the ESP32 to your computer via USB
4. Select the correct board and port in Arduino IDE
5. Click the Upload button
6. Monitor the serial output to verify the connection

Note: The faculty desk unit now supports an always-on BLE option, which keeps the faculty status as "Available" even when no BLE beacon is detected. This is configured in the `config.h` file.

## BLE Beacon Setup

### 1. Testing BLE Functionality
Before deploying the BLE beacons, you can test the BLE functionality using the provided test script:
```bash
cd /path/to/consultease
python scripts/test_ble_connection.py test
```

This script will:
- Simulate a BLE beacon
- Simulate a faculty desk unit
- Test MQTT communication between components
- Verify proper status updates

### 2. BLE Beacon Firmware Upload
1. Open the `faculty_desk_unit/ble_beacon/ble_beacon.ino` file in Arduino IDE
2. Update the configuration in `ble_beacon/config.h`:
   - Faculty ID (matching database record)
   - Faculty name
   - Device name
   - Advertising interval
3. Connect the ESP32 to your computer via USB
4. Select the correct board and port in Arduino IDE
5. Click the Upload button
6. Monitor the serial output to get the MAC address of the beacon
7. Note this MAC address for use in the Faculty Desk Unit configuration

### 3. Beacon Configuration
1. Optionally, customize the beacon settings:
   - Device name
   - Advertising interval
   - LED behavior
2. For battery-powered operation, configure power management settings

### 4. MQTT Communication Testing
Test the MQTT communication between components:
```bash
# Subscribe to faculty status topic
mosquitto_sub -t "consultease/faculty/+/status"

# Subscribe to consultation requests topic
mosquitto_sub -t "consultease/faculty/+/requests"

# Publish a test message
mosquitto_pub -t "consultease/faculty/1/status" -m "keychain_connected"
```

## Network Configuration

### 1. Static IP for Raspberry Pi (Recommended)
1. Edit the DHCP configuration:
   ```bash
   sudo nano /etc/dhcpcd.conf
   ```
2. Add these lines (adjust based on your network):
   ```
   interface eth0  # or wlan0 for WiFi
   static ip_address=192.168.1.100/24
   static routers=192.168.1.1
   static domain_name_servers=192.168.1.1 8.8.8.8
   ```
3. Restart networking:
   ```bash
   sudo systemctl restart dhcpcd
   ```

### 2. Port Forwarding (Optional for Remote Access)
Configure your router to forward the necessary ports if remote access is required:
- Port 1883 for MQTT
- Port 5432 for PostgreSQL (not recommended for direct internet exposure)

## Database Setup

### 1. Initial Data Setup
1. Create a script to add initial admin user:
   ```bash
   sudo nano add_admin.py
   ```
2. Add the following content:
   ```python
   from central_system.models import Admin, init_db
   from central_system.controllers import AdminController

   # Initialize database
   init_db()

   # Create admin controller
   admin_controller = AdminController()

   # Ensure default admin exists
   admin_controller.ensure_default_admin()

   print("Default admin created with username 'admin' and password 'admin123'")
   print("Please change this password immediately!")
   ```
3. Run the script:
   ```bash
   python3 add_admin.py
   ```

### 2. Sample Data (Optional)
1. Create a script to add sample data for testing:
   ```bash
   sudo nano add_sample_data.py
   ```
2. Add faculty and student records as needed
3. Run the script:
   ```bash
   python3 add_sample_data.py
   ```

## System Testing

### 1. UI Improvements Testing
Test the improved UI components:
```bash
cd /path/to/consultease
python scripts/test_ui_improvements.py
```

This script will:
- Test the improved UI transitions
- Test the enhanced consultation panel
- Verify smooth animations and proper user feedback

### 2. Central System Testing
1. Verify RFID scanning works:
   - Scan an RFID card at the login screen
   - Check the logs for detection
2. Test faculty status display:
   - Verify faculty cards show the correct status
3. Test consultation requests:
   - Submit a test consultation request
   - Verify it appears in the database
   - Verify MQTT message is sent
4. Test UI improvements:
   - Verify smooth transitions between screens
   - Test the improved consultation panel
   - Check that the logout button is properly sized

### 3. Faculty Desk Unit Testing
1. Verify connectivity:
   - Check WiFi connection
   - Verify MQTT connection to Raspberry Pi
2. Test BLE detection:
   - Bring the BLE beacon near the unit
   - Verify status changes to "Available"
   - Move the beacon away
   - If not using always-on mode, verify status changes to "Unavailable" after timeout
   - If using always-on mode, verify status remains "Available"
3. Test consultation display:
   - Submit a consultation request from the Central System
   - Verify it appears on the Faculty Desk Unit display
4. Test BLE functionality with the test script:
   ```bash
   python scripts/test_ble_connection.py test
   ```

## Troubleshooting

### Central System Issues
- **RFID reader not detected**: Check USB connection and device permissions
- **Database connection errors**: Verify PostgreSQL is running and credentials are correct
- **UI scaling issues**: Adjust Qt screen scaling or resolution settings
- **On-screen keyboard not appearing**: Run `~/keyboard-show.sh` or press F5 to toggle keyboard

### Faculty Desk Unit Issues
- **WiFi connection problems**: Check network credentials and signal strength
- **Display not working**: Verify SPI connections and TFT_eSPI configuration
- **BLE detection issues**: Check beacon MAC address and RSSI threshold
- **Always showing Available**: This is expected if using the always-on BLE option in config.h

### MQTT Communication Issues
- **Connection failures**: Verify Mosquitto is running and accessible
- **Message not received**: Check topic names and subscription status
- **Delayed updates**: Check network latency and MQTT QoS settings
- **Reconnection issues**: The system now uses exponential backoff for reconnection attempts

### UI Issues
- **Transitions not working**: Some platforms may not support opacity-based transitions
- **Consultation panel not refreshing**: Check auto-refresh timer settings
- **Keyboard not appearing**: Try different keyboard types (squeekboard, onboard)

### For Additional Help
- Check the logs:
  ```bash
  journalctl -u consultease.service
  ```
- Review MQTT messages:
  ```bash
  mosquitto_sub -t "consultease/#" -v
  ```
- Monitor database:
  ```bash
  sudo -u postgres psql -d consultease
  ```

## Touch Interface Setup

ConsultEase is designed to work with a touchscreen interface on the Raspberry Pi. The system uses a `KeyboardManager` to automatically show and hide a virtual keyboard when text fields receive focus.

### 1. Install On-Screen Keyboard(s)

Ensure your desired virtual keyboard(s) are installed. Supported options include `squeekboard` and `matchbox-keyboard`.

```bash
# Example: Install squeekboard (recommended)
sudo apt update
sudo apt install squeekboard -y

# Example: Install matchbox-keyboard (fallback option)
# sudo apt install matchbox-keyboard -y
```
Refer to `scripts/install_squeekboard.sh` or `scripts/install_matchbox_keyboard.sh` if they exist in your project for more specific installation steps.

### 2. Configure Preferred Keyboard

The `KeyboardManager` will attempt to use the keyboard specified in `central_system/config.json`. Update the `keyboard` section:

```json
"keyboard": {
  "preferred": "squeekboard",    // Your preferred keyboard (e.g., "squeekboard", "matchbox-keyboard")
  "fallback": "matchbox-keyboard", // Fallback if preferred is not found
  "show_timeout": 0.5,           // Delay before showing keyboard (seconds)
  "hide_timeout": 0.5            // Delay before hiding keyboard (seconds)
}
```

### 3. Enable Fullscreen Mode

Fullscreen mode is controlled by the `system.fullscreen` setting in `central_system/config.json`:

```json
"system": {
  // ... other system settings ...
  "fullscreen": true, // Set to true for fullscreen, false for windowed
  // ... other system settings ...
}
```
No manual code changes in `base_window.py` are needed for this.

### 4. Adjust Touch Calibration (if needed)

If the touch input is not aligned correctly with the display:

```bash
# Install the calibration tool
sudo apt install -y xinput-calibrator

# Run the calibration
DISPLAY=:0 xinput_calibrator
```

Follow the on-screen instructions to calibrate your touchscreen.

### 4. Testing the Touch Interface

To test the touch interface and keyboard functionality:

1. Start the ConsultEase application.
2. Tap on any text input field (like the Admin Login username field).
3. The on-screen keyboard, as configured in `config.json`, should automatically appear.
4. When you tap outside the text field or the keyboard's close button (if available), the keyboard should hide.

If the keyboard doesn't behave as expected:
- Verify your `keyboard.preferred` and `keyboard.fallback` settings in `config.json` are correct and the specified keyboards are installed.
- Check the application logs for any errors related to `KeyboardManager`.
- Ensure your Raspberry Pi OS desktop environment is not interfering with the application's keyboard management (e.g., disabling other global on-screen keyboard services if they conflict).

## Performance Optimization

### 1. Database Optimization

For optimal database performance:

1. **PostgreSQL Configuration**:
   Locate your `postgresql.conf` file. The path is typically `/etc/postgresql/<YOUR_PG_VERSION>/main/postgresql.conf` (e.g., `/etc/postgresql/13/main/postgresql.conf` if using PostgreSQL 13). You can find your version by running `psql --version`.
   ```bash
   sudo nano /etc/postgresql/<YOUR_PG_VERSION>/main/postgresql.conf
   ```

   Adjust the following settings based on your Raspberry Pi's resources:
   ```
   shared_buffers = 128MB
   work_mem = 8MB
   maintenance_work_mem = 64MB
   effective_cache_size = 512MB
   ```

2. **Regular Maintenance**:
   ```bash
   # Create a maintenance script
   sudo nano /etc/cron.weekly/consultease-maintenance.sh
   ```

   Add the following content:
   ```bash
   #!/bin/bash
   echo "Running ConsultEase database maintenance..."
   sudo -u postgres psql -d consultease -c "VACUUM ANALYZE;"
   echo "Maintenance complete."
   ```

   Make it executable:
   ```bash
   sudo chmod +x /etc/cron.weekly/consultease-maintenance.sh
   ```

### 2. Application Optimization

1. **Memory Usage**:
   - Monitor memory usage with `htop`
   - If memory usage is high, consider increasing swap space:
     ```bash
     sudo dphys-swapfile swapoff
     sudo nano /etc/dphys-swapfile
     # Set CONF_SWAPSIZE=1024
     sudo dphys-swapfile setup
     sudo dphys-swapfile swapon
     ```

2. **CPU Usage**:
   - The application is optimized to use minimal CPU resources
   - If CPU usage is consistently high, check for background processes

## Maintenance and Updates

### Regular System Updates

It's important to keep the system updated:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update ConsultEase from repository (if applicable)
cd /path/to/consultease # Navigate to your project directory
git pull
# After pulling, check if dependencies need updating (e.g., if requirements.txt changed)
# pip3 install -r requirements.txt --upgrade
# Restart the ConsultEase service if it's running
# sudo systemctl restart consultease.service
```

### Database Backups

Regular database backups are essential. The Admin Dashboard UI for backup/restore is currently a placeholder. Backups must be performed manually using command-line tools.

1. **Automated Backups (Example for PostgreSQL)**:
   ```bash
   # Create a backup script
   sudo nano /etc/cron.daily/consultease-backup.sh
   ```

   Add the following content (adjust `DB_NAME`, `DB_USER`, and `BACKUP_DIR` as needed):
   ```bash
   #!/bin/bash
   BACKUP_DIR="/home/pi/consultease_backups"
   DB_NAME="consultease" # From your config.json
   DB_USER="piuser"      # From your config.json, if pg_dump needs it and not running as postgres user
   
   mkdir -p $BACKUP_DIR
   DATE=$(date +%Y-%m-%d_%H%M%S)
   
   # For PostgreSQL
   # Ensure the user running this script (e.g., root if via cron.daily, or pi if run manually)
   # has permissions to run pg_dump or is the postgres user.
   # Using sudo -u postgres is often safest.
   sudo -u postgres pg_dump $DB_NAME > $BACKUP_DIR/${DB_NAME}_${DATE}.sql
   
   # For SQLite (if using SQLite)
   # SQLITE_PATH="/path/to/your/consultease.db" # From your config.json
   # sqlite3 $SQLITE_PATH ".backup $BACKUP_DIR/consultease_sqlite_${DATE}.db"

   # Keep only the last 7 backups
   ls -t $BACKUP_DIR/${DB_NAME}_*.sql 2>/dev/null | tail -n +8 | xargs rm -f
   ls -t $BACKUP_DIR/consultease_sqlite_*.db 2>/dev/null | tail -n +8 | xargs rm -f
   ```

   Make it executable:
   ```bash
   sudo chmod +x /etc/cron.daily/consultease-backup.sh
   ```

2. **Manual Backups**:
   - **For PostgreSQL**:
     ```bash
     sudo -u postgres pg_dump your_db_name > /path/to/your/backup_file.sql
     ```
     (Replace `your_db_name` with the actual database name from `config.json`)
   - **For SQLite**:
     ```bash
     sqlite3 /path/to/your/consultease.db ".backup /path/to/your/backup_file.db"
     ```
     (Replace `/path/to/your/consultease.db` with the actual path from `config.json`)
   
   Store backups in a secure, separate location. Test restore functionality periodically.

   **To Restore a PostgreSQL backup:**
   ```bash
   # sudo -u postgres psql -d your_db_name -f /path/to/your/backup_file.sql
   ```

   **To Restore an SQLite backup:**
   Simply replace the existing database file with the backup file.