/**
 * ConsultEase - Test Runner
 * 
 * This file is the main entry point for running all tests.
 */

#include "framework/test_includes.h"

// Import test functions
extern void runDisplayManagerTests();
extern void runNetworkManagerTests();
// TODO: Add more test functions as they are implemented

// Main setup function
void setup() {
    Serial.begin(115200);
    delay(2000);  // Allow time to open the Serial Monitor
    
    Serial.println("\n\n");
    Serial.println("************************************");
    Serial.println("*   ConsultEase Unit Test Runner   *");
    Serial.println("************************************");
    Serial.println("\n");
    
    // Initialize the test environment
    TestUtils::initTestMode();
    
    // Run all tests
    runDisplayManagerTests();
    runNetworkManagerTests();
    // TODO: Add more test functions as they are implemented
    
    // Print final summary
    Serial.println("\n\n");
    Serial.println("************************************");
    Serial.println("*       All Tests Completed        *");
    Serial.println("************************************");
    
    // Clean up
    TestUtils::cleanupTestMode();
}

// Main loop function
void loop() {
    // Nothing to do here
    delay(1000);
} 