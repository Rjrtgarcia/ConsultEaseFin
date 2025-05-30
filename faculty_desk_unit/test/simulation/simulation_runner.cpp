/**
 * ConsultEase - Simulation Runner
 * 
 * This file provides an entry point for running the Faculty Desk Unit in
 * simulation mode without requiring actual hardware.
 */

#include "simulation_mode.h"

// Main setup function
void setup() {
    Serial.begin(115200);
    delay(2000);  // Allow time to open the Serial Monitor
    
    Serial.println("\n\n");
    Serial.println("************************************");
    Serial.println("* ConsultEase Simulation Mode *");
    Serial.println("************************************");
    Serial.println("\n");
    
    // Initialize the simulation
    SimulationState::instance().init();
    
    // Print simulation instructions
    Serial.println("Simulation started. The following scenarios will be simulated:");
    Serial.println("1. Normal operation (initial state)");
    Serial.println("2. WiFi disconnection (after 1 minute)");
    Serial.println("3. WiFi reconnection and BLE presence change (after 2 minutes)");
    Serial.println("4. Consultation request (after 3 minutes)");
    Serial.println("5. Power saving mode (after 4 minutes)");
    Serial.println("6. Return to normal operation (after 5 minutes)");
    Serial.println("\nYou can also manually trigger scenarios by sending commands:");
    Serial.println("1: Normal operation");
    Serial.println("2: WiFi disconnection");
    Serial.println("3: BLE presence change");
    Serial.println("4: Consultation request");
    Serial.println("5: Power saving mode");
    Serial.println("q: Quit simulation");
    Serial.println("\n");
}

// Main loop function
void loop() {
    // Check for serial input to manually trigger scenarios
    if (Serial.available() > 0) {
        char input = Serial.read();
        
        switch (input) {
            case '1':
                Serial.println("Manual trigger: Normal operation");
                SimulationState::instance().setScenario(SimulationState::NORMAL_OPERATION);
                break;
            case '2':
                Serial.println("Manual trigger: WiFi disconnection");
                SimulationState::instance().setScenario(SimulationState::WIFI_DISCONNECTION);
                break;
            case '3':
                Serial.println("Manual trigger: BLE presence change");
                SimulationState::instance().setScenario(SimulationState::BLE_PRESENCE_CHANGE);
                break;
            case '4':
                Serial.println("Manual trigger: Consultation request");
                SimulationState::instance().setScenario(SimulationState::CONSULTATION_REQUEST);
                break;
            case '5':
                Serial.println("Manual trigger: Power saving mode");
                SimulationState::instance().setScenario(SimulationState::POWER_SAVING_MODE);
                break;
            case 'q':
            case 'Q':
                Serial.println("Quitting simulation...");
                SimulationState::instance().cleanup();
                Serial.println("Simulation ended.");
                while (true) {
                    // Infinite loop to stop execution
                    delay(1000);
                }
                break;
        }
        
        // Clear any remaining input
        while (Serial.available() > 0) {
            Serial.read();
        }
    }
    
    // Run simulation step
    SimulationState::instance().step();
    
    // Print simulation stats every second
    static unsigned long lastStatTime = 0;
    if (millis() - lastStatTime > 1000) {
        lastStatTime = millis();
        
        // Print current scenario
        String scenarioName;
        switch (SimulationState::instance().currentScenario) {
            case SimulationState::NORMAL_OPERATION:
                scenarioName = "Normal operation";
                break;
            case SimulationState::WIFI_DISCONNECTION:
                scenarioName = "WiFi disconnection";
                break;
            case SimulationState::BLE_PRESENCE_CHANGE:
                scenarioName = "BLE presence change";
                break;
            case SimulationState::CONSULTATION_REQUEST:
                scenarioName = "Consultation request";
                break;
            case SimulationState::POWER_SAVING_MODE:
                scenarioName = "Power saving mode";
                break;
        }
        
        // Calculate elapsed time
        unsigned long elapsedTime = SimulationState::instance().simulationCurrentTime - 
                                   SimulationState::instance().simulationStartTime;
        unsigned long elapsedSeconds = elapsedTime / 1000;
        unsigned long elapsedMinutes = elapsedSeconds / 60;
        elapsedSeconds %= 60;
        
        // Print stats
        Serial.print("Simulation time: ");
        Serial.print(elapsedMinutes);
        Serial.print("m ");
        Serial.print(elapsedSeconds);
        Serial.print("s | Current scenario: ");
        Serial.println(scenarioName);
        
        // Print mock display content summary
        SimulationState::instance().tft->printDisplaySummary();
    }
    
    // Slow down the simulation
    delay(100);
} 