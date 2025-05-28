#include <WiFi.h>
#if MQTT_USE_TLS // Conditional include for WiFiClientSecure
#include <WiFiClientSecure.h>
WiFiClientSecure espClientSecure;
#else
WiFiClient espClient;             
#endif
#include <PubSubClient.h>  // MQTT client
#include <NimBLEDevice.h>  // Using NimBLE for scanning
// #include <NimBLEBeacon.h> // No longer needed for MAC address detection
#include <SPI.h>
#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789
#include <time.h>
#include "config.h"          // Include configuration file
#include <ArduinoJson.h>     // For JSON parsing
#include <esp_task_wdt.h>    // For Watchdog Timer

// Watchdog Configuration
#define WDT_TIMEOUT 15 // seconds

// Current Date/Time and User (Consider removing or using NTP only)
// const char* current_date_time = "2025-05-02 09:46:02"; // Hardcoded, NTP is better
const char* current_user = FACULTY_NAME;

// WiFi credentials
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// MQTT Broker settings
const char* mqtt_server = MQTT_SERVER;
const int mqtt_port = MQTT_USE_TLS ? MQTT_TLS_PORT : MQTT_PORT; // Use TLS or non-TLS port
char mqtt_topic_status[60]; // Increased size for safety
char mqtt_topic_requests[60];
char mqtt_topic_legacy_messages[50]; // Kept for receiving, but status publish will be specific
char mqtt_topic_consultation_response[100]; // New topic for consultation responses
char mqtt_client_id[50];

// BLE Target Service UUID to scan for - REMOVED for MAC address detection
// static NimBLEUUID facultyBeaconServiceUUID(SERVICE_UUID); 

// BLE Scanner variables
NimBLEScan* pBLEScan;
bool isFacultyPresent = false;
unsigned long lastBeaconSignalTime = 0;
unsigned long lastStatusPublishTime = 0;
bool bleScanActive = false;

// Button state management for manual override
#ifdef BUTTON_PIN
int buttonState = HIGH;             // Current reading from input pin
int lastButtonState = HIGH;         // Previous reading from input pin
unsigned long lastDebounceTime = 0; // Last time the output pin was toggled
unsigned long debounceDelay = 50;   // Debounce time; increase if bouncing is an issue
bool manualStatusOverrideActive = false;
bool currentManualStatus = false;     // The status set by manual override
#endif

// TFT Display pins for ST7789
#define TFT_CS    5
#define TFT_DC    21
#define TFT_RST   22
#define TFT_MOSI  23
#define TFT_SCLK  18

// Initialize the ST7789 display with hardware SPI
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST);

// Time settings
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 0;  // Adjust for your timezone
const int   daylightOffset_sec = 3600;

// Variables
#if MQTT_USE_TLS
PubSubClient mqttClient(espClientSecure); // Use secure client for TLS
#else
PubSubClient mqttClient(espClient); // Use standard client for non-TLS
#endif
char timeStringBuff[50];
char dateStringBuff[50];
String lastMessage = "";
unsigned long lastTimeUpdate = 0;

// National University Philippines Color Scheme (Copied from existing config.h for completeness in this snippet if needed)
#ifndef NU_BLUE // Protection if already defined by direct include of config.h
    #define NU_BLUE      0x0015      // Dark blue (navy) - Primary color
    #define NU_GOLD      0xFE60      // Gold/Yellow - Secondary color
    #define NU_DARKBLUE  0x000B      // Darker blue for contrasts
    #define NU_LIGHTGOLD 0xF710      // Lighter gold for highlights
    #define ST77XX_WHITE 0xFFFF      // White for text (assuming ST77XX_WHITE is TFT_WHITE)
    #define ST77XX_BLACK 0x0000      // Black for backgrounds (assuming ST77XX_BLACK is TFT_BLACK)
    #define ST77XX_YELLOW 0xFFE0     // A common yellow
    #define ST77XX_RED    0xF800     // A common red
#endif


// Colors for the UI (referencing config.h defines)
#define COLOR_BACKGROUND     TFT_BG
#define COLOR_TEXT           TFT_TEXT
#define COLOR_HEADER         TFT_HEADER
#define COLOR_MESSAGE_BG     TFT_BG // Or a specific message background color
#define COLOR_STATUS_GOOD    NU_GOLD // Or specific status good color
#define COLOR_STATUS_WARNING ST77XX_YELLOW // Example
#define COLOR_STATUS_ERROR   ST77XX_RED    // Example
#define COLOR_ACCENT         TFT_ACCENT
#define COLOR_HIGHLIGHT      TFT_HIGHLIGHT


// UI Layout constants - No gaps
#define HEADER_HEIGHT 40
#define STATUS_HEIGHT 20
#define MESSAGE_AREA_TOP HEADER_HEIGHT        // No gap after header
#define MESSAGE_TITLE_HEIGHT 30
#define MESSAGE_TEXT_TOP (MESSAGE_AREA_TOP + MESSAGE_TITLE_HEIGHT)

// Gold accent width
#define ACCENT_WIDTH 5

// BLE Advertised Device Callback for Scanner
class MyAdvertisedDeviceCallbacks: public NimBLEAdvertisedDeviceCallbacks {
    void onResult(NimBLEAdvertisedDevice* advertisedDevice) {
        Serial.print("Advertised Device found: ");
        Serial.print(advertisedDevice->toString().c_str());
        Serial.print(", Address: ");
        Serial.println(advertisedDevice->getAddress().toString().c_str());

        // Get the MAC address of the advertised device
        NimBLEAddress advertisedAddress = advertisedDevice->getAddress();
        
        // Create a NimBLEAddress object from the target MAC address string in config.h
        NimBLEAddress targetAddress(TARGET_BLE_MAC_ADDRESS);

        // Compare the advertised address with the target address
        if (advertisedAddress.equals(targetAddress)) {
            Serial.println("Found our target faculty BLE device by MAC address!");
            isFacultyPresent = true;
            lastBeaconSignalTime = millis(); // Update time of last sighting

            // Optional: Check RSSI against BLE_RSSI_THRESHOLD if you still want a proximity filter
            // if (advertisedDevice->getRSSI() < BLE_RSSI_THRESHOLD) {
            //     Serial.printf("Device RSSI %d is below threshold %d. Ignoring.\n", advertisedDevice->getRSSI(), BLE_RSSI_THRESHOLD);
            //     // Potentially set isFacultyPresent = false here or don't set it to true above if RSSI is a hard gate
            //     // return; 
            // }

            // Stop scanning once found to save power, will restart on next interval
            if(pBLEScan->isScanning()){
                pBLEScan->stop();
                bleScanActive = false; // Make sure this flag is managed correctly
            }
            digitalWrite(LED_PIN, HIGH); // Turn on LED or indicate presence (LED_PIN from config.h)
        } else {
            // Serial.println("Device MAC address does not match target."); // Uncomment for debugging if needed
        }
    }
};

// Function to process incoming messages and extract content from JSON if needed
String processMessage(const String& payload) { // Changed to const String&
  // Calculate an appropriate buffer size based on the payload length
  // ArduinoJson recommends 1.5x the size of the payload for most JSON documents
  const size_t capacity = JSON_OBJECT_SIZE(10) + payload.length() * 2;  // Allocate more space than needed to be safe
  DynamicJsonDocument doc(capacity); // Adjust size dynamically based on payload
  DeserializationError error = deserializeJson(doc, payload);

  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.f_str());
    return payload; // Return raw payload on error, or handle differently
  }

  // Try to extract known fields for different message types
  if (doc.containsKey("request_message")) {
    String requestMsg = doc["request_message"] | ""; // Get value or empty string if null
    String studentName = doc["student_name"] | "";
    String courseCode = doc["course_code"] | "";
    
    // Add validation for consultation_id to ensure it's a valid number
    long consultation_id_long = doc["consultation_id"] | -1;
    if (consultation_id_long > 0 && consultation_id_long < 1000000) { // Reasonable limits for an ID
      current_consultation_id = consultation_id_long;
    } else {
      Serial.println("Invalid consultation_id received");
      current_consultation_id = -1;
    }
    
    current_consultation_status = doc["consultation_status"] | "";
    // Add validation for status string
    if (current_consultation_status.length() > 0) {
      if (current_consultation_status != "pending" && 
          current_consultation_status != "accepted" && 
          current_consultation_status != "started" && 
          current_consultation_status != "completed" && 
          current_consultation_status != "cancelled") {
        Serial.println("Unknown consultation status: " + current_consultation_status);
        current_consultation_status = "unknown";
      }
    }
    
    String formattedMessage = "REQ ID: " + String(current_consultation_id) + " (Status: " + current_consultation_status + ")\n";
    if (!studentName.isEmpty()) { formattedMessage += "Student: " + studentName + "\n"; }
    if (!courseCode.isEmpty()) { formattedMessage += "Course: " + courseCode + "\n"; }
    formattedMessage += "Request: " + requestMsg;
    return formattedMessage;

  } else if (doc.containsKey("message")) {
    return doc["message"] | payload; // Return message field or raw payload if null
  } else if (doc.containsKey("status_update")) { // Example for another type of JSON message
    String statusUpdate = doc["status_update"] | "Status: N/A";
    return "System Update: " + statusUpdate;
  }
  
  return payload; // Fallback for unknown JSON structure or non-JSON messages
}

// Function to draw the continuous gold accent bar
void drawGoldAccent() {
  // Draw gold accent that spans the entire height except status bar
  tft.fillRect(0, 0, ACCENT_WIDTH, tft.height() - STATUS_HEIGHT, COLOR_ACCENT);
}

// Centralized UI update function that preserves the gold accent
void updateUIArea(int area, const String &message = "") {
  // Area types:
  // 0 = Full message area
  // 1 = Message title area only
  // 2 = Message content area only
  // 3 = Status bar only

  switch (area) {
    case 0: // Full message area
      tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP,
                  tft.width() - ACCENT_WIDTH,
                  tft.height() - MESSAGE_AREA_TOP - STATUS_HEIGHT,
                  COLOR_MESSAGE_BG);
      drawGoldAccent();
      if (message.length() > 0) {
        tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        tft.setTextSize(2);
        tft.setTextColor(NU_GOLD); // Example color for this message type
        tft.println(message);
      }
      break;

    case 1: // Message title area only
      tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP,
                  tft.width() - ACCENT_WIDTH,
                  MESSAGE_TITLE_HEIGHT,
                  COLOR_MESSAGE_BG);
      drawGoldAccent();
      if (message.length() > 0) {
        tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        tft.setTextSize(2);
        tft.setTextColor(NU_GOLD); // Example
        tft.println(message);
      }
      break;

    case 2: // Message content area only
      tft.fillRect(ACCENT_WIDTH, MESSAGE_TEXT_TOP,
                  tft.width() - ACCENT_WIDTH,
                  tft.height() - MESSAGE_TEXT_TOP - STATUS_HEIGHT,
                  COLOR_MESSAGE_BG);
      drawGoldAccent();
      break;

    case 3: // Status bar only
      displaySystemStatus(message);
      break;
  }
}

void testScreen() {
  tft.fillScreen(COLOR_BACKGROUND); // Use defined background
  delay(500);
  int sectionHeight = tft.height() / 3;
  tft.fillRect(0, 0, tft.width(), sectionHeight, NU_DARKBLUE);
  tft.fillRect(0, sectionHeight, tft.width(), sectionHeight, NU_BLUE);
  tft.fillRect(0, 2*sectionHeight, tft.width(), sectionHeight, NU_GOLD);
  drawGoldAccent();
  tft.setTextColor(TFT_TEXT); // Use defined text color
  tft.setTextSize(2);
  tft.setCursor(ACCENT_WIDTH + 5, 10);
  tft.println("National University");
  tft.setCursor(ACCENT_WIDTH + 5, sectionHeight + 10);
  tft.println("Philippines");
  tft.setTextColor(NU_DARKBLUE); // Contrasting text color
  tft.setCursor(ACCENT_WIDTH + 5, 2*sectionHeight + 10);
  tft.println("Professor's Desk Unit");
  delay(3000);
  tft.fillScreen(COLOR_BACKGROUND);
}

void updateTimeDisplay() {
  struct tm timeinfo;
  tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER);
  if(!getLocalTime(&timeinfo)){
    Serial.println("Failed to obtain time via NTP");
    // Fallback to a static or last known time if needed, or just show "Time N/A"
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(2);
    tft.setCursor(ACCENT_WIDTH + 5, 10);
    tft.print("Time N/A");
    drawGoldAccent();
    return;
  }
  strftime(timeStringBuff, sizeof(timeStringBuff), "%H:%M:%S", &timeinfo);
  strftime(dateStringBuff, sizeof(dateStringBuff), "%Y-%m-%d", &timeinfo);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(2);
  tft.setCursor(ACCENT_WIDTH + 5, 10);
  tft.print(timeStringBuff);
  int16_t x1, y1; uint16_t w, h;
  tft.getTextBounds(dateStringBuff, 0, 0, &x1, &y1, &w, &h);
  tft.setCursor(tft.width() - w - 10, 10);
  tft.print(dateStringBuff);
  drawGoldAccent();
}

void displayMessage(String message) {
  updateUIArea(0); // Clear full message area
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 5);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(2);
  tft.println("New Message:");
  tft.drawFastHLine(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + MESSAGE_TITLE_HEIGHT - 5, tft.width() - ACCENT_WIDTH - 10, COLOR_ACCENT);
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_TEXT_TOP);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(2);
  int16_t x1, y1; uint16_t w, h;
  int maxWidth = tft.width() - ACCENT_WIDTH - 10;
  String line = "";
  int yPos = MESSAGE_TEXT_TOP;
  for (int i = 0; i < message.length(); i++) {
    char c = message.charAt(i);
    line += c;
    tft.getTextBounds(line, 0, 0, &x1, &y1, &w, &h);
    if (w > maxWidth || c == '\n') {
      if (w > maxWidth && c != '\n') line = line.substring(0, line.length() - 1);
      tft.setCursor(ACCENT_WIDTH + 5, yPos); tft.println(line);
      yPos += h + 2;
      line = (w > maxWidth && c != '\n') ? String(c) : "";
    }
  }
  if (line.length() > 0) { tft.setCursor(ACCENT_WIDTH + 5, yPos); tft.println(line); }
  lastMessage = message;
}

void displaySystemStatus(String status) {
  tft.fillRect(0, tft.height() - STATUS_HEIGHT, tft.width(), STATUS_HEIGHT, NU_DARKBLUE); // Status bar background
  tft.setCursor(ACCENT_WIDTH + 5, tft.height() - STATUS_HEIGHT + 5);
  tft.setTextColor(COLOR_STATUS_GOOD); // Example status color
  tft.setTextSize(1);
  tft.println(status);
  tft.drawFastHLine(0, tft.height() - STATUS_HEIGHT, tft.width(), COLOR_ACCENT);
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived ["); Serial.print(topic); Serial.print("] ");
  String messageContent = ""; // Use String to build content
  for (int i = 0; i < length; i++) { messageContent += (char)payload[i]; }
  Serial.println(messageContent);
  // Serial.println("Message details:"); Serial.print("Topic: "); Serial.println(topic);
  // Serial.print("Length: "); Serial.println(length); Serial.print("Content: "); Serial.println(messageContent);

  // It's good to check the topic first if certain topics are not expected to be JSON
  if (strcmp(topic, MQTT_TOPIC_NOTIFICATIONS) == 0 && messageContent.indexOf("ping") >= 0) {
    Serial.println("Received system ping, no need to display or parse as JSON");
    return;
  }

  // Now, process the message content (which might be JSON)
  String displayableMessage = processMessage(messageContent);
  
  displayMessage(displayableMessage); // displayMessage should be able to handle formatted strings
  displaySystemStatus("New message received");
  for (int i = 0; i < 3; i++) {
    tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_ACCENT); delay(100);
    tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER); delay(100);
  }
  updateTimeDisplay();
}

void drawUIFramework() {
  tft.fillScreen(COLOR_BACKGROUND);
  tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER);
  tft.fillRect(0, tft.height() - STATUS_HEIGHT, tft.width(), STATUS_HEIGHT, NU_DARKBLUE);
  tft.drawFastHLine(0, tft.height() - STATUS_HEIGHT, tft.width(), COLOR_ACCENT);
  drawGoldAccent();
}

void setup_wifi() {
  updateUIArea(0); // Clear message area
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
  tft.setTextColor(COLOR_TEXT); tft.setTextSize(2); tft.println("Connecting to WiFi");
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 40);
  tft.setTextSize(1); tft.println(ssid);
  delay(10); Serial.println(); Serial.print("Connecting to "); Serial.println(ssid);
  WiFi.begin(ssid, password);
  int dots = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
    tft.fillRect(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 60, tft.width() - ACCENT_WIDTH - 10, 20, COLOR_BACKGROUND);
    tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 60); tft.setTextColor(COLOR_TEXT); tft.print("Connecting");
    for (int i = 0; i < 6; i++) {
      if (i < dots) { tft.setTextColor((i % 2 == 0) ? NU_GOLD : NU_LIGHTGOLD); tft.print("."); }
      else { tft.print(" "); }
    }
    dots = (dots + 1) % 7;
  }
  Serial.println(""); Serial.println("WiFi connected"); Serial.print("IP address: "); Serial.println(WiFi.localIP());
  updateUIArea(0); // Clear message area
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10); tft.setTextSize(2); tft.setTextColor(NU_GOLD); tft.println("WiFi Connected");
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 50); tft.setTextSize(1); tft.setTextColor(COLOR_TEXT);
  tft.print("SSID: "); tft.println(ssid);
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 70); tft.print("IP: "); tft.println(WiFi.localIP().toString());
  displaySystemStatus("WiFi connected successfully");
  delay(2000);
}

void reconnect() {
  int attempts = 0;
  while (!mqttClient.connected() && attempts < 5) {
    Serial.print("Attempting MQTT connection..."); displaySystemStatus("Connecting to MQTT...");
    String clientId = mqtt_client_id; clientId += String(random(0xffff), HEX);

    #if MQTT_USE_TLS
    // Load certificates
    // Note: For ESP32, setCACert, setCertificate, setPrivateKey are the correct methods
    // For some older examples you might see setCACertificate etc.
    try {
      espClientSecure.setCACert(mqtt_ca_cert);
      if (mqtt_client_cert && mqtt_client_cert[0] != '\0') {
        espClientSecure.setCertificate(mqtt_client_cert); // Client certificate
      }
      if (mqtt_client_key && mqtt_client_key[0] != '\0') {
        espClientSecure.setPrivateKey(mqtt_client_key);   // Client private key
      }
      Serial.println("MQTT TLS: Certificates loaded.");
    } catch (const std::exception& e) {
      Serial.print("TLS certificate error: ");
      Serial.println(e.what());
      displaySystemStatus("TLS certificate error");
      delay(2000);
      displaySystemStatus("Will retry with fallback");
      return; // Exit this attempt, will retry
    } catch (...) {
      Serial.println("Unknown TLS certificate error");
      displaySystemStatus("Unknown TLS error");
      delay(2000);
      displaySystemStatus("Will retry with fallback");
      return; // Exit this attempt, will retry
    }
    #endif

    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("connected"); displaySystemStatus("MQTT connected");
      mqttClient.subscribe(mqtt_topic_requests);
      mqttClient.subscribe(mqtt_topic_legacy_messages);
      mqttClient.subscribe(MQTT_TOPIC_NOTIFICATIONS);
      Serial.println("Subscribed to topics:"); Serial.println(mqtt_topic_requests);
      Serial.println(mqtt_topic_legacy_messages); Serial.println(MQTT_TOPIC_NOTIFICATIONS);
      updateUIArea(1, "MQTT Connected"); // Show in title area
      delay(1500);
      updateUIArea(1); // Clear title area
    } else {
      Serial.print("failed, rc="); Serial.print(mqttClient.state()); Serial.println(" try again in 5 seconds");
      displaySystemStatus("MQTT connection failed. Retrying...");
      
      // Handle specific error codes
      int errorCode = mqttClient.state();
      String errorMsg = "Error: ";
      switch (errorCode) {
        case -1: errorMsg += "Timeout"; break;
        case -2: errorMsg += "Failed"; break;
        case -3: errorMsg += "Connection Lost"; break;
        case -4: errorMsg += "Connection Failed"; break;
        case -5: errorMsg += "Bad Protocol"; break;
        default: errorMsg += String(errorCode);
      }
      displaySystemStatus(errorMsg);
      
      delay(5000); attempts++;
    }
  }
  if (!mqttClient.connected()) { displaySystemStatus("Failed to connect to MQTT after multiple attempts"); }
}

void drawNULogo(int centerX, int centerY, int size) {
  int circleSize = size; int innerSize1 = size * 0.8;
  int innerSize2 = size * 0.6; int innerSize3 = size * 0.4;
  tft.fillCircle(centerX, centerY, circleSize, NU_GOLD);
  tft.fillCircle(centerX, centerY, innerSize1, NU_DARKBLUE);
  tft.fillCircle(centerX, centerY, innerSize2, TFT_WHITE); // Use TFT_WHITE from config
  tft.fillCircle(centerX, centerY, innerSize3, NU_BLUE);
  tft.setTextColor(NU_GOLD); tft.setTextSize(1);
  tft.setCursor(centerX - 5, centerY - 3); tft.print("NU");
}

void setup() {
  Serial.begin(115200);
  Serial.println("ConsultEase Faculty Desk Unit Starting (Scanner Mode)...");
  
  // Initialize Watchdog Timer
  Serial.printf("Initializing WDT with timeout of %d seconds\n", WDT_TIMEOUT);
  esp_task_wdt_init(WDT_TIMEOUT, true); // Enable panic so ESP restarts
  esp_task_wdt_add(NULL); // Add current task (main loop) to WDT
  
  pinMode(LED_PIN, OUTPUT); // LED_PIN from config.h
  digitalWrite(LED_PIN, LOW);

#ifdef BUTTON_PIN
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.printf("Manual override button initialized on pin %d\n", BUTTON_PIN);
#endif

  sprintf(mqtt_topic_status, MQTT_TOPIC_STATUS, FACULTY_ID);
  sprintf(mqtt_topic_requests, MQTT_TOPIC_REQUESTS, FACULTY_ID);
  strcpy(mqtt_topic_legacy_messages, MQTT_LEGACY_MESSAGES);
  sprintf(mqtt_topic_consultation_response, "consultease/faculty/%d/consultation/response", FACULTY_ID); // Initialize new topic
  sprintf(mqtt_client_id, "DeskUnitScanner_%s", FACULTY_NAME); // Use FACULTY_NAME from config.h
  Serial.println("MQTT topics initialized for scanner mode.");

  // Initialize display with error handling
  boolean displayInitSuccess = false;
  int displayRetryCount = 0;
  
  while (!displayInitSuccess && displayRetryCount < 3) {
    try {
      SPI.begin();
      tft.init(240, 320);
      displayInitSuccess = true;
      Serial.println("Display initialized successfully");
    } catch (const std::exception& e) {
      displayRetryCount++;
      Serial.print("Display initialization error (attempt "); 
      Serial.print(displayRetryCount);
      Serial.print("/3): ");
      Serial.println(e.what());
      delay(1000); // Wait before retry
    } catch (...) {
      displayRetryCount++;
      Serial.print("Unknown display error (attempt ");
      Serial.print(displayRetryCount);
      Serial.println("/3)");
      delay(1000); // Wait before retry
    }
  }
  
  if (!displayInitSuccess) {
    Serial.println("CRITICAL: Display failed to initialize after multiple attempts");
    // Continue without display, system will show errors on serial
  }
  
  tft.setRotation(TFT_ROTATION); // Use TFT_ROTATION from config.h
  testScreen();
  drawUIFramework();
  updateTimeDisplay();
  displaySystemStatus("Initializing system...");
  
  int centerX = tft.width() / 2; int logoY = MESSAGE_AREA_TOP + 60;
  drawGoldAccent();
  drawNULogo(centerX, logoY, 35);
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10); tft.setTextColor(NU_GOLD); tft.setTextSize(2);
  tft.println("Welcome, " + String(current_user)); // current_user is FACULTY_NAME
  tft.setCursor(ACCENT_WIDTH + 5, logoY + 50); tft.setTextSize(1.5); tft.setTextColor(TFT_TEXT);
  tft.println("National University");
  tft.setCursor(ACCENT_WIDTH + 5, logoY + 70); tft.println("Professor's Desk Unit");
  tft.setCursor(ACCENT_WIDTH + 5, logoY + 100); tft.setTextColor(NU_GOLD);
  tft.println("System Initializing...");
  delay(2000);

  setup_wifi();
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(callback);

  #if MQTT_USE_TLS
  // Optional: If your broker requires specific time for TLS, ensure NTP is synced first.
  // However, PubSubClient and WiFiClientSecure usually handle this fine without explicit pre-NTP sync for cert validation.
  Serial.println("MQTT configured for TLS connection.");
  #else
  Serial.println("MQTT configured for non-TLS connection.");
  #endif

  NimBLEDevice::init("");
  pBLEScan = NimBLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100); 
  pBLEScan->setWindow(99);  
  Serial.println("BLE Scanner initialized.");
  displaySystemStatus("Scanning for beacon...");
  lastBeaconSignalTime = millis() - BLE_CONNECTION_TIMEOUT - 1000; // Initialize to disconnected state
}

void publishStatus(bool isPresent, bool isManual) {
    // Use static memory allocation for JSON document to avoid heap fragmentation
    StaticJsonDocument<128> doc; // Small fixed-size document uses stack memory
    
    // Add data to document
    doc["status"] = isPresent;
    doc["type"] = isManual ? "manual" : "ble";
    
    // Serialize JSON directly to a buffer
    char jsonBuffer[128]; // Fixed buffer size
    size_t jsonSize = serializeJson(doc, jsonBuffer, sizeof(jsonBuffer));
    
    // Check if serialization was successful
    if (jsonSize > 0 && jsonSize < sizeof(jsonBuffer)) {
        if (mqttClient.connected()) {
            mqttClient.publish(mqtt_topic_status, jsonBuffer);
            Serial.print("Published to "); Serial.print(mqtt_topic_status); Serial.print(": "); Serial.println(jsonBuffer);
        }
        lastStatusPublishTime = millis();
        digitalWrite(LED_PIN, isPresent ? HIGH : LOW); 
        // Update display based on the actual status being published
        String displayStatusStr = String(isManual ? "Status (Manual): " : "Status (BLE): ") + (isPresent ? "Available" : "Unavailable");
        displaySystemStatus(displayStatusStr);
    } else {
        Serial.println("Error serializing JSON or buffer too small");
    }
}

#ifdef BUTTON_PIN
void handleButtonPress() {
  int reading = digitalRead(BUTTON_PIN);

  if (reading != lastButtonState) {
    lastDebounceTime = millis(); // reset the debouncing timer
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;
      if (buttonState == LOW) { // Button pressed (assuming active LOW due to INPUT_PULLUP)
        Serial.println("Button Pressed!");
        manualStatusOverrideActive = !manualStatusOverrideActive; // Toggle override mode

        if (manualStatusOverrideActive) {
          // When activating manual override, set status opposite to current BLE or default to available
          currentManualStatus = !isFacultyPresent; // Or a fixed state like true (available)
          Serial.print("Manual override ACTIVATED. Status set to: "); Serial.println(currentManualStatus ? "Available" : "Unavailable");
        } else {
          Serial.println("Manual override DEACTIVATED. Reverting to BLE status.");
          // When deactivating, the next BLE check or timeout will determine status.
          // We can force an immediate publish of current BLE status.
        }
        // Publish the new status immediately
        if (manualStatusOverrideActive) {
            publishStatus(currentManualStatus, true);
        } else {
            // When deactivating, publish the current BLE-determined status
            publishStatus(isFacultyPresent, false);
        }
      }
    }
  }
  lastButtonState = reading;
}
#endif

#if defined(ACCEPT_BUTTON_PIN) && defined(REJECT_BUTTON_PIN)
// Debounce variables for Accept button
int acceptButtonState = HIGH;
int lastAcceptButtonState = HIGH;
unsigned long lastAcceptDebounceTime = 0;

// Debounce variables for Reject button
int rejectButtonState = HIGH;
int lastRejectButtonState = HIGH;
unsigned long lastRejectDebounceTime = 0;

void handleConsultationActionButtons() {
  // Read Accept button
  int acceptReading = digitalRead(ACCEPT_BUTTON_PIN);
  if (acceptReading != lastAcceptButtonState) {
    lastAcceptDebounceTime = millis();
  }
  if ((millis() - lastAcceptDebounceTime) > debounceDelay) {
    if (acceptReading != acceptButtonState) {
      acceptButtonState = acceptReading;
      if (acceptButtonState == LOW) { // Button pressed
        Serial.println("Contextual Action Button (Accept/Start/End) Pressed!");
        if (current_consultation_id != -1 && current_consultation_id > 0 && !current_consultation_status.isEmpty()) {
          String action = "";
          String displayMsgAction = "";

          if (current_consultation_status == "pending") {
            action = "accepted";
            displayMsgAction = "ACCEPTED";
          } else if (current_consultation_status == "accepted") {
            action = "started";
            displayMsgAction = "STARTED";
          } else if (current_consultation_status == "started") {
            action = "completed";
            displayMsgAction = "COMPLETED";
          } else {
            Serial.println("No valid action for current consultation status ('" + current_consultation_status + "') with accept/start/end button.");
            displayMessage("No action for status: " + current_consultation_status);
            return; // Do nothing if no valid action
          }

          String payload = "{\"action\": \"" + action + "\", \"consultation_id\": " + String(current_consultation_id) + "}";
          mqttClient.publish(mqtt_topic_consultation_response, payload.c_str());
          Serial.print("Published to "); Serial.print(mqtt_topic_consultation_response); Serial.print(": "); Serial.println(payload);
          displayMessage("Request ID " + String(current_consultation_id) + " " + displayMsgAction);
          current_consultation_id = -1; // Reset after action
          current_consultation_status = "";
        } else {
          Serial.println("No active/valid consultation to act upon with accept/start/end button.");
          displayMessage("No request selected or status unclear.");
        }
      }
    }
  }
  lastAcceptButtonState = acceptReading;

  // Read Reject/Cancel button (add same validation)
  int rejectReading = digitalRead(REJECT_BUTTON_PIN);
  if (rejectReading != lastRejectButtonState) {
    lastRejectDebounceTime = millis();
  }
  if ((millis() - lastRejectDebounceTime) > debounceDelay) {
    if (rejectReading != rejectButtonState) {
      rejectButtonState = rejectReading;
      if (rejectButtonState == LOW) { // Button pressed
        Serial.println("Contextual Action Button (Reject/Cancel) Pressed!");
        if (current_consultation_id != -1 && current_consultation_id > 0 && !current_consultation_status.isEmpty()) {
          String action = "";
          String displayMsgAction = "";

          if (current_consultation_status == "pending") {
            action = "rejected_by_faculty";
            displayMsgAction = "REJECTED";
          } else if (current_consultation_status == "accepted" || current_consultation_status == "started") {
            action = "cancelled_by_faculty";
            displayMsgAction = "CANCELLED";
          } else {
            Serial.println("No valid action for current consultation status ('" + current_consultation_status + "') with reject/cancel button.");
            displayMessage("No action for status: " + current_consultation_status);
            return; // Do nothing if no valid action
          }
          
          String payload = "{\"action\": \"" + action + "\", \"consultation_id\": " + String(current_consultation_id) + "}";
          mqttClient.publish(mqtt_topic_consultation_response, payload.c_str());
          Serial.print("Published to "); Serial.print(mqtt_topic_consultation_response); Serial.print(": "); Serial.println(payload);
          displayMessage("Request ID " + String(current_consultation_id) + " " + displayMsgAction);
          current_consultation_id = -1; // Reset after action
          current_consultation_status = "";
        } else {
          Serial.println("No active/valid consultation to act upon with reject/cancel button.");
          displayMessage("No request selected or status unclear.");
        }
      }
    }
  }
  lastRejectButtonState = rejectReading;
}
#endif

void loop() {
  // Feed the Watchdog at the beginning of every loop iteration
  esp_task_wdt_reset();

  if (!mqttClient.connected()) { reconnect(); }
  mqttClient.loop();

#ifdef BUTTON_PIN
  handleButtonPress();
#endif

#if defined(ACCEPT_BUTTON_PIN) && defined(REJECT_BUTTON_PIN)
  handleConsultationActionButtons();
#endif

  unsigned long currentMillis = millis();
  bool finalStatusToPublish = isFacultyPresent;
  bool publishTypeIsManual = false;

  if (manualStatusOverrideActive) {
    finalStatusToPublish = currentManualStatus;
    publishTypeIsManual = true;
    // If manual override is active, we don't care about BLE scan results for publishing status,
    // but we might still want to log BLE presence/absence or update lastBeaconSignalTime if needed for other logic.
    // For simplicity here, manual override takes full precedence for published status.
  } else {
    // BLE Presence Logic (only if not manually overridden)
    if (!pBLEScan->isScanning()) {
      if (!isFacultyPresent || (currentMillis - lastBeaconSignalTime > BLE_SCAN_INTERVAL)) {
        Serial.println("Starting BLE scan...");
        
        // Clear results from previous scan to prevent memory leaks
        if (pBLEScan->getResults().getCount() > 0) {
          Serial.println("Clearing previous scan results to prevent memory leaks");
          pBLEScan->clearResults();
        }
        
        bleScanActive = true; 
        pBLEScan->start(BLE_SCAN_DURATION, nullptr, false); 
      }
    }
    if (isFacultyPresent && (currentMillis - lastBeaconSignalTime > BLE_CONNECTION_TIMEOUT)) {
      Serial.println("Beacon signal lost (timeout).");
      isFacultyPresent = false; // This will be picked up by finalStatusToPublish if not overridden
      // statusChanged flag is effectively handled by comparing finalStatusToPublish with previous published state implicitly
    }
    finalStatusToPublish = isFacultyPresent;
    publishTypeIsManual = false;
  }

  // Publish status if it changed OR if it's time for a periodic update
  // To detect change, we need to store the last published status values
  static bool lastPublishedStatusVal = false;
  static bool lastPublishWasManual = false;
  bool significantChange = (finalStatusToPublish != lastPublishedStatusVal) || (publishTypeIsManual != lastPublishWasManual);

  if (significantChange || (currentMillis - lastStatusPublishTime > 300000)) { // 300000ms = 5 minutes for periodic
      publishStatus(finalStatusToPublish, publishTypeIsManual);
      lastPublishedStatusVal = finalStatusToPublish;
      lastPublishWasManual = publishTypeIsManual;
  }

  // Ensure LED state matches the *actual* faculty presence (isFacultyPresent), 
  // not necessarily the manually overridden published status, or choose based on preference.
  // For now, let LED reflect the published status for consistency.
  digitalWrite(LED_PIN, finalStatusToPublish ? HIGH : LOW);

  // Update time display periodically
  static unsigned long lastDisplayTimeUpdate = 0;
  if (currentMillis - lastDisplayTimeUpdate > 1000) { // Update time every second
    updateTimeDisplay();
    lastDisplayTimeUpdate = currentMillis;
  }
}
