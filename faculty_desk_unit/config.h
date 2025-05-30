#ifndef CONFIG_H
#define CONFIG_H

// ================================
// FACULTY DESK UNIT CONFIGURATION - WITH GRACE PERIOD BLE
// ================================
// Updated: May 29, 2025 23:13 (Philippines Time)
// Added: Grace Period functionality for reliable BLE presence detection

// === FACULTY INFORMATION ===
#define FACULTY_ID 1
#define FACULTY_NAME "Dave Jomillo"
#define FACULTY_DEPARTMENT "Helpdesk"

// === IBEACON CONFIGURATION ===
#define FACULTY_BEACON_MAC "51:00:25:04:02:A2"
#define FACULTY_BEACON_UUID "FDA50693-A4E2-4FB1-AFCF-C6EB07647825"
#define FACULTY_BEACON_MAJOR 1
#define FACULTY_BEACON_MINOR 2

// === OPTIMIZED BLE DETECTION SETTINGS ===
// Legacy settings (kept for compatibility)
#define BLE_SCAN_INTERVAL 3000        
#define BLE_SCAN_DURATION 2           
#define MAC_DETECTION_TIMEOUT 30000   
#define ENABLE_UUID_VALIDATION true   
#define ENABLE_MAJOR_MINOR_CHECK false 

// === ADAPTIVE BLE SCANNING ===
// Adaptive scanning intervals
#define BLE_SCAN_INTERVAL_SEARCHING 2000      // Fast scan when away (detect arrival)
#define BLE_SCAN_INTERVAL_MONITORING 8000     // Slow scan when present (confirm presence)
#define BLE_SCAN_INTERVAL_VERIFICATION 1000   // Quick scan during transitions

// Adaptive scan durations
#define BLE_SCAN_DURATION_QUICK 1             // Short scan when monitoring
#define BLE_SCAN_DURATION_FULL 3              // Full scan when searching

// State confirmation timings
#define PRESENCE_CONFIRM_TIME 6000            // Time to confirm presence change
#define ABSENCE_CONFIRM_TIME 15000            // Time to confirm absence

// Performance monitoring
#define BLE_STATS_REPORT_INTERVAL 60000      // Report stats every minute

// === GRACE PERIOD SETTINGS (NEW - JEYSIBN'S SUGGESTION) ===
#define BLE_GRACE_PERIOD_MS 60000              // 1 minute grace period before status change
#define BLE_RECONNECT_ATTEMPT_INTERVAL 5000    // Try reconnecting every 5 seconds
#define BLE_RECONNECT_MAX_ATTEMPTS 12          // 12 attempts = 1 minute total
#define BLE_FAST_RECONNECT_INTERVAL 2000       // Faster attempts in first 20 seconds
#define BLE_SIGNAL_STRENGTH_THRESHOLD -80      // Minimum RSSI to accept signal

// === WIFI CONFIGURATION ===
#define WIFI_SSID "Je"                
#define WIFI_PASSWORD "qazxcvbnm"     
#define WIFI_CONNECT_TIMEOUT 20000    
#define WIFI_RECONNECT_INTERVAL 5000  

// === MQTT CONFIGURATION ===
#define MQTT_SERVER "192.168.1.100"   
#define MQTT_PORT 1883
#define MQTT_USERNAME "faculty_desk"  
#define MQTT_PASSWORD "desk_password" 
#define MQTT_KEEPALIVE 60
#define MQTT_QOS 1
#define MQTT_CLIENT_ID "Faculty_Desk_Unit_1"

// === MQTT TOPICS ===
// Include mqtt_topics.h for standardized topics
#include "mqtt_topics.h"

// Faculty ID-specific topics - will be constructed based on FACULTY_ID
#define TOPIC_ID_STR String(FACULTY_ID)
#define MQTT_TOPIC_STATUS FACULTY_STATUS_TOPIC(TOPIC_ID_STR.c_str())
#define MQTT_TOPIC_MESSAGES FACULTY_REQUEST_TOPIC(TOPIC_ID_STR.c_str())
#define MQTT_TOPIC_HEARTBEAT FACULTY_HEARTBEAT_TOPIC(TOPIC_ID_STR.c_str())
#define MQTT_TOPIC_RESPONSES FACULTY_RESPONSE_TOPIC(TOPIC_ID_STR.c_str())

// === BUTTON CONFIGURATION ===
#define BUTTON_A_PIN 15               // Blue button (Acknowledge)
#define BUTTON_B_PIN 4                // Red button (Busy)
#define BUTTON_DEBOUNCE_DELAY 50      // Debounce delay in milliseconds
#define BUTTON_LONG_PRESS_TIME 1000   // Long press detection time

// === DISPLAY CONFIGURATION (2.4" 320x240 ST7789) ===
#define TFT_CS 5      
#define TFT_RST 22    
#define TFT_DC 21     
#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 240

// === SIMPLIFIED UI LAYOUT ===
#define TOP_PANEL_HEIGHT 30           
#define TOP_PANEL_Y 0
#define MAIN_AREA_Y 35                
#define MAIN_AREA_HEIGHT 140          
#define STATUS_PANEL_HEIGHT 25        
#define STATUS_PANEL_Y 180            
#define BOTTOM_PANEL_HEIGHT 30        
#define BOTTOM_PANEL_Y 210            

// Text positions
#define PROFESSOR_NAME_X 10
#define PROFESSOR_NAME_Y 8
#define DEPARTMENT_X 10
#define DEPARTMENT_Y 18
#define STATUS_CENTER_X 160           
#define STATUS_CENTER_Y 105           
#define TIME_X 10                     
#define TIME_Y 220
#define DATE_X 250                    
#define DATE_Y 220

// === SIMPLIFIED COLOR SCHEME ===
// Navy Blue & Gold Theme - Display-specific values (working colors)
#define NAVY_BLUE        0x001F       // Main navy blue
#define NAVY_DARK        0x000B       // Darker navy
#define GOLD_BRIGHT      0xFE60       // Bright gold

// Basic Colors (display-specific - inverted for this hardware)
#define COLOR_WHITE      0x0000       // Displays as white (inverted)
#define COLOR_BLACK      0xFFFF       // Displays as black (inverted)
#define COLOR_GRAY_LIGHT 0x7BEF       // Light gray

// Status Colors with Simple Backgrounds (display-specific)
#define COLOR_SUCCESS    0xF81F       // Displays as green
#define COLOR_SUCCESS_BG 0x0E60       // Light green background
#define COLOR_ERROR      0x07FF       // Displays as red
#define COLOR_ERROR_BG   0x6000       // Light red background
#define COLOR_WARNING    GOLD_BRIGHT  // Gold
#define COLOR_BLUE       0xF800       // Displays as blue for acknowledge button
#define COLOR_BLUE_BG    0x3000       // Light blue background

// UI Assignments
#define COLOR_BACKGROUND COLOR_BLACK  // Black background
#define COLOR_TEXT       COLOR_WHITE  // White text
#define COLOR_ACCENT     GOLD_BRIGHT  // Gold accents
#define COLOR_PANEL      NAVY_BLUE    // Navy panels
#define COLOR_PANEL_DARK NAVY_DARK    // Dark navy

// === TIME CONFIGURATION ===
#define NTP_SERVER "pool.ntp.org"
#define TIME_ZONE_OFFSET 8               // GMT+8 for Philippines
#define NTP_UPDATE_INTERVAL 3600000      

// === SYSTEM TIMING CONSTANTS ===
#define MESSAGE_DISPLAY_TIMEOUT 30000        // Auto-clear messages after 30s
#define HEARTBEAT_INTERVAL 300000            // Send heartbeat every 5 minutes
#define STATUS_UPDATE_INTERVAL 10000         // Update system status every 10s
#define TIME_UPDATE_INTERVAL 5000            // Update time display every 5s
#define CONFIRMATION_DISPLAY_TIME 2000       // Show response confirmation for 2s
#define ANIMATION_INTERVAL 800               // Status indicator animation speed

// === SYSTEM LIMITS ===
#define MAX_MESSAGE_LENGTH 512               // Prevent buffer overflow
#define JSON_BUFFER_SIZE 1024                // For MQTT message construction
#define MAX_WIFI_RETRY_COUNT 10              // Maximum WiFi connection retries
#define MAX_MQTT_RETRY_COUNT 5               // Maximum MQTT connection retries

// === POWER MANAGEMENT ===
#define ENABLE_POWER_MANAGEMENT true
#define CPU_FREQ_NORMAL 240              
#define CPU_FREQ_POWER_SAVE 80           

// === DEBUG SETTINGS ===
#define ENABLE_SERIAL_DEBUG true
#define SERIAL_BAUD_RATE 115200
#define DEBUG_BLE true
#define DEBUG_MQTT true
#define DEBUG_DISPLAY false

// === SYSTEM VALIDATION ===
#ifndef FACULTY_ID
#error "FACULTY_ID must be defined"
#endif

#ifndef FACULTY_BEACON_MAC
#error "FACULTY_BEACON_MAC must be defined"
#endif

#ifndef WIFI_SSID
#error "WIFI_SSID must be defined"
#endif

#ifndef MQTT_SERVER
#error "MQTT_SERVER must be defined"
#endif

// === HELPER MACROS ===
#define DEBUG_PRINT(x) if(ENABLE_SERIAL_DEBUG) Serial.print(x)
#define DEBUG_PRINTLN(x) if(ENABLE_SERIAL_DEBUG) Serial.println(x)
#define DEBUG_PRINTF(format, ...) if(ENABLE_SERIAL_DEBUG) Serial.printf(format, ##__VA_ARGS__)

// === RUNTIME VALIDATION FUNCTION ===
inline bool validateConfiguration() {
  bool valid = true;
  
  // MAC address validation
  if (strlen(FACULTY_BEACON_MAC) != 17) {
    DEBUG_PRINTLN("ERROR: FACULTY_BEACON_MAC must be 17 characters");
    valid = false;
  }
  
  // WiFi validation
  if (strlen(WIFI_SSID) == 0) {
    DEBUG_PRINTLN("ERROR: WIFI_SSID cannot be empty");
    valid = false;
  }
  
  // UUID validation
  if (strlen(FACULTY_BEACON_UUID) != 36) {
    DEBUG_PRINTLN("ERROR: FACULTY_BEACON_UUID must be 36 characters");
    valid = false;
  }
  
  // MQTT validation
  if (strlen(MQTT_SERVER) == 0) {
    DEBUG_PRINTLN("ERROR: MQTT_SERVER cannot be empty");
    valid = false;
  }
  
  // Port validation
  if (MQTT_PORT < 1 || MQTT_PORT > 65535) {
    DEBUG_PRINTLN("ERROR: Invalid MQTT port");
    valid = false;
  }
  
  // GPIO validation
  if (BUTTON_A_PIN == BUTTON_B_PIN) {
    DEBUG_PRINTLN("ERROR: Button pins cannot be the same");
    valid = false;
  }
  
  // Display pin validation
  int displayPins[] = {TFT_CS, TFT_RST, TFT_DC};
  for (int i = 0; i < 3; i++) {
    if (displayPins[i] == BUTTON_A_PIN || displayPins[i] == BUTTON_B_PIN) {
      DEBUG_PRINTLN("ERROR: Display pin conflicts with button pin");
      valid = false;
    }
  }
  
  // BLE timing validation
  if (BLE_SCAN_DURATION_FULL >= BLE_SCAN_INTERVAL_SEARCHING/1000) {
    DEBUG_PRINTLN("WARNING: BLE scan duration too close to interval");
  }
  
  // Grace period validation
  if (BLE_GRACE_PERIOD_MS < BLE_RECONNECT_ATTEMPT_INTERVAL) {
    DEBUG_PRINTLN("ERROR: Grace period too short for reconnection attempts");
    valid = false;
  }
  
  if (valid) {
    DEBUG_PRINTLN("✅ Configuration validation passed");
  }
  
  return valid;
}

#endif // CONFIG_H