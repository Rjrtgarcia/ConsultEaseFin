/**
 * ConsultEase - BLE Mock
 * 
 * This file provides mock implementations of NimBLE-related classes
 * for testing BLE functionality without requiring actual Bluetooth hardware.
 */

#ifndef BLE_MOCK_H
#define BLE_MOCK_H

#include <Arduino.h>
#include <vector>
#include <string>
#include <map>
#include <functional>

// Forward declarations
class NimBLEAddress_Mock;
class NimBLEAdvertisedDevice_Mock;
class NimBLEAdvertisedDeviceCallbacks_Mock;
class NimBLEScan_Mock;
class NimBLEDevice_Mock;

// BLE Address class
class NimBLEAddress_Mock {
private:
    uint8_t _address[6];
    std::string _macString;

public:
    // Default constructor
    NimBLEAddress_Mock() {
        memset(_address, 0, sizeof(_address));
        _macString = "00:00:00:00:00:00";
    }
    
    // Constructor with MAC address
    NimBLEAddress_Mock(const char* macAddress) {
        setAddress(macAddress);
    }
    
    // Constructor with byte array
    NimBLEAddress_Mock(const uint8_t* addr) {
        memcpy(_address, addr, 6);
        char macStr[18];
        snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
                _address[0], _address[1], _address[2], _address[3], _address[4], _address[5]);
        _macString = macStr;
    }
    
    // Set address from string
    void setAddress(const char* macAddress) {
        _macString = macAddress;
        
        // Parse MAC address
        int a, b, c, d, e, f;
        sscanf(macAddress, "%x:%x:%x:%x:%x:%x", &a, &b, &c, &d, &e, &f);
        _address[0] = (uint8_t)a;
        _address[1] = (uint8_t)b;
        _address[2] = (uint8_t)c;
        _address[3] = (uint8_t)d;
        _address[4] = (uint8_t)e;
        _address[5] = (uint8_t)f;
    }
    
    // Convert to string
    std::string toString() const {
        return _macString;
    }
    
    // Compare addresses
    bool equals(const NimBLEAddress_Mock& other) const {
        return memcmp(_address, other._address, 6) == 0;
    }
    
    // Get address bytes
    const uint8_t* getNative() const {
        return _address;
    }
};

// Advertised device class
class NimBLEAdvertisedDevice_Mock {
private:
    NimBLEAddress_Mock _address;
    std::string _name;
    int _rssi;
    bool _connectable;
    std::map<uint16_t, std::string> _serviceUUIDs;
    std::map<uint16_t, std::vector<uint8_t>> _manufacturerData;

public:
    // Constructor
    NimBLEAdvertisedDevice_Mock() : _rssi(-80), _connectable(true) {
    }
    
    // Set address
    void setAddress(const NimBLEAddress_Mock& address) {
        _address = address;
    }
    
    // Get address
    const NimBLEAddress_Mock& getAddress() const {
        return _address;
    }
    
    // Set name
    void setName(const std::string& name) {
        _name = name;
    }
    
    // Get name
    std::string getName() const {
        return _name;
    }
    
    // Set RSSI
    void setRSSI(int rssi) {
        _rssi = rssi;
    }
    
    // Get RSSI
    int getRSSI() const {
        return _rssi;
    }
    
    // Set connectable
    void setConnectable(bool connectable) {
        _connectable = connectable;
    }
    
    // Is connectable
    bool isConnectable() const {
        return _connectable;
    }
    
    // Add service UUID
    void addServiceUUID(uint16_t uuid, const std::string& uuidStr) {
        _serviceUUIDs[uuid] = uuidStr;
    }
    
    // Has service UUID
    bool hasServiceUUID(uint16_t uuid) const {
        return _serviceUUIDs.find(uuid) != _serviceUUIDs.end();
    }
    
    // Add manufacturer data
    void setManufacturerData(uint16_t companyId, const std::vector<uint8_t>& data) {
        _manufacturerData[companyId] = data;
    }
    
    // Has manufacturer data
    bool hasManufacturerData() const {
        return !_manufacturerData.empty();
    }
    
    // Get manufacturer data
    std::vector<uint8_t> getManufacturerData(uint16_t companyId) const {
        if (_manufacturerData.find(companyId) != _manufacturerData.end()) {
            return _manufacturerData.at(companyId);
        }
        return std::vector<uint8_t>();
    }
    
    // Get device info string
    std::string toString() const {
        std::string result = "Device: ";
        result += _address.toString();
        result += ", Name: ";
        result += _name;
        result += ", RSSI: ";
        result += std::to_string(_rssi);
        return result;
    }
};

// Advertised device callbacks base class
class NimBLEAdvertisedDeviceCallbacks_Mock {
public:
    // Constructor
    NimBLEAdvertisedDeviceCallbacks_Mock() {}
    
    // Virtual destructor
    virtual ~NimBLEAdvertisedDeviceCallbacks_Mock() {}
    
    // Callback for when a device is found
    virtual void onResult(NimBLEAdvertisedDevice_Mock* advertisedDevice) = 0;
};

// Scan result class
class NimBLEScanResults_Mock {
private:
    std::vector<NimBLEAdvertisedDevice_Mock> _devices;

public:
    // Constructor
    NimBLEScanResults_Mock() {}
    
    // Add a device
    void addDevice(const NimBLEAdvertisedDevice_Mock& device) {
        _devices.push_back(device);
    }
    
    // Get device count
    int getCount() const {
        return _devices.size();
    }
    
    // Clear results
    void clear() {
        _devices.clear();
    }
    
    // Get device at index
    const NimBLEAdvertisedDevice_Mock* getDevice(size_t index) const {
        if (index < _devices.size()) {
            return &_devices[index];
        }
        return nullptr;
    }
};

// Scan class
class NimBLEScan_Mock {
private:
    std::vector<std::string> methodCallLog;
    bool _scanning;
    NimBLEScanResults_Mock _results;
    NimBLEAdvertisedDeviceCallbacks_Mock* _callbacks;
    bool _activeScan;
    uint16_t _interval;
    uint16_t _window;
    uint16_t _duration;

public:
    // Constructor
    NimBLEScan_Mock() :
        _scanning(false),
        _callbacks(nullptr),
        _activeScan(true),
        _interval(100),
        _window(99),
        _duration(0) {
        
        methodCallLog.push_back("NimBLEScan_Mock constructor called");
    }
    
    // Set advertised device callbacks
    void setAdvertisedDeviceCallbacks(NimBLEAdvertisedDeviceCallbacks_Mock* callbacks) {
        methodCallLog.push_back("setAdvertisedDeviceCallbacks()");
        _callbacks = callbacks;
    }
    
    // Set active scan
    void setActiveScan(bool active) {
        methodCallLog.push_back("setActiveScan(" + String(active ? "true" : "false") + ")");
        _activeScan = active;
    }
    
    // Set interval
    void setInterval(uint16_t interval) {
        methodCallLog.push_back("setInterval(" + String(interval) + ")");
        _interval = interval;
    }
    
    // Set window
    void setWindow(uint16_t window) {
        methodCallLog.push_back("setWindow(" + String(window) + ")");
        _window = window;
    }
    
    // Start scan
    bool start(uint32_t duration, void (*scanCompleteCB)(NimBLEScanResults_Mock), bool continuous = false) {
        methodCallLog.push_back("start(" + String(duration) + ", " + String(continuous ? "true" : "false") + ")");
        
        _scanning = true;
        _duration = duration;
        
        return true;
    }
    
    // Stop scan
    void stop() {
        methodCallLog.push_back("stop()");
        _scanning = false;
    }
    
    // Check if scanning
    bool isScanning() const {
        return _scanning;
    }
    
    // Clear results
    void clearResults() {
        methodCallLog.push_back("clearResults()");
        _results.clear();
    }
    
    // Get results
    NimBLEScanResults_Mock getResults() {
        return _results;
    }
    
    // Simulate found device (for testing)
    void simulateDeviceFound(const NimBLEAdvertisedDevice_Mock& device) {
        _results.addDevice(device);
        
        if (_callbacks != nullptr) {
            NimBLEAdvertisedDevice_Mock* deviceCopy = new NimBLEAdvertisedDevice_Mock(device);
            _callbacks->onResult(deviceCopy);
            delete deviceCopy;
        }
    }
    
    // Get method call log
    const std::vector<std::string>& getMethodCallLog() const {
        return methodCallLog;
    }
    
    // Clear method call log
    void clearMethodCallLog() {
        methodCallLog.clear();
    }
    
    // Get active scan setting
    bool getActiveScan() const {
        return _activeScan;
    }
    
    // Get interval
    uint16_t getInterval() const {
        return _interval;
    }
    
    // Get window
    uint16_t getWindow() const {
        return _window;
    }
    
    // Get duration
    uint16_t getDuration() const {
        return _duration;
    }
};

// Static BLE device class (singleton)
class NimBLEDevice_Mock {
private:
    static std::vector<std::string> methodCallLog;
    static bool _initialized;
    static NimBLEScan_Mock* _pScan;

public:
    // Initialize BLE
    static void init(const std::string& deviceName) {
        methodCallLog.push_back("init(" + String(deviceName.c_str()) + ")");
        _initialized = true;
        
        if (_pScan == nullptr) {
            _pScan = new NimBLEScan_Mock();
        }
    }
    
    // Check if initialized
    static bool getInitialized() {
        return _initialized;
    }
    
    // Get scan object
    static NimBLEScan_Mock* getScan() {
        if (!_initialized) {
            return nullptr;
        }
        
        return _pScan;
    }
    
    // Get method call log
    static const std::vector<std::string>& getMethodCallLog() {
        return methodCallLog;
    }
    
    // Clear method call log
    static void clearMethodCallLog() {
        methodCallLog.clear();
    }
};

// Initialize static members
std::vector<std::string> NimBLEDevice_Mock::methodCallLog;
bool NimBLEDevice_Mock::_initialized = false;
NimBLEScan_Mock* NimBLEDevice_Mock::_pScan = nullptr;

// Use these typedefs to easily switch between mock and real implementations
typedef NimBLEAddress_Mock MockBLEAddress;
typedef NimBLEAdvertisedDevice_Mock MockBLEAdvertisedDevice;
typedef NimBLEAdvertisedDeviceCallbacks_Mock MockBLEAdvertisedDeviceCallbacks;
typedef NimBLEScanResults_Mock MockBLEScanResults;
typedef NimBLEScan_Mock MockBLEScan;
typedef NimBLEDevice_Mock MockBLEDevice;

#endif // BLE_MOCK_H 