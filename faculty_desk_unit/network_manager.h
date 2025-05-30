/**
 * ConsultEase - Network Manager
 * 
 * This module handles WiFi and MQTT connections for the Faculty Desk Unit,
 * including connection management, error handling, and message publishing.
 */

#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <WiFi.h>
#ifdef MQTT_USE_TLS
#include <WiFiClientSecure.h>
#endif
#include <PubSubClient.h>
#include "config.h"
#include "display_manager.h"

// Network-related constants
#define WIFI_CONNECT_TIMEOUT 30000  // 30 seconds timeout for WiFi connection
#define WIFI_MAX_RETRIES 5          // Maximum number of WiFi connection retries
#define MQTT_CONNECT_TIMEOUT 10000  // 10 seconds timeout for MQTT connection
#define MQTT_MAX_RETRIES 3          // Maximum number of MQTT connection retries before WiFi reset

class NetworkManager {
private:
    // WiFi variables
    const char* ssid;
    const char* password;
    bool wifiConnected;
    int wifiRetryCount;
    unsigned long lastWifiRetryTime;
    
    // MQTT variables
    const char* mqttServer;
    int mqttPort;
    const char* mqttUsername;
    const char* mqttPassword;
    const char* mqttClientId;
    bool mqttConnected;
    int mqttRetryCount;
    unsigned long lastMqttRetryTime;
    
    // Topics
    char topicStatus[100];
    char topicRequests[100];
    char topicResponse[100];
    
    // Network clients
#ifdef MQTT_USE_TLS
    WiFiClientSecure* espClient;
#else
    WiFiClient* espClient;
#endif
    PubSubClient* mqttClient;
    
    // Display manager reference
    DisplayManager* display;
    
    // Callback function type for MQTT messages
    typedef void (*MessageCallback)(char* topic, byte* payload, unsigned int length);
    MessageCallback messageCallback;

public:
    /**
     * Constructor
     */
    NetworkManager(
#ifdef MQTT_USE_TLS
        WiFiClientSecure* secureClient,
#else
        WiFiClient* client,
#endif
        PubSubClient* mqtt,
        DisplayManager* disp
    ) : 
        ssid(WIFI_SSID),
        password(WIFI_PASSWORD),
        mqttServer(MQTT_BROKER),
        mqttPort(MQTT_USE_TLS ? MQTT_TLS_PORT : MQTT_PORT),
        mqttUsername(MQTT_USERNAME),
        mqttPassword(MQTT_PASSWORD),
        mqttClientId(MQTT_CLIENT_ID),
        wifiConnected(false),
        wifiRetryCount(0),
        mqttConnected(false),
        mqttRetryCount(0),
        lastWifiRetryTime(0),
        lastMqttRetryTime(0),
#ifdef MQTT_USE_TLS
        espClient(secureClient),
#else
        espClient(client),
#endif
        mqttClient(mqtt),
        display(disp),
        messageCallback(NULL)
    {
        // Initialize topic strings
        snprintf(topicStatus, sizeof(topicStatus), FACULTY_STATUS_TOPIC(FACULTY_ID));
        snprintf(topicRequests, sizeof(topicRequests), FACULTY_REQUEST_TOPIC(FACULTY_ID));
        snprintf(topicResponse, sizeof(topicResponse), FACULTY_RESPONSE_TOPIC(FACULTY_ID));
    }
    
    /**
     * Set the callback function for MQTT messages
     * @param callback The function to call when an MQTT message is received
     */
    void setMessageCallback(MessageCallback callback) {
        messageCallback = callback;
        if (mqttClient != NULL) {
            mqttClient->setCallback(callback);
        }
    }
    
    /**
     * Initialize the network connections
     * @return true if successful, false otherwise
     */
    bool initialize() {
        // Configure MQTT client
        mqttClient->setServer(mqttServer, mqttPort);
        
        if (messageCallback != NULL) {
            mqttClient->setCallback(messageCallback);
        }
        
        // Connect to WiFi
        bool wifiResult = connectToWiFi();
        if (!wifiResult) {
            return false;
        }
        
        // Configure time
        configTime(0, 0, "pool.ntp.org");
        
        // Connect to MQTT
        return connectToMQTT();
    }
    
    /**
     * Connect to WiFi network
     * @return true if connected successfully, false otherwise
     */
    bool connectToWiFi() {
        display->updateUIArea(0);
        display->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        display->setTextColor(COLOR_TEXT);
        display->setTextSize(2);
        display->println("Connecting to WiFi");
        display->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 40);
        display->setTextSize(1);
        display->println(ssid);
        
        // Start WiFi connection
        Serial.print("Connecting to WiFi: ");
        Serial.println(ssid);
        
        WiFi.mode(WIFI_STA);  // Set station mode
        WiFi.begin(ssid, password);
        
        // Track connection start time for timeout
        unsigned long startTime = millis();
        int dots = 0;
        bool timeout = false;
        
        // Wait for connection or timeout
        while (WiFi.status() != WL_CONNECTED && !timeout) {
            // Check for timeout
            if (millis() - startTime > WIFI_CONNECT_TIMEOUT) {
                timeout = true;
                break;
            }
            
            delay(500);
            Serial.print(".");
            
            // Update display with connection animation
            display->showWiFiConnecting(ssid, "Connecting to WiFi...", dots);
            dots = (dots + 1) % 7;
            
            // Reset watchdog to prevent timeout
            esp_task_wdt_reset();
        }
        
        // Check connection result
        if (WiFi.status() == WL_CONNECTED) {
            wifiConnected = true;
            wifiRetryCount = 0;
            
            Serial.println("");
            Serial.println("WiFi connected successfully");
            Serial.print("IP address: ");
            Serial.println(WiFi.localIP());
            
            // Update display with success info
            display->showWiFiConnected(ssid, WiFi.localIP().toString().c_str());
            
            return true;
        } else {
            wifiConnected = false;
            wifiRetryCount++;
            
            // Log the error with the specific WiFi error code
            Serial.print("WiFi connection failed. Status code: ");
            Serial.print(WiFi.status());
            Serial.print(", Retry count: ");
            Serial.println(wifiRetryCount);
            
            // Display different messages based on error code
            const char* errorMsg;
            switch (WiFi.status()) {
                case WL_IDLE_STATUS:
                    errorMsg = "WiFi idle";
                    break;
                case WL_NO_SSID_AVAIL:
                    errorMsg = "SSID not found";
                    break;
                case WL_CONNECT_FAILED:
                    errorMsg = "Invalid password";
                    break;
                case WL_DISCONNECTED:
                    errorMsg = "Disconnected";
                    break;
                default:
                    errorMsg = "Connection error";
            }
            
            display->showWiFiError(WiFi.status(), wifiRetryCount, errorMsg);
            
            return false;
        }
    }
    
#ifdef MQTT_USE_TLS
    /**
     * Configure TLS settings for secure MQTT connection
     */
    void setupTLS() {
        Serial.println("Setting up TLS for MQTT connection");
        
        // Set up CA certificate if provided
        if (MQTT_CA_CERT != NULL && strlen(MQTT_CA_CERT) > 0) {
            Serial.println("Using provided CA certificate");
            espClient->setCACert(MQTT_CA_CERT);
        } else {
            Serial.println("No CA cert provided, using default trust store");
        }
        
        // Set up client certificate and key if provided
        if (MQTT_CLIENT_CERT != NULL && strlen(MQTT_CLIENT_CERT) > 0) {
            if (MQTT_CLIENT_KEY != NULL && strlen(MQTT_CLIENT_KEY) > 0) {
                Serial.println("Using client certificate and key");
                espClient->setCertificate(MQTT_CLIENT_CERT);
                espClient->setPrivateKey(MQTT_CLIENT_KEY);
            } else {
                Serial.println("Client certificate provided but key missing");
                display->displaySystemStatus("TLS config error: key missing");
            }
        }
        
        // Configure server verification mode
        if (MQTT_INSECURE) {
            Serial.println("WARNING: TLS server verification disabled");
            espClient->setInsecure();
        }
        
        Serial.println("TLS configuration complete");
    }
#endif
    
    /**
     * Connect to MQTT broker
     * @return true if connected successfully, false otherwise
     */
    bool connectToMQTT() {
        if (!wifiConnected) {
            Serial.println("Cannot connect to MQTT: WiFi not connected");
            display->displaySystemStatus("WiFi not connected");
            return false;
        }
        
        display->displaySystemStatus("Connecting to MQTT...");
        
        // Create a unique client ID
        char clientId[50];
        snprintf(clientId, sizeof(clientId), "%s_%lX", mqttClientId, random(0xffff));
        
        Serial.print("Attempting MQTT connection to ");
        Serial.print(mqttServer);
        Serial.print(":");
        Serial.print(mqttPort);
        Serial.print(" with client ID ");
        Serial.println(clientId);
        
#ifdef MQTT_USE_TLS
        // Set up TLS configuration
        setupTLS();
#endif

        // Try to connect with timeout
        unsigned long startTime = millis();
        bool timeout = false;
        
        // Connect with credentials if provided
        bool connectResult = false;
        if (strlen(mqttUsername) > 0) {
            connectResult = mqttClient->connect(clientId, mqttUsername, mqttPassword);
        } else {
            connectResult = mqttClient->connect(clientId);
        }
        
        // Check connection result
        if (connectResult) {
            Serial.println("MQTT connected successfully");
            mqttConnected = true;
            mqttRetryCount = 0;
            
            // Subscribe to topics with appropriate QoS levels
            bool subResult1 = mqttClient->subscribe(topicRequests, 1);  // QoS 1 for important requests
            bool subResult2 = mqttClient->subscribe(LEGACY_FACULTY_MESSAGE_TOPIC, 0);  // QoS 0 for less critical messages
            bool subResult3 = mqttClient->subscribe(SYSTEM_STATUS_TOPIC, 1);  // QoS 1 for system status
            
            Serial.println("MQTT topic subscriptions:");
            Serial.print(topicRequests);
            Serial.print(" - ");
            Serial.println(subResult1 ? "Success" : "Failed");
            
            Serial.print(LEGACY_FACULTY_MESSAGE_TOPIC);
            Serial.print(" - ");
            Serial.println(subResult2 ? "Success" : "Failed");
            
            Serial.print(SYSTEM_STATUS_TOPIC);
            Serial.print(" - ");
            Serial.println(subResult3 ? "Success" : "Failed");
            
            // Show connection info
            display->updateUIArea(1, "MQTT Connected");
            display->displaySystemStatus("MQTT connected");
            
            return true;
        } else {
            mqttConnected = false;
            mqttRetryCount++;
            
            // Get error information
            int errorCode = mqttClient->state();
            char errorMsg[64];
            snprintf(errorMsg, sizeof(errorMsg), "MQTT error: ");
            
            switch (errorCode) {
                case -4: // MQTT_CONNECTION_TIMEOUT
                    strcat(errorMsg, "Timeout");
                    break;
                case -3: // MQTT_CONNECTION_LOST
                    strcat(errorMsg, "Connection Lost");
                    break;
                case -2: // MQTT_CONNECT_FAILED
                    strcat(errorMsg, "Network Connection Failed");
                    break;
                case -1: // MQTT_DISCONNECTED
                    strcat(errorMsg, "Disconnected");
                    break;
                case 1: // MQTT_CONNECT_BAD_PROTOCOL
                    strcat(errorMsg, "Bad Protocol");
                    break;
                case 2: // MQTT_CONNECT_BAD_CLIENT_ID
                    strcat(errorMsg, "Bad Client ID");
                    break;
                case 3: // MQTT_CONNECT_UNAVAILABLE
                    strcat(errorMsg, "Server Unavailable");
                    break;
                case 4: // MQTT_CONNECT_BAD_CREDENTIALS
                    strcat(errorMsg, "Bad Credentials");
                    break;
                case 5: // MQTT_CONNECT_UNAUTHORIZED
                    strcat(errorMsg, "Unauthorized");
                    break;
                default:
                    char codeStr[8];
                    snprintf(codeStr, sizeof(codeStr), "Error %d", errorCode);
                    strcat(errorMsg, codeStr);
            }
            
            Serial.print("MQTT connection failed, state: ");
            Serial.print(errorCode);
            Serial.print(" (");
            Serial.print(errorMsg);
            Serial.print("), retry count: ");
            Serial.println(mqttRetryCount);
            
            display->displaySystemStatus(errorMsg);
            
            return false;
        }
    }
    
    /**
     * Handle reconnection events with MQTT broker
     */
    void handleMQTTReconnection() {
        // Resubscribe to topics
        bool subResult1 = mqttClient->subscribe(topicRequests, 1);  // QoS 1 for important requests
        bool subResult2 = mqttClient->subscribe(LEGACY_FACULTY_MESSAGE_TOPIC, 0);  // QoS 0 for less critical messages
        bool subResult3 = mqttClient->subscribe(SYSTEM_STATUS_TOPIC, 1);  // QoS 1 for system status
        
        // Log subscription results
        Serial.println("MQTT topic subscriptions on reconnection:");
        Serial.print(topicRequests);
        Serial.print(" - ");
        Serial.println(subResult1 ? "Success" : "Failed");
        
        Serial.print(LEGACY_FACULTY_MESSAGE_TOPIC);
        Serial.print(" - ");
        Serial.println(subResult2 ? "Success" : "Failed");
        
        Serial.print(SYSTEM_STATUS_TOPIC);
        Serial.print(" - ");
        Serial.println(subResult3 ? "Success" : "Failed");
    }
    
    /**
     * Check and maintain network connections
     * @return true if all connections are active, false otherwise
     */
    bool maintainConnections() {
        // Check WiFi connection and attempt reconnection if needed
        if (WiFi.status() != WL_CONNECTED) {
            // Only retry WiFi at intervals and if we haven't exceeded max retries
            if (!wifiConnected || 
                (wifiRetryCount < WIFI_MAX_RETRIES && 
                 millis() - lastWifiRetryTime > CONNECTION_RETRY_INTERVAL)) {
                
                Serial.println("WiFi disconnected, attempting to reconnect");
                lastWifiRetryTime = millis();
                wifiConnected = connectToWiFi();
                
                if (!wifiConnected && wifiRetryCount >= WIFI_MAX_RETRIES) {
                    Serial.println("Maximum WiFi retries reached, will try again later");
                    // Wait a longer time before next retry after max retries
                    lastWifiRetryTime = millis() - CONNECTION_RETRY_INTERVAL + 60000; // Wait extra minute
                }
            }
        } else {
            wifiConnected = true;
        }
    
        // Check MQTT connection and attempt reconnection if needed
        static bool wasMQTTConnected = false;
        mqttConnected = mqttClient->connected();
        
        if (wifiConnected && !mqttConnected) {
            // Only retry MQTT at intervals
            if (millis() - lastMqttRetryTime > CONNECTION_RETRY_INTERVAL) {
                Serial.println("MQTT disconnected, attempting to reconnect");
                lastMqttRetryTime = millis();
                mqttConnected = connectToMQTT();
                
                // Check if we should reset WiFi after too many MQTT failures
                if (!mqttConnected && mqttRetryCount >= MQTT_MAX_RETRIES) {
                    Serial.println("Maximum MQTT retries reached, resetting WiFi connection");
                    WiFi.disconnect();
                    wifiConnected = false;
                    wifiRetryCount = 0;
                    mqttRetryCount = 0;
                    delay(1000);
                }
            }
        }
    
        // Handle MQTT reconnection event (from disconnected to connected)
        if (mqttConnected && !wasMQTTConnected) {
            Serial.println("MQTT reconnection detected, resubscribing to topics");
            handleMQTTReconnection();
        }
        wasMQTTConnected = mqttConnected;
    
        if (mqttConnected) {
            mqttClient->loop();
        }
        
        return wifiConnected && mqttConnected;
    }
    
    /**
     * Publish a message to an MQTT topic
     * @param topic The topic to publish to
     * @param message The message to publish
     * @param qos The QoS level (0, 1, or 2)
     * @param retain Whether to retain the message
     * @return true if successfully published, false otherwise
     */
    bool publishMessage(const char* topic, const char* message, int qos = 0, bool retain = false) {
        if (!mqttConnected) {
            Serial.println("Cannot publish: MQTT not connected");
            return false;
        }
        
        bool success = mqttClient->publish(topic, message, retain, qos);
        
        char logBuffer[150];
        snprintf(logBuffer, sizeof(logBuffer),
                 "Published to %s (QoS %d, Retain: %s): %s [%s]",
                 topic, qos, retain ? "true" : "false", message,
                 success ? "SUCCESS" : "FAILED");
        Serial.println(logBuffer);
        
        return success;
    }
    
    /**
     * Publish a JSON document to an MQTT topic
     * @param topic The topic to publish to
     * @param doc The JSON document to publish
     * @param qos The QoS level (0, 1, or 2)
     * @param retain Whether to retain the message
     * @return true if successfully published, false otherwise
     */
    bool publishJSONMessage(const char* topic, JsonDocument& doc, int qos = 0, bool retain = false) {
        char jsonBuffer[MAX_PAYLOAD_SIZE];
        size_t jsonSize = serializeJson(doc, jsonBuffer, sizeof(jsonBuffer));
        
        if (jsonSize > 0 && jsonSize < sizeof(jsonBuffer)) {
            return publishMessage(topic, jsonBuffer, qos, retain);
        } else {
            Serial.println("Error serializing JSON or buffer too small");
            return false;
        }
    }
    
    /**
     * Publish a faculty status update
     * @param isPresent Whether the faculty is present
     * @param isManual Whether the status is manually set
     * @param qos The QoS level (0, 1, or 2)
     * @param retain Whether to retain the message
     * @return true if successfully published, false otherwise
     */
    bool publishFacultyStatus(bool isPresent, bool isManual, int qos = 1, bool retain = true) {
        // Use static memory allocation for JSON document to avoid heap fragmentation
        StaticJsonDocument<128> doc; // Small fixed-size document uses stack memory
        
        // Add data to document
        doc["status"] = isPresent;
        doc["type"] = isManual ? "manual" : "ble";
        doc["faculty_id"] = FACULTY_ID;  // Always include faculty_id for consistency
        
        // Publish the message
        bool success = publishJSONMessage(topicStatus, doc, qos, retain);
        
        // Update display based on the actual status being published
        char displayStatusBuffer[64]; // Fixed size display buffer
        snprintf(displayStatusBuffer, sizeof(displayStatusBuffer), 
                "Status (%s): %s", 
                isManual ? "Manual" : "BLE", 
                isPresent ? "Available" : "Unavailable");
        display->displaySystemStatus(displayStatusBuffer);
        
        return success;
    }
    
    /**
     * Publish a consultation response
     * @param consultationId The ID of the consultation
     * @param action The action to take (accept, reject, start, complete, cancel)
     * @return true if successfully published, false otherwise
     */
    bool publishConsultationResponse(long consultationId, const char* action) {
        if (consultationId <= 0) {
            Serial.println("Invalid consultation ID");
            return false;
        }
        
        StaticJsonDocument<128> doc;
        doc["action"] = action;
        doc["consultation_id"] = consultationId;
        
        return publishJSONMessage(topicResponse, doc, 1, false); // QoS 1, no retain
    }
    
    /**
     * Get the status topic for this faculty
     * @return The status topic
     */
    const char* getStatusTopic() {
        return topicStatus;
    }
    
    /**
     * Get the requests topic for this faculty
     * @return The requests topic
     */
    const char* getRequestsTopic() {
        return topicRequests;
    }
    
    /**
     * Get the response topic for this faculty
     * @return The response topic
     */
    const char* getResponseTopic() {
        return topicResponse;
    }
    
    /**
     * Check if WiFi is connected
     * @return true if WiFi is connected, false otherwise
     */
    bool isWiFiConnected() {
        return wifiConnected;
    }
    
    /**
     * Check if MQTT is connected
     * @return true if MQTT is connected, false otherwise
     */
    bool isMQTTConnected() {
        return mqttConnected;
    }
};

#endif // NETWORK_MANAGER_H 