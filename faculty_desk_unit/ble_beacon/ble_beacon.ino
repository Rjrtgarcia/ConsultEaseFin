/**
 * ConsultEase - Faculty BLE Beacon
 * 
 * This firmware creates a BLE beacon that faculty members can carry to automatically
 * update their availability status. It can be used on a separate ESP32 device or 
 * even programmed onto a small ESP32-based wearable.
 * 
 * The device advertises a BLE signal with a specific MAC address that the
 * Faculty Desk Unit detects to determine presence.
 */

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEBeacon.h>
#include "config.h"

// ===== Configuration =====
const char* DEVICE_NAME = "ConsultEase-Faculty";  // BLE device name
const int ADVERTISE_INTERVAL = 200;               // Advertising interval in ms
const int LED_PIN = 2;                            // Built-in LED pin (for status indication)

// Battery management
const int BATTERY_PIN = 34;                       // Battery voltage measurement pin (optional)
const float BATTERY_DIVIDER_RATIO = 2.0;          // Voltage divider ratio for battery measurement
const float BATTERY_MAX_VOLTAGE = 4.2;            // Maximum battery voltage
const float BATTERY_MIN_VOLTAGE = 3.3;            // Minimum battery voltage
const float ADC_REFERENCE = 3.3;                  // ADC reference voltage
const int ADC_RESOLUTION = 4095;                  // ADC resolution

// ===== Global Variables =====
bool deviceConnected = false;
unsigned long lastBatteryCheck = 0;
int batteryLevel = 100;
bool lowBatteryWarning = false;

// UUID used for ConsultEase faculty identification
#define SERVICE_UUID        "91BAD35B-F3CB-4FC1-8603-88D5137892A6"
#define CHARACTERISTIC_UUID "D9473AA3-E6F4-424B-B6E7-A5F94FDDA285"

// UUID conversion helper
static BLEUUID convertStringToUUID(const char* uuid_str) {
  uint8_t uuid_bytes[16];
  
  // Parse UUID string (8-4-4-4-12 format) to bytes
  sscanf(uuid_str, 
         "%2hhx%2hhx%2hhx%2hhx-%2hhx%2hhx-%2hhx%2hhx-%2hhx%2hhx-%2hhx%2hhx%2hhx%2hhx%2hhx%2hhx",
         &uuid_bytes[0], &uuid_bytes[1], &uuid_bytes[2], &uuid_bytes[3],
         &uuid_bytes[4], &uuid_bytes[5], &uuid_bytes[6], &uuid_bytes[7],
         &uuid_bytes[8], &uuid_bytes[9], &uuid_bytes[10], &uuid_bytes[11],
         &uuid_bytes[12], &uuid_bytes[13], &uuid_bytes[14], &uuid_bytes[15]);
         
  return BLEUUID(uuid_bytes);
}

void setup() {
    // Initialize serial
    if (ENABLE_SERIAL_DEBUG) {
        Serial.begin(SERIAL_BAUD_RATE);
        delay(1000);
    }
    
    DEBUG_PRINTLN("===== ConsultEase Faculty BLE Beacon =====");
    DEBUG_PRINTF("Faculty: %s (ID: %d)\n", FACULTY_NAME, FACULTY_ID);
    DEBUG_PRINTF("Department: %s\n", FACULTY_DEPARTMENT);
    DEBUG_PRINTF("UUID: %s\n", BEACON_UUID);
    DEBUG_PRINTF("Major: %d, Minor: %d\n", BEACON_MAJOR, BEACON_MINOR);
    
    // Initialize LED
    pinMode(LED_PIN, OUTPUT);
    
    // Initialize BLE device
    BLEDevice::init(DEVICE_NAME);
    
    // Create advertising object
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    
    // Create an iBeacon
    BLEBeacon oBeacon = BLEBeacon();
    oBeacon.setManufacturerId(MANUFACTURER_ID);
    oBeacon.setProximityUUID(convertStringToUUID(BEACON_UUID));
    oBeacon.setMajor(BEACON_MAJOR);
    oBeacon.setMinor(BEACON_MINOR);
    oBeacon.setSignalPower(TX_POWER);
    
    // Set the beacon data
    BLEAdvertisementData oAdvertisementData = BLEAdvertisementData();
    BLEAdvertisementData oScanResponseData = BLEAdvertisementData();
    
    std::string strServiceData = "";
    strServiceData += (char)26;     // Length
    strServiceData += (char)0xFF;   // Type (Manufacturer Specific Data)
    strServiceData += (char)0x4C;   // Company ID (Apple) - LSB
    strServiceData += (char)0x00;   // Company ID (Apple) - MSB
    strServiceData += (char)0x02;   // Beacon Type
    strServiceData += (char)0x15;   // Length of Beacon Data
    
    strServiceData += oBeacon.getData(); 
    oAdvertisementData.addData(strServiceData);
    
    // Set advertising parameters
    pAdvertising->setAdvertisementData(oAdvertisementData);
    pAdvertising->setScanResponseData(oScanResponseData);
    pAdvertising->setAdvertisementType(ADV_TYPE_NONCONN_IND);
    pAdvertising->setMinInterval(ADVERTISING_INTERVAL / 0.625);  // 0.625ms units
    pAdvertising->setMaxInterval(ADVERTISING_INTERVAL / 0.625);
    
    // Start advertising
    pAdvertising->start();
    
    DEBUG_PRINTLN("Beacon started broadcasting!");
    DEBUG_PRINTF("Device name: %s\n", DEVICE_NAME);
    DEBUG_PRINTF("Advertising interval: %dms\n", ADVERTISING_INTERVAL);
    
    // Blink LED to indicate ready
    for (int i = 0; i < 5; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(100);
        digitalWrite(LED_PIN, LOW);
        delay(100);
    }
}

void loop() {
    // Check battery level periodically if enabled
    if (ENABLE_BATTERY_MANAGEMENT && millis() - lastBatteryCheck > BATTERY_CHECK_INTERVAL) {
        checkBatteryLevel();
        lastBatteryCheck = millis();
    }
    
    // Print a status message every 30 seconds
    static unsigned long lastStatusTime = 0;
    if (millis() - lastStatusTime > 30000) {
        DEBUG_PRINTLN("Beacon running...");
        if (ENABLE_BATTERY_MANAGEMENT) {
            DEBUG_PRINTF("Battery level: %d%%\n", batteryLevel);
        }
        lastStatusTime = millis();
    }
    
    // Blink LED occasionally to show it's working
    if (!deviceConnected) {
        // Single short blink every 5 seconds if not connected
        if (millis() % 5000 < 50) {
            digitalWrite(LED_PIN, HIGH);
        } else {
            digitalWrite(LED_PIN, LOW);
        }
    }
    
    // Allow for some power savings
    delay(100);
}

void checkBatteryLevel() {
    // This is a simulated battery check
    // In a real implementation, this would read from an ADC pin
    
    // Simulate battery drain (very slow)
    static unsigned long lastDrain = 0;
    if (millis() - lastDrain > 3600000) {  // Every hour
        batteryLevel--;
        if (batteryLevel < 0) batteryLevel = 0;
        lastDrain = millis();
    }
    
    // Check for low battery warning
    if (batteryLevel < 20 && !lowBatteryWarning) {
        DEBUG_PRINTLN("WARNING: Low battery!");
        lowBatteryWarning = true;
    } else if (batteryLevel >= 20 && lowBatteryWarning) {
        lowBatteryWarning = false;
    }
    
    // In a real implementation, this would calculate battery percentage
    // based on voltage reading from an ADC pin
} 