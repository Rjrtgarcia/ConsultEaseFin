/**
 * ConsultEase - Faculty Desk Unit Configuration
 *
 * This file contains configuration settings for the Faculty Desk Unit.
 * Update these values to match your specific setup.
 */

#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
#define WIFI_SSID "ConsultEase"
#define WIFI_PASSWORD "Admin123"

// MQTT Configuration
#define MQTT_SERVER "172.20.10.8"  // Updated to match central system's MQTT broker IP
#define MQTT_PORT 1883
#define MQTT_USERNAME ""  // Leave empty if not using authentication
#define MQTT_PASSWORD ""  // Leave empty if not using authentication

// Faculty Configuration
#define FACULTY_ID 3  // This should match the faculty ID in the database
#define FACULTY_NAME "Jeysibn"  // This should match the faculty name in the database
#define FACULTY_DEPARTMENT "Computer Science"  // This should match the faculty department in the database

// BLE Configuration
#define BLE_SCAN_INTERVAL 5000  // Scan interval in milliseconds
#define BLE_SCAN_DURATION 3     // Scan duration in seconds
#define BLE_RSSI_THRESHOLD -80  // RSSI threshold for presence detection (higher values = closer proximity required)

// Display Configuration
#define TFT_ROTATION 1  // 0=Portrait, 1=Landscape, 2=Inverted Portrait, 3=Inverted Landscape

// Color Scheme - National University Philippines
#define NU_BLUE      0x0015      // Dark blue (navy) - Primary color
#define NU_GOLD      0xFE60      // Gold/Yellow - Secondary color
#define NU_DARKBLUE  0x000B      // Darker blue for contrasts
#define NU_LIGHTGOLD 0xF710      // Lighter gold for highlights
#define TFT_WHITE    0xFFFF      // White for text
#define TFT_BLACK    0x0000      // Black for backgrounds

// UI Colors
#define TFT_BG       NU_BLUE         // Background color
#define TFT_TEXT     TFT_WHITE       // Text color
#define TFT_HEADER   NU_DARKBLUE     // Header color
#define TFT_ACCENT   NU_GOLD         // Accent color
#define TFT_HIGHLIGHT NU_LIGHTGOLD   // Highlight color

// MQTT Topics - Standardized format
#define MQTT_TOPIC_STATUS "consultease/faculty/%d/status"  // %d will be replaced with FACULTY_ID
#define MQTT_TOPIC_REQUESTS "consultease/faculty/%d/requests"  // %d will be replaced with FACULTY_ID
#define MQTT_TOPIC_MESSAGES "consultease/faculty/%d/messages"  // %d will be replaced with FACULTY_ID
#define MQTT_TOPIC_NOTIFICATIONS "consultease/system/notifications"

// Legacy MQTT Topics - For backward compatibility
#define MQTT_LEGACY_STATUS "professor/status"
#define MQTT_LEGACY_MESSAGES "professor/messages"

// BLE Connection Stability
#define BLE_CONNECTION_TIMEOUT 30000  // Time in ms to consider BLE disconnected if no signal (30 seconds)
#define BLE_RECONNECT_ATTEMPTS 3      // Number of reconnection attempts before giving up
#define BLE_RECONNECT_DELAY 5000      // Delay between reconnection attempts in ms

// Debug Configuration
#define DEBUG_ENABLED true  // Set to false to disable debug output

#endif // CONFIG_H
