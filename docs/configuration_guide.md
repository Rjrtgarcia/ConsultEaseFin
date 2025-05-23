# ConsultEase Configuration Guide

This guide explains how to use the centralized configuration system introduced in the major architecture refactoring of ConsultEase. The system now uses a single `config.json` file to manage all settings, replacing the previous approach with `settings.ini` and environment variables.

## Configuration Overview

The configuration system has several components:
- `config.py`: The core module that loads and provides access to configuration settings
- `config.json`: The user-modifiable JSON file containing all settings
- `get_config()`: The function used throughout the application to access configuration values

## Creating the Configuration File

The system requires a `config.json` file in the `central_system` directory. To create one:

1. Navigate to the central_system directory:
   ```bash
   cd central_system
   ```

2. Copy the example configuration:
   ```bash
   cp config.example.json config.json
   ```

3. Edit the configuration to match your environment:
   ```bash
   nano config.json
   ```

## Configuration Sections

### Database Configuration

```json
"database": {
  "type": "postgresql",       // "postgresql" or "sqlite"
  "host": "localhost",        // PostgreSQL host (ignored for SQLite)
  "port": 5432,               // PostgreSQL port (ignored for SQLite)
  "name": "consultease",      // Database name
  "user": "piuser",           // PostgreSQL username (ignored for SQLite)
  "password": "password",     // PostgreSQL password (ignored for SQLite)
  "sqlite_path": "consultease.db"  // Path for SQLite file (ignored for PostgreSQL)
}
```

Notes:
- For development, you can use SQLite by changing `type` to `sqlite`
- For production, PostgreSQL is recommended
- Setting `type` automatically determines which other fields are used

### MQTT Configuration

```json
"mqtt": {
  "broker_host": "localhost",   // MQTT broker hostname or IP
  "broker_port": 1883,          // MQTT broker port (usually 1883 or 8883 for TLS)
  "client_id_base": "consultease_central",  // Base client ID (random suffix added)
  "username": "",               // MQTT username (if required)
  "password": "",               // MQTT password (if required)
  "use_tls": false,             // Enable TLS encryption for MQTT
  "tls_ca_certs": null,         // Path to CA certificate file for server verification
  "tls_certfile": null,         // Path to client certificate file
  "tls_keyfile": null,          // Path to client key file
  "tls_insecure": false,        // If true, allows self-signed certs without CA validation (testing only)
  "tls_version": "CLIENT_DEFAULT", // TLS protocol version, e.g., "TLSv1.2", "TLSv1.3", "CLIENT_DEFAULT" (auto-negotiate)
  "tls_cert_reqs": "CERT_REQUIRED" // Server certificate requirements, e.g., "CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"
}
```

Notes:
- For secure MQTT communication, set `use_tls` to `true` and provide certificate paths.
- `tls_insecure` should only be `true` for development/testing with self-signed certificates where the CA isn't fully trusted.
- `tls_version` allows specifying a specific TLS protocol version. "CLIENT_DEFAULT" is often sufficient.
- `tls_cert_reqs` defines how the client handles server certificate validation.
- Client IDs will have a random suffix added to ensure uniqueness.
- Configure the same MQTT broker on ESP32 faculty desk units.

### RFID Reader Configuration

```json
"rfid_reader": {
  "vid": "0xFFFF",             // RFID reader vendor ID in hex format
  "pid": "0x0035",             // RFID reader product ID in hex format
  "simulation_mode": false,    // Enable simulation mode for testing without hardware
  "refresh_interval": 300      // Student data cache refresh interval in seconds
}
```

Notes:
- To find your reader's VID/PID, run `sudo ./scripts/fix_rfid.sh`
- Simulation mode allows testing without an actual RFID reader
- The refresh interval controls how often the student data cache is updated

### Keyboard Configuration

```json
"keyboard": {
  "preferred": "squeekboard",    // Preferred keyboard program
  "fallback": "matchbox-keyboard", // Fallback keyboard program
  "show_timeout": 0.5,           // Delay before showing keyboard (seconds)
  "hide_timeout": 0.5            // Delay before hiding keyboard (seconds)
}
```

Notes:
- The system will try to use the preferred keyboard first, then fallback if not available
- Available options include "squeekboard", "matchbox-keyboard", "onboard", and "florence"
- Install your preferred keyboard using the provided scripts (e.g., `scripts/install_squeekboard.sh`)

### System Configuration

```json
"system": {
  "ensure_test_faculty_available": false,  // Whether to create test faculty on startup
  "fullscreen": true,                      // Start in fullscreen mode
  "log_level": "INFO",                     // Logging level (DEBUG, INFO, WARNING, ERROR)
  "log_file": "consultease.log",           // Path to log file
  "log_max_size": 10485760,                // Max log file size in bytes (e.g., 10MB = 10 * 1024 * 1024)
  "log_backup_count": 5,                   // Number of old log files to keep
  "admin_lockout_attempts": 5,             // Failed attempts before account lockout
  "admin_lockout_minutes": 30              // Duration of account lockout in minutes
}
```

Notes:
- `ensure_test_faculty_available` is useful for development but should be disabled in production.
- `log_max_size` and `log_backup_count` control the log rotation behavior to prevent log files from growing indefinitely.
- The admin lockout settings help protect against brute force attacks.

### UI Configuration

```json
"ui": {
  "theme": "light",                 // UI theme (currently only "light" is fully supported)
  "transition_duration": 300,       // Duration of UI transitions in milliseconds
  "refresh_interval": 60            // Auto-refresh interval for dynamic content (seconds)
}
```

## Environment Variable Override

Any configuration setting can be overridden with environment variables using the following pattern:

```bash
CONSULTEASE_SECTION_KEY=value
```

For example:
- To override the database type: `CONSULTEASE_DATABASE_TYPE=sqlite`
- To override MQTT broker host: `CONSULTEASE_MQTT_BROKER_HOST=192.168.1.100`

Environment variables take precedence over `config.json` values.

## Configuration Access in Code

Throughout the application, configuration values are accessed using the `get_config()` function:

```python
from central_system.config import get_config

# Get a specific value with a default fallback
mqtt_host = get_config("mqtt.broker_host", "localhost")

# Get a whole section
mqtt_config = get_config("mqtt")
```

## Default Configuration

If a required setting is not defined in `config.json` or environment variables, the system will use sensible defaults defined in `config.py`. However, it's best practice to explicitly set all required values.

## Configuration Structure and Paths

When deploying the application, ensure that all paths in the configuration are appropriate for your environment. For example:

- For SystemD service deployment, use absolute paths
- For development, relative paths from the project root are acceptable

## MQTT TLS Configuration

To enable secure MQTT communication:

1. Generate or obtain TLS certificates (refer to your MQTT broker's documentation or standard OpenSSL procedures for generating CA, server, and client certificates/keys).

   Example for self-signed certificates (for testing):
   ```bash
   # Ensure you have openssl installed
   # Create a directory for your certs
   mkdir -p /path/to/your/certs
   cd /path/to/your/certs

   # 1. Generate CA key and certificate
   openssl genrsa -out ca.key 2048
   openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/CN=MyTestCA"

   # 2. Generate Server key and certificate request (CSR)
   #    Replace 'your_broker_hostname' with the actual hostname or IP of your MQTT broker
   openssl genrsa -out server.key 2048
   openssl req -new -key server.key -out server.csr -subj "/CN=your_broker_hostname"

   # 3. Sign the Server certificate with your CA
   openssl x509 -req -days 3650 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt

   # 4. Generate Client key and certificate request (CSR)
   #    Replace 'your_client_identifier' (e.g., "CentralSystemClient")
   openssl genrsa -out client.key 2048
   openssl req -new -key client.key -out client.csr -subj "/CN=your_client_identifier"

   # 5. Sign the Client certificate with your CA
   openssl x509 -req -days 3650 -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt
   ```
   **Note:** For production, use properly signed certificates from a trusted Certificate Authority.

2. Update `config.json` with the relevant certificate paths and TLS settings:
   ```json
   "mqtt": {
     // ... other mqtt settings ...
     "use_tls": true,
     "tls_ca_certs": "/path/to/your/certs/ca.crt",       // Path to CA certificate
     "tls_certfile": "/path/to/your/certs/client.crt",   // Path to client certificate
     "tls_keyfile": "/path/to/your/certs/client.key",    // Path to client key
     "tls_insecure": false,                            // Set to true only for testing if CA is not trusted by client
     "tls_version": "CLIENT_DEFAULT",                  // Or "TLSv1.2", "TLSv1.3"
     "tls_cert_reqs": "CERT_REQUIRED"                  // Or "CERT_OPTIONAL", "CERT_NONE"
   }
   ```

3. Configure your MQTT broker (e.g., Mosquitto) for TLS as well. This typically involves:
   - Setting `listener <port_number>` (e.g., `listener 8883`)
   - Providing `cafile /path/to/your/certs/ca.crt`
   - Providing `certfile /path/to/your/certs/server.crt`
   - Providing `keyfile /path/to/your/certs/server.key`
   - Requiring client certificates (`require_certificate true` if `tls_cert_reqs` is `CERT_REQUIRED` on the client).

   Refer to your MQTT broker's documentation for specific TLS configuration instructions.

## Troubleshooting Configuration Issues

### Syntax Errors in config.json
If the application fails to start with JSON parsing errors:
1. Validate your JSON syntax using an online validator
2. Check for missing commas or braces
3. Ensure all keys and values are properly quoted

### Database Connection Issues
If the application cannot connect to the database:
1. Verify database credentials in `config.json`
2. For PostgreSQL, ensure the service is running: `sudo systemctl status postgresql`
3. For SQLite, ensure the application has write permissions to the database file path

### MQTT Connection Issues
If MQTT communication fails:
1. Verify MQTT broker settings in `config.json`
2. Ensure the broker is running: `sudo systemctl status mosquitto`
3. Test the connection: `mosquitto_sub -h localhost -t test`
4. If using TLS, verify certificate paths and permissions

### RFID Reader Detection Issues
If the RFID reader is not detected:
1. Verify the correct VID/PID in `config.json`
2. Check USB connections and permissions
3. Enable simulation mode for testing without hardware

## Configuration Backup
It's recommended to back up your `config.json` file after making changes:
```bash
cp central_system/config.json central_system/config.json.backup
```

This ensures you can quickly restore working settings if needed. 