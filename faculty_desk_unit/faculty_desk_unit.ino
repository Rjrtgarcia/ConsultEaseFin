#include <WiFi.h>
#include <PubSubClient.h>  // MQTT client
#include <NimBLEDevice.h>  // Using NimBLE for scanning
#include <SPI.h>
#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_ST7789.h> // Hardware-specific library for ST7789
#include <time.h>
#include "config.h"          // Include configuration file

// Current Date/Time and User (Consider removing or using NTP only)
// const char* current_date_time = "2025-05-02 09:46:02"; // Hardcoded, NTP is better
const char* current_user = FACULTY_NAME;

// WiFi credentials
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// MQTT Broker settings
const char* mqtt_server = MQTT_SERVER;
const int mqtt_port = MQTT_PORT;
char mqtt_topic_status[60]; // Increased size for safety
char mqtt_topic_requests[60];
char mqtt_topic_legacy_messages[50]; // Kept for receiving, but status publish will be specific
char mqtt_client_id[50];

// BLE Target Service UUID to scan for (from faculty's beacon)
static NimBLEUUID facultyBeaconServiceUUID(SERVICE_UUID);

// BLE Scanner variables
NimBLEScan* pBLEScan;
bool isFacultyPresent = false;
unsigned long lastBeaconSignalTime = 0;
unsigned long lastStatusPublishTime = 0;
bool bleScanActive = false;

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
WiFiClient espClient;
PubSubClient mqttClient(espClient);
char timeStringBuff[50];
char dateStringBuff[50];
String lastMessage = "";
unsigned long lastTimeUpdate = 0;

// National University Philippines Color Scheme
#define NU_BLUE      0x0015      // Dark blue (navy) - Primary color
#define NU_GOLD      0xFE60      // Gold/Yellow - Secondary color
#define NU_DARKBLUE  0x000B      // Darker blue for contrasts
#define NU_LIGHTGOLD 0xF710      // Lighter gold for highlights
#define ST77XX_WHITE 0xFFFF      // White for text
#define ST77XX_BLACK 0x0000      // Black for backgrounds

// Colors for the UI
#define COLOR_BACKGROUND     NU_BLUE         // Changed to blue as primary color
#define COLOR_TEXT           ST77XX_WHITE
#define COLOR_HEADER         NU_DARKBLUE
#define COLOR_MESSAGE_BG     NU_BLUE
#define COLOR_STATUS_GOOD    NU_GOLD
#define COLOR_STATUS_WARNING ST77XX_YELLOW
#define COLOR_STATUS_ERROR   ST77XX_RED
#define COLOR_ACCENT         NU_GOLD
#define COLOR_HIGHLIGHT      NU_LIGHTGOLD

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
        Serial.println(advertisedDevice->toString().c_str());
        // Check if the advertised device has the service UUID we are looking for
        if (advertisedDevice->isAdvertisingService(facultyBeaconServiceUUID)) {
            Serial.println("Found our faculty beacon!");
            isFacultyPresent = true;
            lastBeaconSignalTime = millis(); // Update time of last sighting
            // Stop scanning once found to save power, will restart on next interval
            if(pBLEScan->isScanning()){
                pBLEScan->stop();
                bleScanActive = false;
            }
            digitalWrite(LED_PIN, HIGH); // Turn on LED or indicate presence
        } else {
            // Optional: Handle other devices or just ignore
        }
    }
};

// Function to process incoming messages and extract content from JSON if needed
String processMessage(String message) {
  if (message.startsWith("{")) {
    int messageStart = message.indexOf("\"message\":\"");
    if (messageStart > 0) {
      messageStart += 11;
      int messageEnd = message.indexOf("\"", messageStart);
      if (messageEnd > messageStart) {
        String extractedMessage = message.substring(messageStart, messageEnd);
        extractedMessage.replace("\\\"", "\"");
        extractedMessage.replace("\\n", "\n");
        return extractedMessage;
      }
    }
    messageStart = message.indexOf("\"request_message\":\"");
    if (messageStart > 0) {
      messageStart += 18; 
      int messageEnd = message.indexOf("\"", messageStart);
      if (messageEnd > messageStart) {
        String extractedMessage = message.substring(messageStart, messageEnd);
        extractedMessage.replace("\\\"", "\"");
        extractedMessage.replace("\\n", "\n");
        String studentName = "";
        int studentStart = message.indexOf("\"student_name\":\"");
        if (studentStart > 0) { studentStart += 16; int studentEnd = message.indexOf("\"", studentStart); if (studentEnd > studentStart) { studentName = message.substring(studentStart, studentEnd); } }
        String courseCode = "";
        int courseStart = message.indexOf("\"course_code\":\"");
        if (courseStart > 0) { courseStart += 14; int courseEnd = message.indexOf("\"", courseStart); if (courseEnd > courseStart) { courseCode = message.substring(courseStart, courseEnd); } }
        String formattedMessage = "";
        if (studentName != "") { formattedMessage += "Student: " + studentName + "\n"; }
        if (courseCode != "") { formattedMessage += "Course: " + courseCode + "\n"; }
        formattedMessage += "Request: " + extractedMessage;
        return formattedMessage;
      }
    }
    return message; // Return raw JSON if specific fields not found
  }
  return message;
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
      // Clear the message area but preserve gold accent
      tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP,
                  tft.width() - ACCENT_WIDTH,
                  tft.height() - MESSAGE_AREA_TOP - STATUS_HEIGHT,
                  COLOR_MESSAGE_BG);

      // Ensure gold accent is intact
      drawGoldAccent();

      // If message provided, display it
      if (message.length() > 0) {
        tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        tft.setTextSize(2);
        tft.setTextColor(NU_GOLD);
        tft.println(message);
      }
      break;

    case 1: // Message title area only
      // Clear just the title area
      tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP,
                  tft.width() - ACCENT_WIDTH,
                  MESSAGE_TITLE_HEIGHT,
                  COLOR_MESSAGE_BG);

      // Ensure gold accent is intact
      drawGoldAccent();

      // If message provided, display it as title
      if (message.length() > 0) {
        tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        tft.setTextSize(2);
        tft.setTextColor(NU_GOLD);
        tft.println(message);
      }
      break;

    case 2: // Message content area only
      // Clear just the content area below title
      tft.fillRect(ACCENT_WIDTH, MESSAGE_TEXT_TOP,
                  tft.width() - ACCENT_WIDTH,
                  tft.height() - MESSAGE_TEXT_TOP - STATUS_HEIGHT,
                  COLOR_MESSAGE_BG);

      // Ensure gold accent is intact
      drawGoldAccent();
      break;

    case 3: // Status bar only
      // Update status bar
      displaySystemStatus(message);
      break;
  }
}

// Function to test the full display
void testScreen() {
  // Test pattern to verify the display is working properly
  tft.fillScreen(NU_BLUE);
  delay(500);

  // Draw National University Philippines colors for test
  int sectionHeight = tft.height() / 3;

  // Draw sections with no gaps
  tft.fillRect(0, 0, tft.width(), sectionHeight, NU_DARKBLUE);
  tft.fillRect(0, sectionHeight, tft.width(), sectionHeight, NU_BLUE);
  tft.fillRect(0, 2*sectionHeight, tft.width(), sectionHeight, NU_GOLD);

  // Add continuous gold accent line at left
  drawGoldAccent();

  // Display text
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);

  tft.setCursor(ACCENT_WIDTH + 5, 10);
  tft.println("National University");

  tft.setCursor(ACCENT_WIDTH + 5, sectionHeight + 10);
  tft.println("Philippines");

  tft.setTextColor(NU_DARKBLUE);
  tft.setCursor(ACCENT_WIDTH + 5, 2*sectionHeight + 10);
  tft.println("Professor's Desk Unit");

  delay(3000);
  tft.fillScreen(NU_BLUE);
}

// Function to draw the header with time and date
void updateTimeDisplay() {
  struct tm timeinfo;

  // Clear only the header area, preserving the gold accent
  tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER);

  // Get the current time
  if(!getLocalTime(&timeinfo)){
    Serial.println("Failed to obtain time");

    // Use provided time if NTP fails
    // Parse the date and time from current_date_time string
    String dateTime = String(current_date_time);
    String date = dateTime.substring(0, 10);  // "2025-05-02"
    String time = dateTime.substring(11);     // "09:46:02"

    // Draw time on left
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(2);
    tft.setCursor(ACCENT_WIDTH + 5, 10);
    tft.print(time);

    // Draw date on right
    int16_t x1, y1;
    uint16_t w, h;
    tft.getTextBounds(date, 0, 0, &x1, &y1, &w, &h);
    tft.setCursor(tft.width() - w - 10, 10);
    tft.print(date);

    // Ensure gold accent is intact
    drawGoldAccent();
    return;
  }

  // Format time (HH:MM:SS)
  strftime(timeStringBuff, sizeof(timeStringBuff), "%H:%M:%S", &timeinfo);

  // Format date (YYYY-MM-DD)
  strftime(dateStringBuff, sizeof(dateStringBuff), "%Y-%m-%d", &timeinfo);

  // Draw time on left
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(2);
  tft.setCursor(ACCENT_WIDTH + 5, 10);
  tft.print(timeStringBuff);

  // Draw date on right
  int16_t x1, y1;
  uint16_t w, h;
  tft.getTextBounds(dateStringBuff, 0, 0, &x1, &y1, &w, &h);
  tft.setCursor(tft.width() - w - 10, 10);
  tft.print(dateStringBuff);

  // Ensure gold accent is intact
  drawGoldAccent();
}

// Function to display a new message
void displayMessage(String message) {
  // Use centralized UI update function to clear the full message area
  updateUIArea(0);

  // Display "New Message:" title with gold accent
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 5);
  tft.setTextColor(COLOR_ACCENT);  // Gold color for title
  tft.setTextSize(2);
  tft.println("New Message:");

  // Draw a gold divider line right after the title
  tft.drawFastHLine(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + MESSAGE_TITLE_HEIGHT - 5, tft.width() - ACCENT_WIDTH - 10, COLOR_ACCENT);

  // Display message text with word wrapping
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_TEXT_TOP);
  tft.setTextColor(COLOR_TEXT);  // White text for message
  tft.setTextSize(2);

  // Handle long messages with line wrapping
  int16_t x1, y1;
  uint16_t w, h;
  int maxWidth = tft.width() - ACCENT_WIDTH - 10;
  String line = "";
  int yPos = MESSAGE_TEXT_TOP;

  for (int i = 0; i < message.length(); i++) {
    char c = message.charAt(i);
    line += c;

    tft.getTextBounds(line, 0, 0, &x1, &y1, &w, &h);

    if (w > maxWidth || c == '\n') {
      // Remove the last character if it was due to width
      if (w > maxWidth && c != '\n')
        line = line.substring(0, line.length() - 1);

      tft.setCursor(ACCENT_WIDTH + 5, yPos);
      tft.println(line);

      yPos += h + 2;  // Reduced spacing for more compact layout
      line = (w > maxWidth && c != '\n') ? String(c) : "";
    }
  }

  // Print any remaining text
  if (line.length() > 0) {
    tft.setCursor(ACCENT_WIDTH + 5, yPos);
    tft.println(line);
  }

  lastMessage = message;
}

// Show system status on display
void displaySystemStatus(String status) {
  // Clear the status area at the bottom of the screen
  tft.fillRect(0, tft.height() - STATUS_HEIGHT, tft.width(), STATUS_HEIGHT, NU_DARKBLUE);

  // Display the status text
  tft.setCursor(ACCENT_WIDTH + 5, tft.height() - STATUS_HEIGHT + 5);
  tft.setTextColor(COLOR_STATUS_GOOD);
  tft.setTextSize(1);
  tft.println(status);

  // Draw a gold line above status bar
  tft.drawFastHLine(0, tft.height() - STATUS_HEIGHT, tft.width(), COLOR_ACCENT);
}

// MQTT callback with improved topic handling
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.println(message);

  // Enhanced debug output
  Serial.println("Message details:");
  Serial.print("Topic: ");
  Serial.println(topic);
  Serial.print("Length: ");
  Serial.println(length);
  Serial.print("Content: ");
  Serial.println(message);

  // Check if this is a system ping message (for keeping connection alive)
  if (strcmp(topic, MQTT_TOPIC_NOTIFICATIONS) == 0 && message.indexOf("ping") >= 0) {
    Serial.println("Received system ping, no need to display");
    return;
  }

  // Process the message based on format
  message = processMessage(message);

  // Display the message on TFT with visual notification
  displayMessage(message);
  displaySystemStatus("New message received");

  // Flash the screen briefly to draw attention to the new message
  for (int i = 0; i < 3; i++) {
    // Flash the header area
    tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_ACCENT);
    delay(100);
    tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER);
    delay(100);
  }

  // Restore the time display
  updateTimeDisplay();
}

// Draw the main UI framework - truly seamless design
void drawUIFramework() {
  // Fill entire screen with the NU blue color
  tft.fillScreen(COLOR_BACKGROUND);

  // Draw the header bar with darker blue - no gaps
  tft.fillRect(ACCENT_WIDTH, 0, tft.width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER);

  // Draw status bar area - seamless with main area
  tft.fillRect(0, tft.height() - STATUS_HEIGHT, tft.width(), STATUS_HEIGHT, NU_DARKBLUE);

  // Add thin gold accent line above status bar
  tft.drawFastHLine(0, tft.height() - STATUS_HEIGHT, tft.width(), COLOR_ACCENT);

  // Draw continuous gold accent at left
  drawGoldAccent();
}

void setup_wifi() {
  // Clear the main content area but preserve the gold accent bar
  tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP, tft.width() - ACCENT_WIDTH, tft.height() - MESSAGE_AREA_TOP - STATUS_HEIGHT, COLOR_BACKGROUND);

  // Ensure gold accent is intact
  drawGoldAccent();

  // Display connecting message
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(2);
  tft.println("Connecting to WiFi");

  // Add the SSID right beneath
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 40);
  tft.setTextSize(1);
  tft.println(ssid);

  // Connect to WiFi
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  // Animated connecting indicator with National University colors
  int dots = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");

    // Clear dot area but preserve gold accent
    tft.fillRect(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 60, tft.width() - ACCENT_WIDTH - 10, 20, COLOR_BACKGROUND);

    // Update dots animation with alternating colors
    tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 60);
    tft.setTextColor(COLOR_TEXT);
    tft.print("Connecting");

    for (int i = 0; i < 6; i++) {
      if (i < dots) {
        // Alternate between blue and gold dots
        tft.setTextColor((i % 2 == 0) ? NU_GOLD : NU_LIGHTGOLD);
        tft.print(".");
      } else {
        tft.print(" ");
      }
    }

    dots = (dots + 1) % 7;
  }

  // Connected - display connection details
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  // Clear the connecting message and show success - but preserve gold accent bar
  tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP, tft.width() - ACCENT_WIDTH, tft.height() - MESSAGE_AREA_TOP - STATUS_HEIGHT, COLOR_BACKGROUND);

  // Ensure gold accent is intact
  drawGoldAccent();

  // Show connected message
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
  tft.setTextSize(2);
  tft.setTextColor(NU_GOLD);
  tft.println("WiFi Connected");

  // Show network details
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 50);
  tft.setTextSize(1);
  tft.setTextColor(COLOR_TEXT);
  tft.print("SSID: ");
  tft.println(ssid);

  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 70);
  tft.print("IP: ");
  tft.println(WiFi.localIP().toString());

  // Update status bar
  displaySystemStatus("WiFi connected successfully");

  // Give time to read the info
  delay(2000);
}

void reconnect() {
  // Loop until we're reconnected to MQTT broker
  int attempts = 0;

  while (!mqttClient.connected() && attempts < 5) {
    Serial.print("Attempting MQTT connection...");
    displaySystemStatus("Connecting to MQTT...");

    // Create a client ID using the user's login
    String clientId = mqtt_client_id;
    clientId += String(random(0xffff), HEX);

    // Attempt to connect
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("connected");
      displaySystemStatus("MQTT connected");
      // Subscribe to message topics (both standardized and legacy topics)
      mqttClient.subscribe(mqtt_topic_requests);
      mqttClient.subscribe(mqtt_topic_legacy_messages);

      // Also subscribe to system notifications for ping messages
      mqttClient.subscribe(MQTT_TOPIC_NOTIFICATIONS);

      Serial.println("Subscribed to topics:");
      Serial.println(mqtt_topic_requests);
      Serial.println(mqtt_topic_legacy_messages);
      Serial.println(MQTT_TOPIC_NOTIFICATIONS);

      // Display a brief confirmation in message area - preserve gold accent
      tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP, tft.width() - ACCENT_WIDTH, 40, COLOR_MESSAGE_BG);

      // Ensure gold accent is intact
      drawGoldAccent();

      tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
      tft.setTextSize(2);
      tft.setTextColor(COLOR_ACCENT);
      tft.println("MQTT Connected");
      delay(1000);

      // Clear message but preserve gold accent
      tft.fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP, tft.width() - ACCENT_WIDTH, 40, COLOR_MESSAGE_BG);
      drawGoldAccent();
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      displaySystemStatus("MQTT connection failed. Retrying...");
      delay(5000);
      attempts++;
    }
  }

  if (!mqttClient.connected()) {
    displaySystemStatus("Failed to connect to MQTT after multiple attempts");
  }
}

void drawNULogo(int centerX, int centerY, int size) {
  // Draw a simplified NU logo
  int circleSize = size;
  int innerSize1 = size * 0.8;
  int innerSize2 = size * 0.6;
  int innerSize3 = size * 0.4;

  // Outer gold circle
  tft.fillCircle(centerX, centerY, circleSize, NU_GOLD);

  // Inner blue circle
  tft.fillCircle(centerX, centerY, innerSize1, NU_DARKBLUE);

  // White middle ring
  tft.fillCircle(centerX, centerY, innerSize2, ST77XX_WHITE);

  // Blue inner circle
  tft.fillCircle(centerX, centerY, innerSize3, NU_BLUE);

  // Add "NU" text in the center
  tft.setTextColor(NU_GOLD);
  tft.setTextSize(1);

  // Center the text in the logo
  tft.setCursor(centerX - 5, centerY - 3);
  tft.print("NU");
}

void setup() {
  Serial.begin(115200);
  Serial.println("ConsultEase Faculty Desk Unit Starting (Scanner Mode)...");
  pinMode(LED_PIN, OUTPUT); // For status indication
  digitalWrite(LED_PIN, LOW);

  // Initialize MQTT topics - only need specific status for publishing, specific requests for subscribing
  sprintf(mqtt_topic_status, MQTT_TOPIC_STATUS, FACULTY_ID);
  sprintf(mqtt_topic_requests, MQTT_TOPIC_REQUESTS, FACULTY_ID); // For subscribing to its own requests
  strcpy(mqtt_topic_legacy_messages, MQTT_LEGACY_MESSAGES); // For subscribing to legacy general messages
  sprintf(mqtt_client_id, "DeskUnitScanner_%s", FACULTY_NAME);
  Serial.println("MQTT topics initialized for scanner mode.");

  // Initialize SPI communication
  SPI.begin();

  // Initialize ST7789 display (240x320)
  tft.init(240, 320); // Initialize the display with its dimensions

  Serial.println("Display initialized");

  // Set rotation for landscape orientation
  tft.setRotation(1);

  // Run screen test to check if display is working correctly
  testScreen();

  // Setup the basic UI framework - truly seamless design
  drawUIFramework();

  // Show current time/date in header
  updateTimeDisplay();

  // Show initial status
  displaySystemStatus("Initializing system...");

  // Display welcome message with NU branding - seamlessly
  int centerX = tft.width() / 2;
  int logoY = MESSAGE_AREA_TOP + 60;

  // Ensure gold accent is intact
  drawGoldAccent();

  // Draw NU logo
  drawNULogo(centerX, logoY, 35);

  // Draw welcome text
  tft.setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
  tft.setTextColor(NU_GOLD);
  tft.setTextSize(2);
  tft.println("Welcome, " + String(current_user));

  tft.setCursor(ACCENT_WIDTH + 5, logoY + 50);
  tft.setTextSize(1.5);
  tft.setTextColor(ST77XX_WHITE);
  tft.println("National University");

  tft.setCursor(ACCENT_WIDTH + 5, logoY + 70);
  tft.println("Professor's Desk Unit");

  tft.setCursor(ACCENT_WIDTH + 5, logoY + 100);
  tft.setTextColor(NU_GOLD);
  tft.println("System Initializing...");

  delay(2000);

  // Set up WiFi - this will clear the welcome message but preserve gold accent
  setup_wifi();

  // Configure time
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);

  // Initialize MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(callback);

  // Initialize BLE Device as a Central/Scanner
  NimBLEDevice::init(""); // Initialize with no specific name for a scanner
  pBLEScan = NimBLEDevice::getScan(); // Get the scanner
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true); // Active scan uses more power, but gets scan response data
  pBLEScan->setInterval(100); // How often to scan
  pBLEScan->setWindow(99);  // How long to scan for during the interval
  Serial.println("BLE Scanner initialized.");
  displaySystemStatus("Scanning for beacon...");
  lastBeaconSignalTime = millis() - BLE_CONNECTION_TIMEOUT - 1000; // Initialize to disconnected state
}

void publishStatus(bool isPresent) {
    const char* statusMsg = isPresent ? "keychain_connected" : "keychain_disconnected";
    // Publish ONLY to specific faculty status topic
    if (mqttClient.connected()) {
        mqttClient.publish(mqtt_topic_status, statusMsg);
        Serial.print("Published to "); Serial.print(mqtt_topic_status); Serial.print(": "); Serial.println(statusMsg);
    }
    lastStatusPublishTime = millis();
    digitalWrite(LED_PIN, isPresent ? HIGH : LOW);
}

void loop() {
  if (!mqttClient.connected()) { reconnect(); }
  mqttClient.loop();

  unsigned long currentMillis = millis();

  // BLE Scanning Logic
  if (!pBLEScan->isScanning()) {
      if (currentMillis - lastBeaconSignalTime > BLE_SCAN_INTERVAL) { // Time to scan again if beacon hasn't been seen recently
          Serial.println("Starting BLE scan...");
          bleScanActive = true;
          // Start scan for BLE_SCAN_DURATION seconds, non-blocking
          // The scan results are handled in MyAdvertisedDeviceCallbacks
          pBLEScan->start(BLE_SCAN_DURATION, nullptr, false); 
      }
  } else { // Still scanning
      // If scan duration has passed and we are still marked as scanning by our flag
      // but pBLEScan->isScanning() is false, it means scan finished.
      // The onResult callback would have set isFacultyPresent if found.
      // If it wasn't found during the scan, isFacultyPresent would remain false (or become false after timeout)
      // The timeout logic below will handle this.
  }
  
  // Presence Timeout & Status Publishing Logic
  bool statusChanged = false;
  if (isFacultyPresent && (currentMillis - lastBeaconSignalTime > BLE_CONNECTION_TIMEOUT)) {
    Serial.println("Beacon signal lost (timeout).");
    isFacultyPresent = false;
    statusChanged = true;
  }

  // Publish status if it changed OR if it's time for a periodic update (e.g., every 5 mins)
  if (statusChanged || (currentMillis - lastStatusPublishTime > 300000)) { // 300000ms = 5 minutes
      publishStatus(isFacultyPresent);
  }

  if (isFacultyPresent && !digitalRead(LED_PIN)) { // Should be on if present
      digitalWrite(LED_PIN, HIGH);
  } else if (!isFacultyPresent && digitalRead(LED_PIN)) { // Should be off if not present
      digitalWrite(LED_PIN, LOW);
  }

  // Update time display every minute (as before)
  if (currentMillis - lastTimeUpdate > 60000) { lastTimeUpdate = currentMillis; updateTimeDisplay(); }
  delay(100); // Main loop delay
}