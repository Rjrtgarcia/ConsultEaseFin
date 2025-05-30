/**
 * ConsultEase - Simulation Mode
 * 
 * This file provides functionality for running the Faculty Desk Unit in
 * simulation mode without requiring actual hardware.
 */

#ifndef SIMULATION_MODE_H
#define SIMULATION_MODE_H

#include "../framework/test_includes.h"

// Define simulation mode flag
#define SIMULATION_MODE

// Simulation state
class SimulationState {
public:
    // Singleton instance
    static SimulationState& instance() {
        static SimulationState instance;
        return instance;
    }
    
    // Display manager instance
    DisplayManager* displayManager;
    
    // Network manager instance
    NetworkManager* networkManager;
    
    // BLE manager instance
    BLEManager* bleManager;
    
    // Consultation manager instance
    ConsultationManager* consultationManager;
    
    // Button manager instance
    ButtonManager* buttonManager;
    
    // Power manager instance
    PowerManager* powerManager;
    
    // Mock objects
    MockDisplay* tft;
    MockWiFiClient* wifiClient;
    MockPubSubClient* mqttClient;
    
    // Simulation controls
    bool simulationRunning;
    unsigned long simulationStartTime;
    unsigned long simulationCurrentTime;
    
    // Simulation scenario
    enum SimulationScenario {
        NORMAL_OPERATION,
        WIFI_DISCONNECTION,
        BLE_PRESENCE_CHANGE,
        CONSULTATION_REQUEST,
        POWER_SAVING_MODE
    };
    
    SimulationScenario currentScenario;
    
    // Initialize simulation
    void init() {
        // Create mock objects
        tft = new MockDisplay();
        wifiClient = new MockWiFiClient();
        mqttClient = new MockPubSubClient(*wifiClient);
        
        // Initialize mock WiFi
        WiFiClass_Mock WiFi;
        WiFi.setStatus(WL_CONNECTED);
        
        // Create manager instances
        displayManager = new DisplayManager(tft);
        networkManager = new NetworkManager(displayManager);
        bleManager = new BLEManager(displayManager, networkManager);
        consultationManager = new ConsultationManager(displayManager, networkManager);
        buttonManager = new ButtonManager(bleManager, consultationManager);
        powerManager = new PowerManager(networkManager, bleManager);
        
        // Initialize components
        displayManager->init();
        displayManager->drawHeader();
        displayManager->drawStatusArea();
        
        // Set initial simulation state
        simulationRunning = true;
        simulationStartTime = millis();
        simulationCurrentTime = simulationStartTime;
        
        // Set initial scenario
        currentScenario = NORMAL_OPERATION;
        
        Serial.println("Simulation mode initialized");
    }
    
    // Clean up simulation
    void cleanup() {
        // Delete manager instances
        delete powerManager;
        delete buttonManager;
        delete consultationManager;
        delete bleManager;
        delete networkManager;
        delete displayManager;
        
        // Delete mock objects
        delete mqttClient;
        delete wifiClient;
        delete tft;
        
        simulationRunning = false;
        
        Serial.println("Simulation mode cleanup complete");
    }
    
    // Run simulation step
    void step() {
        if (!simulationRunning) {
            return;
        }
        
        // Update simulation time
        simulationCurrentTime = millis();
        unsigned long elapsedTime = simulationCurrentTime - simulationStartTime;
        
        // Update managers
        displayManager->updateTimeDisplay();
        networkManager->processMessages();
        bleManager->checkPresence();
        consultationManager->processRequests();
        buttonManager->checkButtons();
        powerManager->updatePowerMode();
        
        // Handle scenarios based on elapsed time
        handleScenarios(elapsedTime);
    }
    
    // Handle different simulation scenarios
    void handleScenarios(unsigned long elapsedTime) {
        // Change scenarios based on elapsed time
        if (elapsedTime > 60000 && currentScenario == NORMAL_OPERATION) {
            // After 1 minute, simulate WiFi disconnection
            currentScenario = WIFI_DISCONNECTION;
            simulateWiFiDisconnection();
        } else if (elapsedTime > 120000 && currentScenario == WIFI_DISCONNECTION) {
            // After 2 minutes, simulate WiFi reconnection and BLE presence change
            currentScenario = BLE_PRESENCE_CHANGE;
            simulateWiFiReconnection();
            simulateBLEPresenceChange();
        } else if (elapsedTime > 180000 && currentScenario == BLE_PRESENCE_CHANGE) {
            // After 3 minutes, simulate consultation request
            currentScenario = CONSULTATION_REQUEST;
            simulateConsultationRequest();
        } else if (elapsedTime > 240000 && currentScenario == CONSULTATION_REQUEST) {
            // After 4 minutes, simulate power saving mode
            currentScenario = POWER_SAVING_MODE;
            simulatePowerSavingMode();
        } else if (elapsedTime > 300000 && currentScenario == POWER_SAVING_MODE) {
            // After 5 minutes, reset to normal operation
            currentScenario = NORMAL_OPERATION;
            simulateNormalOperation();
            simulationStartTime = millis(); // Reset the timer
        }
    }
    
    // Simulation scenarios
    void simulateWiFiDisconnection() {
        Serial.println("Simulating WiFi disconnection...");
        
        // Set WiFi status to disconnected
        WiFiClass_Mock WiFi;
        WiFi.setStatus(WL_DISCONNECTED);
        
        // Update network manager
        networkManager->onWiFiDisconnected();
    }
    
    void simulateWiFiReconnection() {
        Serial.println("Simulating WiFi reconnection...");
        
        // Set WiFi status to connected
        WiFiClass_Mock WiFi;
        WiFi.setStatus(WL_CONNECTED);
        
        // Update network manager
        networkManager->connectWiFi();
        networkManager->connectMQTT();
    }
    
    void simulateBLEPresenceChange() {
        Serial.println("Simulating BLE presence change...");
        
        // Create a mock BLE device with faculty MAC address
        MockBLEAdvertisedDevice device;
        device.setAddress(MockBLEAddress(FACULTY_BEACON_MAC));
        device.setName("Faculty Phone");
        device.setRSSI(-65);  // Good signal strength
        
        // Simulate device found
        bleManager->onDeviceFound(&device);
    }
    
    void simulateConsultationRequest() {
        Serial.println("Simulating consultation request...");
        
        // Create a consultation request JSON
        String json = TestUtils::createSampleConsultationRequest(
            123,
            "John Doe",
            "I need help with my project",
            "pending"
        );
        
        // Convert to char array for the callback
        char topic[50] = "consultease/faculty/F12345/request";
        char* payload = new char[json.length() + 1];
        strcpy(payload, json.c_str());
        
        // Simulate MQTT message received
        networkManager->onMQTTMessage(topic, (uint8_t*)payload, json.length());
        
        // Clean up
        delete[] payload;
    }
    
    void simulatePowerSavingMode() {
        Serial.println("Simulating power saving mode...");
        
        // Set power mode to low power
        powerManager->setPowerMode(POWER_MODE_LOW_POWER);
    }
    
    void simulateNormalOperation() {
        Serial.println("Simulating normal operation...");
        
        // Reset all components to normal state
        WiFiClass_Mock WiFi;
        WiFi.setStatus(WL_CONNECTED);
        
        networkManager->connectWiFi();
        networkManager->connectMQTT();
        
        powerManager->setPowerMode(POWER_MODE_NORMAL);
        
        bleManager->setManualOverride(false);
    }
    
    // Set a specific scenario
    void setScenario(SimulationScenario scenario) {
        currentScenario = scenario;
        
        switch (scenario) {
            case NORMAL_OPERATION:
                simulateNormalOperation();
                break;
            case WIFI_DISCONNECTION:
                simulateWiFiDisconnection();
                break;
            case BLE_PRESENCE_CHANGE:
                simulateBLEPresenceChange();
                break;
            case CONSULTATION_REQUEST:
                simulateConsultationRequest();
                break;
            case POWER_SAVING_MODE:
                simulatePowerSavingMode();
                break;
        }
    }
    
private:
    // Private constructor for singleton
    SimulationState() : 
        displayManager(nullptr),
        networkManager(nullptr),
        bleManager(nullptr),
        consultationManager(nullptr),
        buttonManager(nullptr),
        powerManager(nullptr),
        tft(nullptr),
        wifiClient(nullptr),
        mqttClient(nullptr),
        simulationRunning(false),
        simulationStartTime(0),
        simulationCurrentTime(0),
        currentScenario(NORMAL_OPERATION) {
    }
    
    // Prevent copies
    SimulationState(const SimulationState&) = delete;
    SimulationState& operator=(const SimulationState&) = delete;
};

#endif // SIMULATION_MODE_H 