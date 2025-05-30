/**
 * ConsultEase - WiFi Mock
 * 
 * This file provides mock implementations of WiFi-related classes
 * for testing purposes without requiring actual network connectivity.
 */

#ifndef WIFI_MOCK_H
#define WIFI_MOCK_H

#include <Arduino.h>
#include <vector>
#include <string>
#include <map>

// Mock WiFi status codes (matching the real ones)
#define WL_CONNECTED 3
#define WL_DISCONNECTED 6
#define WL_CONNECT_FAILED 4
#define WL_NO_SSID_AVAIL 1
#define WL_IDLE_STATUS 0

// Mock WiFi client class
class WiFiClient_Mock {
private:
    bool _connected;
    std::vector<uint8_t> _receiveBuffer;
    std::vector<uint8_t> _sendBuffer;
    std::vector<std::string> methodCallLog;

public:
    WiFiClient_Mock() : _connected(false) {
        methodCallLog.push_back("WiFiClient_Mock constructor called");
    }
    
    // Connect to a server
    int connect(const char* host, uint16_t port) {
        String logMsg = "connect(" + String(host) + ", " + String(port) + ")";
        methodCallLog.push_back(logMsg.c_str());
        
        // For testing, we'll simulate successful connections to known hosts
        if (strcmp(host, "test.mosquitto.org") == 0 || 
            strcmp(host, "127.0.0.1") == 0 || 
            strcmp(host, "localhost") == 0 || 
            strcmp(host, "192.168.1.100") == 0) {
            _connected = true;
            return 1;
        }
        
        _connected = false;
        return 0;
    }
    
    // Connect to a server by IP
    int connect(IPAddress ip, uint16_t port) {
        String ipStr = String(ip[0]) + "." + String(ip[1]) + "." + String(ip[2]) + "." + String(ip[3]);
        String logMsg = "connect(IP:" + ipStr + ", " + String(port) + ")";
        methodCallLog.push_back(logMsg.c_str());
        
        // Simulate connection to local addresses
        if (ip[0] == 127 || ip[0] == 192 || ip[0] == 10) {
            _connected = true;
            return 1;
        }
        
        _connected = false;
        return 0;
    }
    
    // Check if connected
    operator bool() {
        return _connected;
    }
    
    // Write data
    size_t write(uint8_t b) {
        if (!_connected) return 0;
        
        _sendBuffer.push_back(b);
        return 1;
    }
    
    // Write buffer
    size_t write(const uint8_t *buf, size_t size) {
        if (!_connected) return 0;
        
        methodCallLog.push_back("write(buffer, " + String(size) + ")");
        
        for (size_t i = 0; i < size; i++) {
            _sendBuffer.push_back(buf[i]);
        }
        
        return size;
    }
    
    // Available data
    int available() {
        return _receiveBuffer.size();
    }
    
    // Read one byte
    int read() {
        if (_receiveBuffer.empty()) {
            return -1;
        }
        
        uint8_t b = _receiveBuffer.front();
        _receiveBuffer.erase(_receiveBuffer.begin());
        return b;
    }
    
    // Read buffer
    int read(uint8_t *buf, size_t size) {
        if (_receiveBuffer.empty()) {
            return 0;
        }
        
        size_t readCount = std::min(size, _receiveBuffer.size());
        
        for (size_t i = 0; i < readCount; i++) {
            buf[i] = _receiveBuffer.front();
            _receiveBuffer.erase(_receiveBuffer.begin());
        }
        
        return readCount;
    }
    
    // Close connection
    void stop() {
        methodCallLog.push_back("stop()");
        _connected = false;
    }
    
    // Check if connected
    bool connected() {
        return _connected;
    }
    
    // Flush (does nothing in mock)
    void flush() {
        methodCallLog.push_back("flush()");
    }
    
    // Set test data to be returned on read
    void setReceiveBuffer(const uint8_t* data, size_t size) {
        _receiveBuffer.clear();
        for (size_t i = 0; i < size; i++) {
            _receiveBuffer.push_back(data[i]);
        }
    }
    
    // Set test data as string
    void setReceiveString(const char* str) {
        _receiveBuffer.clear();
        size_t len = strlen(str);
        for (size_t i = 0; i < len; i++) {
            _receiveBuffer.push_back(str[i]);
        }
    }
    
    // Get sent data
    const std::vector<uint8_t>& getSendBuffer() const {
        return _sendBuffer;
    }
    
    // Get sent data as string
    String getSendString() const {
        String result;
        for (auto b : _sendBuffer) {
            result += (char)b;
        }
        return result;
    }
    
    // Clear send buffer
    void clearSendBuffer() {
        _sendBuffer.clear();
    }
    
    // Get method call log
    const std::vector<std::string>& getMethodCallLog() const {
        return methodCallLog;
    }
    
    // Clear method call log
    void clearMethodCallLog() {
        methodCallLog.clear();
    }
    
    // Set connected state (for testing)
    void setConnected(bool connected) {
        _connected = connected;
    }
};

// Secure WiFi client mock
class WiFiClientSecure_Mock : public WiFiClient_Mock {
private:
    std::vector<std::string> methodCallLog;
    bool _insecure;
    const char* _caCert;
    const char* _clientCert;
    const char* _clientKey;

public:
    WiFiClientSecure_Mock() : WiFiClient_Mock(), _insecure(false), _caCert(nullptr), _clientCert(nullptr), _clientKey(nullptr) {
        methodCallLog.push_back("WiFiClientSecure_Mock constructor called");
    }
    
    // Set CA certificate
    void setCACert(const char* cert) {
        methodCallLog.push_back("setCACert()");
        _caCert = cert;
    }
    
    // Set client certificate
    void setCertificate(const char* cert) {
        methodCallLog.push_back("setCertificate()");
        _clientCert = cert;
    }
    
    // Set client private key
    void setPrivateKey(const char* key) {
        methodCallLog.push_back("setPrivateKey()");
        _clientKey = key;
    }
    
    // Disable server verification
    void setInsecure() {
        methodCallLog.push_back("setInsecure()");
        _insecure = true;
    }
    
    // Get method call log (overriding the parent method)
    const std::vector<std::string>& getSecureMethodCallLog() const {
        return methodCallLog;
    }
    
    // Check if CA cert is set
    bool hasCACert() const {
        return _caCert != nullptr;
    }
    
    // Check if client cert is set
    bool hasClientCert() const {
        return _clientCert != nullptr;
    }
    
    // Check if client key is set
    bool hasClientKey() const {
        return _clientKey != nullptr;
    }
    
    // Check if insecure mode is set
    bool isInsecure() const {
        return _insecure;
    }
};

// WiFi class mock
class WiFiClass_Mock {
private:
    std::vector<std::string> methodCallLog;
    int _status;
    IPAddress _localIP;
    String _ssid;
    int _rssi;
    uint8_t _macAddress[6];
    
    // WiFi power save modes
    typedef enum {
        WIFI_PS_NONE,
        WIFI_PS_MIN_MODEM,
        WIFI_PS_MAX_MODEM
    } wifi_ps_type_t;
    
    wifi_ps_type_t _powerSaveMode;

public:
    WiFiClass_Mock() : 
        _status(WL_DISCONNECTED),
        _rssi(-70),
        _powerSaveMode(WIFI_PS_NONE) {
        
        methodCallLog.push_back("WiFiClass_Mock constructor called");
        
        // Set default local IP
        _localIP[0] = 192;
        _localIP[1] = 168;
        _localIP[2] = 1;
        _localIP[3] = 100;
        
        // Set default MAC address
        for (int i = 0; i < 6; i++) {
            _macAddress[i] = i + 1;
        }
    }
    
    // Begin connection
    int begin(const char* ssid, const char* password) {
        methodCallLog.push_back("begin(" + String(ssid) + ", ***)");
        
        // Simulate connection to test networks
        if (strcmp(ssid, "ConsultEase") == 0 || 
            strcmp(ssid, "TestNetwork") == 0 || 
            strcmp(ssid, "MockWiFi") == 0) {
            _status = WL_CONNECTED;
            _ssid = ssid;
        } else {
            _status = WL_CONNECT_FAILED;
        }
        
        return _status;
    }
    
    // Disconnect
    int disconnect() {
        methodCallLog.push_back("disconnect()");
        _status = WL_DISCONNECTED;
        return WL_DISCONNECTED;
    }
    
    // Get connection status
    uint8_t status() {
        return _status;
    }
    
    // Get local IP
    IPAddress localIP() {
        return _localIP;
    }
    
    // Get SSID
    String SSID() {
        return _ssid;
    }
    
    // Get RSSI
    int RSSI() {
        return _rssi;
    }
    
    // Get MAC address
    uint8_t* macAddress(uint8_t* mac) {
        for (int i = 0; i < 6; i++) {
            mac[i] = _macAddress[i];
        }
        return mac;
    }
    
    // Set MAC address (for testing)
    void setMacAddress(const uint8_t* mac) {
        for (int i = 0; i < 6; i++) {
            _macAddress[i] = mac[i];
        }
    }
    
    // Set mode
    int mode(int m) {
        methodCallLog.push_back("mode(" + String(m) + ")");
        return 0;
    }
    
    // Set power save mode
    esp_err_t set_ps(wifi_ps_type_t ps_type) {
        methodCallLog.push_back("set_ps(" + String(ps_type) + ")");
        _powerSaveMode = ps_type;
        return ESP_OK;
    }
    
    // Get power save mode
    wifi_ps_type_t get_ps() {
        return _powerSaveMode;
    }
    
    // Set status (for testing)
    void setStatus(int status) {
        _status = status;
    }
    
    // Set local IP (for testing)
    void setLocalIP(IPAddress ip) {
        _localIP = ip;
    }
    
    // Set RSSI (for testing)
    void setRSSI(int rssi) {
        _rssi = rssi;
    }
    
    // Get method call log
    const std::vector<std::string>& getMethodCallLog() const {
        return methodCallLog;
    }
    
    // Clear method call log
    void clearMethodCallLog() {
        methodCallLog.clear();
    }
};

// Global WiFi instance
extern WiFiClass_Mock WiFi_Mock;

// ESP functions mock
namespace ESP_Mock {
    uint32_t getFreeHeap() {
        static uint32_t heapSize = 300000; // 300kB initial heap
        return heapSize;
    }
    
    // Simulate memory allocation/deallocation
    void simulateAllocation(uint32_t bytes) {
        uint32_t currentHeap = getFreeHeap();
        uint32_t newHeap = currentHeap > bytes ? currentHeap - bytes : 0;
        // This would modify the static heapSize in the getFreeHeap function
    }
    
    void simulateDeallocation(uint32_t bytes) {
        uint32_t currentHeap = getFreeHeap();
        uint32_t newHeap = currentHeap + bytes;
        // This would modify the static heapSize in the getFreeHeap function
    }
}

// Define typedefs for easy switching between real and mock implementations
typedef WiFiClient_Mock MockWiFiClient;
typedef WiFiClientSecure_Mock MockWiFiClientSecure;
typedef WiFiClass_Mock MockWiFi;

#endif // WIFI_MOCK_H 