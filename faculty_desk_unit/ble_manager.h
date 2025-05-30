/**
 * ConsultEase - BLE Manager
 * 
 * This module handles Bluetooth Low Energy (BLE) functionality for the Faculty Desk Unit,
 * including scanning for faculty devices and presence detection.
 */

#ifndef BLE_MANAGER_H
#define BLE_MANAGER_H

#include <NimBLEDevice.h>
#include "config.h"

// BLE scanning constants
#define BLE_ACTIVE_SCAN true  // Active scanning gets more data
#define BLE_SCAN_INTERVAL 100 // Interval between scan windows (in ms * 0.625)
#define BLE_SCAN_WINDOW 99    // Scan window size (in ms * 0.625)

class BLEManager {
private:
    NimBLEScan* pBLEScan;
    bool isFacultyPresent;
    bool bleScanActive;
    unsigned long lastBeaconSignalTime;
    const char* targetMacAddress;
    int rssiThreshold;
    bool manualOverrideActive;
    bool manualOverrideStatus;
    
    // BLE device callback class
    class AdvertisedDeviceCallbacks : public NimBLEAdvertisedDeviceCallbacks {
    private:
        BLEManager* manager;
        
    public:
        AdvertisedDeviceCallbacks(BLEManager* mgr) : manager(mgr) {}
        
        void onResult(NimBLEAdvertisedDevice* advertisedDevice) {
            // Only process if manual override is not active
            if (manager->isManualOverrideActive()) {
                return;
            }
            
            // Debug log
            if (DEBUG_ENABLED) {
                Serial.print("BLE Device found: ");
                Serial.print(advertisedDevice->toString().c_str());
                Serial.print(", Address: ");
                Serial.println(advertisedDevice->getAddress().toString().c_str());
            }
            
            // Get the MAC address of the advertised device
            NimBLEAddress advertisedAddress = advertisedDevice->getAddress();
            
            // Create a NimBLEAddress object from the target MAC address
            NimBLEAddress targetAddress(manager->getTargetMacAddress());
            
            // Compare the advertised address with the target address
            if (advertisedAddress.equals(targetAddress)) {
                Serial.println("Found target faculty BLE device by MAC address!");
                
                // Optional: Check RSSI if threshold is enabled
                if (manager->getRssiThreshold() != 0) {
                    int rssi = advertisedDevice->getRSSI();
                    if (rssi < manager->getRssiThreshold()) {
                        Serial.printf("Device RSSI %d is below threshold %d. Ignoring.\n", 
                                      rssi, manager->getRssiThreshold());
                        return;
                    }
                    
                    Serial.printf("RSSI: %d (above threshold: %d)\n", 
                                 rssi, manager->getRssiThreshold());
                }
                
                // Update faculty presence state
                manager->setFacultyPresent(true);
                
                // Stop scanning to save power, will restart on next interval
                if (manager->pBLEScan->isScanning()) {
                    manager->pBLEScan->stop();
                    manager->setBleScanActive(false);
                }
            }
        }
    };
    
    // BLE advertisement callback instance
    AdvertisedDeviceCallbacks* deviceCallbacks;

public:
    /**
     * Constructor
     */
    BLEManager() :
        pBLEScan(nullptr),
        isFacultyPresent(false),
        bleScanActive(false),
        lastBeaconSignalTime(0),
        targetMacAddress(TARGET_BLE_MAC_ADDRESS),
        rssiThreshold(BLE_RSSI_THRESHOLD),
        manualOverrideActive(false),
        manualOverrideStatus(false),
        deviceCallbacks(nullptr)
    {
    }
    
    /**
     * Destructor
     */
    ~BLEManager() {
        if (deviceCallbacks != nullptr) {
            delete deviceCallbacks;
        }
    }
    
    /**
     * Initialize BLE functionality
     * @return true if successful, false otherwise
     */
    bool initialize() {
        Serial.println("Initializing BLE Manager...");
        
        // Initialize BLE device
        NimBLEDevice::init("");
        
        // Get scan object
        pBLEScan = NimBLEDevice::getScan();
        if (pBLEScan == nullptr) {
            Serial.println("ERROR: Failed to get BLE scan object");
            return false;
        }
        
        // Create and set callbacks
        deviceCallbacks = new AdvertisedDeviceCallbacks(this);
        pBLEScan->setAdvertisedDeviceCallbacks(deviceCallbacks);
        
        // Configure scan parameters
        pBLEScan->setActiveScan(BLE_ACTIVE_SCAN);
        pBLEScan->setInterval(BLE_SCAN_INTERVAL);
        pBLEScan->setWindow(BLE_SCAN_WINDOW);
        
        Serial.println("BLE Manager initialized successfully");
        Serial.print("Target MAC Address: ");
        Serial.println(targetMacAddress);
        Serial.print("RSSI Threshold: ");
        Serial.println(rssiThreshold);
        
        return true;
    }
    
    /**
     * Start a BLE scan to detect faculty presence
     * @return true if scan started, false otherwise
     */
    bool startScan() {
        // Don't scan if manual override is active
        if (manualOverrideActive) {
            return false;
        }
        
        // Don't start a new scan if one is already in progress
        if (bleScanActive || pBLEScan->isScanning()) {
            return false;
        }
        
        Serial.println("Starting BLE scan...");
        
        // Clear results from previous scan to prevent memory leaks
        if (pBLEScan->getResults().getCount() > 0) {
            Serial.println("Clearing previous scan results to prevent memory leaks");
            pBLEScan->clearResults();
        }
        
        // Start scan with specified duration, no callback on completion, not continuous
        bool result = pBLEScan->start(BLE_SCAN_DURATION, nullptr, false);
        bleScanActive = result;
        
        if (result) {
            Serial.println("BLE scan started successfully");
        } else {
            Serial.println("ERROR: Failed to start BLE scan");
        }
        
        return result;
    }
    
    /**
     * Stop the current BLE scan
     */
    void stopScan() {
        if (pBLEScan->isScanning()) {
            pBLEScan->stop();
            bleScanActive = false;
            Serial.println("BLE scan stopped");
        }
    }
    
    /**
     * Check if a faculty timeout has occurred
     * @param currentTime The current time in milliseconds
     * @return true if timeout occurred, false otherwise
     */
    bool checkFacultyTimeout(unsigned long currentTime) {
        // Skip timeout check if manual override is active
        if (manualOverrideActive) {
            return false;
        }
        
        // Check if faculty was present but now timed out
        if (isFacultyPresent && (currentTime - lastBeaconSignalTime > BLE_CONNECTION_TIMEOUT)) {
            Serial.println("BLE beacon signal lost (timeout)");
            isFacultyPresent = false;
            return true;
        }
        
        return false;
    }
    
    /**
     * Set the faculty presence state
     * @param present Whether the faculty is present
     */
    void setFacultyPresent(bool present) {
        // Only update if changed
        if (isFacultyPresent != present) {
            isFacultyPresent = present;
            Serial.print("Faculty presence changed to: ");
            Serial.println(present ? "PRESENT" : "ABSENT");
        }
        
        // Always update the last beacon time
        if (present) {
            lastBeaconSignalTime = millis();
        }
    }
    
    /**
     * Enable or disable manual override
     * @param active Whether manual override is active
     * @param status The manual status to use (if active)
     */
    void setManualOverride(bool active, bool status) {
        manualOverrideActive = active;
        manualOverrideStatus = status;
        
        Serial.print("Manual override ");
        if (active) {
            Serial.print("ACTIVATED. Status: ");
            Serial.println(status ? "AVAILABLE" : "UNAVAILABLE");
        } else {
            Serial.println("DEACTIVATED");
        }
    }
    
    /**
     * Set the BLE scan active state
     * @param active Whether BLE scan is active
     */
    void setBleScanActive(bool active) {
        bleScanActive = active;
    }
    
    /**
     * Get the faculty presence state
     * @return Whether the faculty is present (based on BLE or manual override)
     */
    bool getFacultyPresence() {
        // Manual override takes precedence if active
        if (manualOverrideActive) {
            return manualOverrideStatus;
        }
        
        return isFacultyPresent;
    }
    
    /**
     * Check if manual override is active
     * @return Whether manual override is active
     */
    bool isManualOverrideActive() const {
        return manualOverrideActive;
    }
    
    /**
     * Get the manual override status
     * @return The manual override status
     */
    bool getManualOverrideStatus() const {
        return manualOverrideStatus;
    }
    
    /**
     * Get the target MAC address
     * @return The target MAC address
     */
    const char* getTargetMacAddress() const {
        return targetMacAddress;
    }
    
    /**
     * Get the RSSI threshold
     * @return The RSSI threshold
     */
    int getRssiThreshold() const {
        return rssiThreshold;
    }
    
    /**
     * Check if BLE scan is active
     * @return Whether BLE scan is active
     */
    bool isBleScanActive() const {
        return bleScanActive;
    }
    
    /**
     * Get the last beacon signal time
     * @return The last beacon signal time in milliseconds
     */
    unsigned long getLastBeaconSignalTime() const {
        return lastBeaconSignalTime;
    }
};

#endif // BLE_MANAGER_H 