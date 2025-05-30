/**
 * ConsultEase - Faculty BLE Beacon Configuration
 * 
 * This file contains configuration settings for the Faculty BLE Beacon.
 * Update these values to match your specific setup.
 */

#ifndef BLE_BEACON_CONFIG_H
#define BLE_BEACON_CONFIG_H

// ================================
// FACULTY BLE BEACON CONFIGURATION
// ================================
// This beacon is carried by the faculty member and broadcasts 
// a unique identifier that the desk unit can recognize

// Faculty information
#define FACULTY_ID 1
#define FACULTY_NAME "Dave Jomillo"
#define FACULTY_DEPARTMENT "Helpdesk"

// BLE iBeacon parameters
#define BEACON_UUID "FDA50693-A4E2-4FB1-AFCF-C6EB07647825" // Keep this consistent with desk unit
#define BEACON_MAJOR 1  // Should match faculty ID
#define BEACON_MINOR 1  // Can be used for multiple beacons per faculty

// Broadcast parameters
#define TX_POWER -59  // Calibrated TX power at 1m in dBm
#define ADVERTISING_INTERVAL 200  // Advertising interval in ms (200ms = good battery life)
#define MANUFACTURER_ID 0x4C00  // Apple's ID (standard for iBeacon)

// Battery management
#define ENABLE_BATTERY_MANAGEMENT true
#define SLEEP_AFTER_MINUTES 240  // Sleep after 4 hours of no movement to save battery
#define BATTERY_CHECK_INTERVAL 60000  // Check battery level every minute

// Device configuration
#define DEVICE_NAME "Faculty1_Beacon"  // Bluetooth device name

// Debug settings
#define ENABLE_SERIAL_DEBUG true
#define SERIAL_BAUD_RATE 115200

// Helper macros
#define DEBUG_PRINT(x) if(ENABLE_SERIAL_DEBUG) Serial.print(x)
#define DEBUG_PRINTLN(x) if(ENABLE_SERIAL_DEBUG) Serial.println(x)
#define DEBUG_PRINTF(format, ...) if(ENABLE_SERIAL_DEBUG) Serial.printf(format, ##__VA_ARGS__)

#endif // BLE_BEACON_CONFIG_H
