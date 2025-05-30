/**
 * ConsultEase - Power Manager
 * 
 * This module handles power-related functionality for the Faculty Desk Unit,
 * including CPU frequency management, sleep modes, and power optimization.
 */

#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <Arduino.h>
#include <esp_pm.h>
#include <esp_wifi.h>
#include "config.h"

// Power modes
enum PowerMode {
    POWER_MODE_NORMAL,       // Normal operation, full power
    POWER_MODE_BALANCED,     // Balanced power savings, WiFi active
    POWER_MODE_LOW_POWER,    // Low power mode, reduced WiFi power
    POWER_MODE_ULTRA_LOW     // Ultra low power, WiFi periodic scan
};

class PowerManager {
private:
    PowerMode currentMode;
    bool wifiPowerSavingEnabled;
    bool autoFrequencyEnabled;
    
    // CPU frequency settings
    int normalFrequencyMHz;
    int balancedFrequencyMHz;
    int lowPowerFrequencyMHz;
    
    // Power saving intervals
    unsigned long lastActivityTime;
    unsigned long inactivityTimeout;
    bool inactivityTimeoutEnabled;
    
    // Performance configuration
    esp_pm_config_esp32_t pmConfig;

public:
    /**
     * Constructor
     */
    PowerManager() :
        currentMode(POWER_MODE_NORMAL),
        wifiPowerSavingEnabled(false),
        autoFrequencyEnabled(false),
        normalFrequencyMHz(240),        // Normal frequency
        balancedFrequencyMHz(160),      // Balanced frequency
        lowPowerFrequencyMHz(80),       // Low power frequency
        lastActivityTime(0),
        inactivityTimeout(300000),      // 5 minutes
        inactivityTimeoutEnabled(false)
    {
        // Initialize performance configuration
        pmConfig.max_freq_mhz = normalFrequencyMHz;
        pmConfig.min_freq_mhz = lowPowerFrequencyMHz;
        pmConfig.light_sleep_enable = false;  // No light sleep by default
    }
    
    /**
     * Initialize the power manager
     * @return true if successful, false otherwise
     */
    bool initialize() {
        Serial.println("Initializing Power Manager...");
        
        // Set initial CPU frequency
        setCpuFrequencyMHz(normalFrequencyMHz);
        Serial.printf("Initial CPU frequency set to %d MHz\n", normalFrequencyMHz);
        
        // Set initial WiFi power mode
        if (WIFI_POWER_SAVE_ENABLED) {
            enableWiFiPowerSaving(true);
        }
        
        // Enable automatic frequency scaling if configured
        if (AUTO_FREQUENCY_ENABLED) {
            enableAutoFrequency(true);
        }
        
        // Enable inactivity timeout if configured
        if (INACTIVITY_TIMEOUT_ENABLED) {
            enableInactivityTimeout(true);
        }
        
        // Record initial activity time
        recordActivity();
        
        return true;
    }
    
    /**
     * Set the CPU frequency in MHz
     * @param frequencyMHz The target frequency in MHz
     * @return true if successful, false otherwise
     */
    bool setCpuFrequencyMHz(int frequencyMHz) {
        if (frequencyMHz != 80 && frequencyMHz != 160 && frequencyMHz != 240) {
            Serial.printf("Invalid CPU frequency: %d MHz\n", frequencyMHz);
            return false;
        }
        
        Serial.printf("Setting CPU frequency to %d MHz\n", frequencyMHz);
        return setCpuFrequencyMHz(frequencyMHz);
    }
    
    /**
     * Enable or disable WiFi power saving
     * @param enable Whether to enable power saving
     */
    void enableWiFiPowerSaving(bool enable) {
        wifiPowerSavingEnabled = enable;
        
        if (enable) {
            esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
            Serial.println("WiFi power saving enabled (MODEM_SLEEP_T)");
        } else {
            esp_wifi_set_ps(WIFI_PS_NONE);
            Serial.println("WiFi power saving disabled");
        }
    }
    
    /**
     * Enable or disable automatic CPU frequency scaling
     * @param enable Whether to enable auto frequency
     * @return true if successful, false otherwise
     */
    bool enableAutoFrequency(bool enable) {
        autoFrequencyEnabled = enable;
        
        if (enable) {
            // Configure automatic frequency scaling
            esp_err_t err = esp_pm_configure(&pmConfig);
            
            if (err != ESP_OK) {
                Serial.printf("Failed to configure automatic frequency scaling: %d\n", err);
                autoFrequencyEnabled = false;
                return false;
            }
            
            Serial.printf("Automatic frequency scaling enabled (%d-%d MHz)\n", 
                         pmConfig.min_freq_mhz, pmConfig.max_freq_mhz);
        } else {
            // Disable automatic frequency scaling by setting fixed frequency
            setCpuFrequencyMHz(normalFrequencyMHz);
            Serial.println("Automatic frequency scaling disabled");
        }
        
        return true;
    }
    
    /**
     * Enable or disable inactivity timeout
     * @param enable Whether to enable inactivity timeout
     * @param timeout The timeout in milliseconds (default: 5 minutes)
     */
    void enableInactivityTimeout(bool enable, unsigned long timeout = 300000) {
        inactivityTimeoutEnabled = enable;
        
        if (enable) {
            inactivityTimeout = timeout;
            Serial.printf("Inactivity timeout enabled (%lu ms)\n", timeout);
        } else {
            Serial.println("Inactivity timeout disabled");
        }
    }
    
    /**
     * Record user activity (resets inactivity timer)
     */
    void recordActivity() {
        lastActivityTime = millis();
    }
    
    /**
     * Set the power mode
     * @param mode The target power mode
     */
    void setPowerMode(PowerMode mode) {
        if (currentMode == mode) {
            return;
        }
        
        currentMode = mode;
        
        switch (mode) {
            case POWER_MODE_NORMAL:
                setCpuFrequencyMHz(normalFrequencyMHz);
                enableWiFiPowerSaving(false);
                Serial.println("Power mode set to NORMAL");
                break;
                
            case POWER_MODE_BALANCED:
                setCpuFrequencyMHz(balancedFrequencyMHz);
                enableWiFiPowerSaving(true);
                Serial.println("Power mode set to BALANCED");
                break;
                
            case POWER_MODE_LOW_POWER:
                setCpuFrequencyMHz(lowPowerFrequencyMHz);
                enableWiFiPowerSaving(true);
                Serial.println("Power mode set to LOW_POWER");
                break;
                
            case POWER_MODE_ULTRA_LOW:
                setCpuFrequencyMHz(lowPowerFrequencyMHz);
                enableWiFiPowerSaving(true);
                // Additional power saving measures could be added here
                Serial.println("Power mode set to ULTRA_LOW");
                break;
        }
    }
    
    /**
     * Update power management (should be called in each loop iteration)
     */
    void update() {
        // Check inactivity timeout
        if (inactivityTimeoutEnabled) {
            unsigned long currentTime = millis();
            unsigned long inactiveTime = currentTime - lastActivityTime;
            
            if (inactiveTime > inactivityTimeout) {
                // Switch to low power mode after inactivity
                if (currentMode == POWER_MODE_NORMAL) {
                    setPowerMode(POWER_MODE_BALANCED);
                } else if (currentMode == POWER_MODE_BALANCED && inactiveTime > inactivityTimeout * 2) {
                    setPowerMode(POWER_MODE_LOW_POWER);
                }
            }
        }
    }
    
    /**
     * Enter deep sleep mode (ESP32 will restart on wake)
     * @param sleepTimeMs Time to sleep in milliseconds (0 for indefinite)
     */
    void enterDeepSleep(uint64_t sleepTimeMs = 0) {
        Serial.printf("Entering deep sleep for %llu ms\n", sleepTimeMs);
        
        // Perform any necessary cleanup here
        
        // Configure wake sources if needed
        
        // Enter deep sleep
        esp_sleep_enable_timer_wakeup(sleepTimeMs * 1000); // Convert to microseconds
        esp_deep_sleep_start();
    }
    
    /**
     * Get the current power mode
     * @return The current power mode
     */
    PowerMode getCurrentMode() const {
        return currentMode;
    }
    
    /**
     * Get the current CPU frequency
     * @return The current CPU frequency in MHz
     */
    int getCurrentCpuFrequency() const {
        return getCpuFrequencyMHz();
    }
    
    /**
     * Check if WiFi power saving is enabled
     * @return true if enabled, false otherwise
     */
    bool isWiFiPowerSavingEnabled() const {
        return wifiPowerSavingEnabled;
    }
    
    /**
     * Check if automatic frequency scaling is enabled
     * @return true if enabled, false otherwise
     */
    bool isAutoFrequencyEnabled() const {
        return autoFrequencyEnabled;
    }
};

#endif // POWER_MANAGER_H 