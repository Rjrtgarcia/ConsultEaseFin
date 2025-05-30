/**
 * ConsultEase - Test Includes
 * 
 * This file includes all the necessary test framework and mock headers,
 * and provides utilities for test setup and teardown.
 */

#ifndef TEST_INCLUDES_H
#define TEST_INCLUDES_H

// Include Arduino framework for ESP32
#include <Arduino.h>

// Include ESP32-specific libraries
#include <esp_task_wdt.h>
#include <esp_pm.h>
#include <esp_heap_caps.h>

// Include standard libraries
#include <string>
#include <vector>
#include <functional>
#include <map>

// Include test framework
#include "test_framework.h"

// Include mocks
#include "../mocks/display_mock.h"
#include "../mocks/wifi_mock.h"
#include "../mocks/mqtt_mock.h"
#include "../mocks/ble_mock.h"

// Include actual headers being tested
#include "../../config.h"
#include "../../faculty_constants.h"
#include "../../display_manager.h"
#include "../../network_manager.h"
#include "../../ble_manager.h"
#include "../../consultation_manager.h"
#include "../../button_manager.h"
#include "../../power_manager.h"

// Utilities for test setup and teardown
namespace TestUtils {
    // Global flag to indicate test mode is active
    extern bool testModeActive;
    
    // Initialize testing mode
    void initTestMode() {
        testModeActive = true;
        Serial.println("Test mode initialized");
        
        // Clear any existing mock logs
        MockBLEDevice::clearMethodCallLog();
    }
    
    // Cleanup after tests
    void cleanupTestMode() {
        testModeActive = false;
        Serial.println("Test mode cleanup complete");
    }
    
    // Simulate delay without actually delaying
    void simulateDelay(unsigned long ms) {
        // Do nothing - just simulate the passage of time
        Serial.print("Simulating delay of ");
        Serial.print(ms);
        Serial.println(" ms");
    }
    
    // Simulate millis() value progression
    unsigned long mockMillis() {
        static unsigned long current_millis = 0;
        current_millis += 100; // Simulate 100ms passing each call
        return current_millis;
    }
    
    // Reset millis counter
    void resetMillis() {
        // Reset the mock millis() counter
    }
    
    // Create a sample consultation request JSON
    String createSampleConsultationRequest(
        int id = 123,
        const char* studentName = "John Doe",
        const char* message = "I need help with my project",
        const char* status = "pending"
    ) {
        String json = "{";
        json += "\"id\":" + String(id) + ",";
        json += "\"student_name\":\"" + String(studentName) + "\",";
        json += "\"message\":\"" + String(message) + "\",";
        json += "\"status\":\"" + String(status) + "\"";
        json += "}";
        return json;
    }
    
    // Create a sample faculty status JSON
    String createSampleFacultyStatus(
        bool isAvailable = true,
        const char* status = "available",
        int consultationCount = 0
    ) {
        String json = "{";
        json += "\"available\":" + String(isAvailable ? "true" : "false") + ",";
        json += "\"status\":\"" + String(status) + "\",";
        json += "\"consultation_count\":" + String(consultationCount);
        json += "}";
        return json;
    }
    
    // Setup standard test environment
    void setupStandardTestEnvironment() {
        initTestMode();
        
        // Initialize mock WiFi
        WiFiClass_Mock WiFi_Mock;
        WiFi_Mock.setStatus(WL_CONNECTED);
        
        // Set mock time
        resetMillis();
    }
}

// Initialize the test mode flag
bool TestUtils::testModeActive = false;

#endif // TEST_INCLUDES_H 