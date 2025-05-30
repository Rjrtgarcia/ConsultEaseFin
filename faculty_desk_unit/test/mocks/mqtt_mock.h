/**
 * ConsultEase - MQTT Mock
 * 
 * This file provides a mock implementation of the PubSubClient class
 * for testing MQTT functionality without requiring an actual broker.
 */

#ifndef MQTT_MOCK_H
#define MQTT_MOCK_H

#include <Arduino.h>
#include <vector>
#include <string>
#include <map>
#include <functional>
#include "wifi_mock.h"

// MQTT client states (matching the real ones)
#define MQTT_CONNECTION_TIMEOUT     -4
#define MQTT_CONNECTION_LOST        -3
#define MQTT_CONNECT_FAILED         -2
#define MQTT_DISCONNECTED           -1
#define MQTT_CONNECTED               0
#define MQTT_CONNECT_BAD_PROTOCOL    1
#define MQTT_CONNECT_BAD_CLIENT_ID   2
#define MQTT_CONNECT_UNAVAILABLE     3
#define MQTT_CONNECT_BAD_CREDENTIALS 4
#define MQTT_CONNECT_UNAUTHORIZED    5

// MQTT callback function type
typedef std::function<void(char*, uint8_t*, unsigned int)> MQTTCallback;

// Message struct for storing published/received messages
struct MQTTMessage {
    String topic;
    String payload;
    bool retained;
    int qos;
};

// Mock PubSubClient
class PubSubClient_Mock {
private:
    std::vector<std::string> methodCallLog;
    int _state;
    String _clientId;
    String _username;
    String _password;
    bool _willRetain;
    int _willQos;
    String _willTopic;
    String _willMessage;
    MQTTCallback _callback;
    WiFiClient_Mock* _client;
    String _server;
    uint16_t _port;
    
    // Stored messages by topic
    std::map<String, std::vector<MQTTMessage>> _messages;
    
    // Subscribed topics
    std::map<String, int> _subscriptions;

public:
    PubSubClient_Mock() : 
        _state(MQTT_DISCONNECTED),
        _client(nullptr),
        _port(1883) {
        
        methodCallLog.push_back("PubSubClient_Mock constructor called");
    }
    
    // Constructor with client
    PubSubClient_Mock(WiFiClient_Mock& client) : 
        _state(MQTT_DISCONNECTED),
        _client(&client),
        _port(1883) {
        
        methodCallLog.push_back("PubSubClient_Mock constructor with client called");
    }
    
    // Set server by address
    PubSubClient_Mock& setServer(const char* server, uint16_t port) {
        _server = server;
        _port = port;
        methodCallLog.push_back("setServer(" + String(server) + ", " + String(port) + ")");
        return *this;
    }
    
    // Set server by IP
    PubSubClient_Mock& setServer(IPAddress ip, uint16_t port) {
        String ipStr = String(ip[0]) + "." + String(ip[1]) + "." + String(ip[2]) + "." + String(ip[3]);
        _server = ipStr;
        _port = port;
        methodCallLog.push_back("setServer(IP:" + ipStr + ", " + String(port) + ")");
        return *this;
    }
    
    // Set callback
    PubSubClient_Mock& setCallback(MQTTCallback callback) {
        _callback = callback;
        methodCallLog.push_back("setCallback()");
        return *this;
    }
    
    // Set client
    PubSubClient_Mock& setClient(WiFiClient_Mock& client) {
        _client = &client;
        methodCallLog.push_back("setClient()");
        return *this;
    }
    
    // Connect without credentials
    bool connect(const char* clientId) {
        _clientId = clientId;
        _username = "";
        _password = "";
        methodCallLog.push_back("connect(" + String(clientId) + ")");
        
        // For testing, always connect with standard client ID pattern
        if (String(clientId).startsWith("FacultyUnit") || 
            String(clientId).startsWith("TestClient") || 
            String(clientId).startsWith("MockClient")) {
            _state = MQTT_CONNECTED;
            return true;
        }
        
        _state = MQTT_CONNECT_BAD_CLIENT_ID;
        return false;
    }
    
    // Connect with credentials
    bool connect(const char* clientId, const char* username, const char* password) {
        _clientId = clientId;
        _username = username;
        _password = password;
        methodCallLog.push_back("connect(" + String(clientId) + ", " + String(username) + ", ***)");
        
        // For testing, check for specific test credentials
        if ((strcmp(username, "faculty") == 0 && strcmp(password, "faculty123") == 0) ||
            (strcmp(username, "test") == 0 && strcmp(password, "test123") == 0)) {
            _state = MQTT_CONNECTED;
            return true;
        }
        
        _state = MQTT_CONNECT_BAD_CREDENTIALS;
        return false;
    }
    
    // Connect with will message
    bool connect(const char* clientId, const char* willTopic, uint8_t willQos, bool willRetain, const char* willMessage) {
        _clientId = clientId;
        _willTopic = willTopic;
        _willQos = willQos;
        _willRetain = willRetain;
        _willMessage = willMessage;
        
        methodCallLog.push_back("connect(" + String(clientId) + ", " + String(willTopic) + ", " + 
                               String(willQos) + ", " + String(willRetain) + ", " + String(willMessage) + ")");
        
        _state = MQTT_CONNECTED;
        return true;
    }
    
    // Connect with credentials and will message
    bool connect(const char* clientId, const char* username, const char* password, 
                 const char* willTopic, uint8_t willQos, bool willRetain, const char* willMessage) {
        _clientId = clientId;
        _username = username;
        _password = password;
        _willTopic = willTopic;
        _willQos = willQos;
        _willRetain = willRetain;
        _willMessage = willMessage;
        
        methodCallLog.push_back("connect(full)");
        
        // For testing, check for specific test credentials
        if ((strcmp(username, "faculty") == 0 && strcmp(password, "faculty123") == 0) ||
            (strcmp(username, "test") == 0 && strcmp(password, "test123") == 0)) {
            _state = MQTT_CONNECTED;
            return true;
        }
        
        _state = MQTT_CONNECT_BAD_CREDENTIALS;
        return false;
    }
    
    // Disconnect
    void disconnect() {
        methodCallLog.push_back("disconnect()");
        _state = MQTT_DISCONNECTED;
    }
    
    // Subscribe to a topic
    bool subscribe(const char* topic) {
        methodCallLog.push_back("subscribe(" + String(topic) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        _subscriptions[topic] = 0; // QoS 0
        return true;
    }
    
    // Subscribe to a topic with QoS
    bool subscribe(const char* topic, uint8_t qos) {
        methodCallLog.push_back("subscribe(" + String(topic) + ", " + String(qos) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        _subscriptions[topic] = qos;
        return true;
    }
    
    // Unsubscribe from a topic
    bool unsubscribe(const char* topic) {
        methodCallLog.push_back("unsubscribe(" + String(topic) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        _subscriptions.erase(topic);
        return true;
    }
    
    // Check if client is connected
    bool connected() {
        return _state == MQTT_CONNECTED;
    }
    
    // Get client state
    int state() {
        return _state;
    }
    
    // Set the connection state (for testing)
    void setState(int state) {
        _state = state;
    }
    
    // Publish message
    bool publish(const char* topic, const char* payload) {
        methodCallLog.push_back("publish(" + String(topic) + ", " + String(payload) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        MQTTMessage msg;
        msg.topic = topic;
        msg.payload = payload;
        msg.retained = false;
        msg.qos = 0;
        
        _messages[topic].push_back(msg);
        
        // Call callback for subscribers
        deliverMessage(topic, payload);
        
        return true;
    }
    
    // Publish message with retain flag
    bool publish(const char* topic, const char* payload, bool retained) {
        methodCallLog.push_back("publish(" + String(topic) + ", " + String(payload) + ", " + String(retained) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        MQTTMessage msg;
        msg.topic = topic;
        msg.payload = payload;
        msg.retained = retained;
        msg.qos = 0;
        
        _messages[topic].push_back(msg);
        
        // Call callback for subscribers
        deliverMessage(topic, payload);
        
        return true;
    }
    
    // Publish message with retain flag and QoS
    bool publish(const char* topic, const char* payload, bool retained, int qos) {
        methodCallLog.push_back("publish(" + String(topic) + ", " + String(payload) + ", " + 
                               String(retained) + ", " + String(qos) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        MQTTMessage msg;
        msg.topic = topic;
        msg.payload = payload;
        msg.retained = retained;
        msg.qos = qos;
        
        _messages[topic].push_back(msg);
        
        // Call callback for subscribers
        deliverMessage(topic, payload);
        
        return true;
    }
    
    // Publish message with binary payload
    bool publish(const char* topic, const uint8_t* payload, unsigned int plength) {
        methodCallLog.push_back("publish(" + String(topic) + ", binary, " + String(plength) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        // Convert binary payload to string for testing
        String payloadStr;
        for (unsigned int i = 0; i < plength; i++) {
            payloadStr += (char)payload[i];
        }
        
        MQTTMessage msg;
        msg.topic = topic;
        msg.payload = payloadStr;
        msg.retained = false;
        msg.qos = 0;
        
        _messages[topic].push_back(msg);
        
        // Call callback for subscribers
        deliverMessage(topic, payloadStr.c_str());
        
        return true;
    }
    
    // Publish message with binary payload and retain flag
    bool publish(const char* topic, const uint8_t* payload, unsigned int plength, bool retained) {
        methodCallLog.push_back("publish(" + String(topic) + ", binary, " + String(plength) + 
                               ", " + String(retained) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        // Convert binary payload to string for testing
        String payloadStr;
        for (unsigned int i = 0; i < plength; i++) {
            payloadStr += (char)payload[i];
        }
        
        MQTTMessage msg;
        msg.topic = topic;
        msg.payload = payloadStr;
        msg.retained = retained;
        msg.qos = 0;
        
        _messages[topic].push_back(msg);
        
        // Call callback for subscribers
        deliverMessage(topic, payloadStr.c_str());
        
        return true;
    }
    
    // Publish message with binary payload, retain flag, and QoS
    bool publish(const char* topic, const uint8_t* payload, unsigned int plength, bool retained, int qos) {
        methodCallLog.push_back("publish(" + String(topic) + ", binary, " + String(plength) + 
                               ", " + String(retained) + ", " + String(qos) + ")");
        
        if (_state != MQTT_CONNECTED) {
            return false;
        }
        
        // Convert binary payload to string for testing
        String payloadStr;
        for (unsigned int i = 0; i < plength; i++) {
            payloadStr += (char)payload[i];
        }
        
        MQTTMessage msg;
        msg.topic = topic;
        msg.payload = payloadStr;
        msg.retained = retained;
        msg.qos = qos;
        
        _messages[topic].push_back(msg);
        
        // Call callback for subscribers
        deliverMessage(topic, payloadStr.c_str());
        
        return true;
    }
    
    // Process incoming messages
    bool loop() {
        methodCallLog.push_back("loop()");
        return true;
    }
    
    // Deliver a message to callback (for testing)
    void deliverMessage(const char* topic, const char* payload) {
        if (_callback && isSubscribed(topic)) {
            // Convert payload to byte array
            uint8_t* payloadBytes = new uint8_t[strlen(payload)];
            for (size_t i = 0; i < strlen(payload); i++) {
                payloadBytes[i] = (uint8_t)payload[i];
            }
            
            // Make a copy of the topic string
            char* topicCopy = new char[strlen(topic) + 1];
            strcpy(topicCopy, topic);
            
            // Call the callback
            _callback(topicCopy, payloadBytes, strlen(payload));
            
            // Clean up
            delete[] payloadBytes;
            delete[] topicCopy;
        }
    }
    
    // Check if a topic is subscribed
    bool isSubscribed(const char* topic) {
        // Direct match
        if (_subscriptions.find(topic) != _subscriptions.end()) {
            return true;
        }
        
        // Topic pattern matching (simplified)
        for (const auto& subscription : _subscriptions) {
            // Check for wildcard subscriptions
            if (subscription.first.endsWith("#")) {
                String prefix = subscription.first.substring(0, subscription.first.length() - 1);
                if (String(topic).startsWith(prefix)) {
                    return true;
                }
            }
            
            // Check for single-level wildcard
            if (subscription.first.indexOf("+") >= 0) {
                // This is a simplification - a real implementation would properly handle
                // multi-level topic matching with + wildcards
                String pattern = subscription.first;
                pattern.replace("+", "[^/]+");
                // This would be a regex match in a real implementation
                if (pattern == topic) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    // Get the method call log
    const std::vector<std::string>& getMethodCallLog() const {
        return methodCallLog;
    }
    
    // Clear method call log
    void clearMethodCallLog() {
        methodCallLog.clear();
    }
    
    // Get all messages for a topic
    const std::vector<MQTTMessage>& getMessages(const char* topic) {
        return _messages[topic];
    }
    
    // Get the last message for a topic
    MQTTMessage getLastMessage(const char* topic) {
        if (_messages.find(topic) != _messages.end() && !_messages[topic].empty()) {
            return _messages[topic].back();
        }
        
        // Return empty message
        MQTTMessage emptyMsg;
        emptyMsg.topic = "";
        emptyMsg.payload = "";
        emptyMsg.retained = false;
        emptyMsg.qos = 0;
        return emptyMsg;
    }
    
    // Clear all stored messages
    void clearMessages() {
        _messages.clear();
    }
    
    // Get all subscriptions
    const std::map<String, int>& getSubscriptions() const {
        return _subscriptions;
    }
    
    // Clear all subscriptions
    void clearSubscriptions() {
        _subscriptions.clear();
    }
};

// Use this typedef to easily switch between mock and real implementations
typedef PubSubClient_Mock MockPubSubClient;

#endif // MQTT_MOCK_H 