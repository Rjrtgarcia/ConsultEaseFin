/**
 * ConsultEase - Display Manager
 * 
 * This module handles all display-related functionality for the Faculty Desk Unit,
 * including UI components, screen updates, and user feedback.
 */

#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include "config.h"

// Display layout constants
#define HEADER_HEIGHT 40
#define STATUS_HEIGHT 20
#define MESSAGE_AREA_TOP HEADER_HEIGHT
#define MESSAGE_TITLE_HEIGHT 30
#define MESSAGE_TEXT_TOP (MESSAGE_AREA_TOP + MESSAGE_TITLE_HEIGHT)
#define ACCENT_WIDTH 5

class DisplayManager {
private:
    Adafruit_ST7789* tft;
    char timeStringBuff[50];
    char dateStringBuff[50];
    char lastMessage[MAX_DISPLAY_MESSAGE_SIZE];
    unsigned long lastTimeUpdate;

    /**
     * Draws the gold accent bar that runs along the left side of the display
     */
    void drawGoldAccent() {
        tft->fillRect(0, 0, ACCENT_WIDTH, tft->height() - STATUS_HEIGHT, COLOR_ACCENT);
    }

public:
    /**
     * Constructor
     */
    DisplayManager(Adafruit_ST7789* display) : 
        tft(display), 
        lastTimeUpdate(0) {
        memset(timeStringBuff, 0, sizeof(timeStringBuff));
        memset(dateStringBuff, 0, sizeof(dateStringBuff));
        memset(lastMessage, 0, sizeof(lastMessage));
    }

    /**
     * Initializes the display
     * @return true if successful, false otherwise
     */
    bool initialize() {
        boolean displayInitSuccess = false;
        int displayRetryCount = 0;
        
        while (!displayInitSuccess && displayRetryCount < 3) {
            try {
                tft->init(240, 320);
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
            return false;
        }
        
        tft->setRotation(TFT_ROTATION);
        testScreen();
        drawUIFramework();
        updateTimeDisplay();
        displaySystemStatus("Initializing system...");
        
        return true;
    }

    /**
     * Runs a test pattern on the screen
     */
    void testScreen() {
        tft->fillScreen(COLOR_BACKGROUND);
        delay(500);
        int sectionHeight = tft->height() / 3;
        tft->fillRect(0, 0, tft->width(), sectionHeight, NU_DARKBLUE);
        tft->fillRect(0, sectionHeight, tft->width(), sectionHeight, NU_BLUE);
        tft->fillRect(0, 2*sectionHeight, tft->width(), sectionHeight, NU_GOLD);
        drawGoldAccent();
        tft->setTextColor(TFT_TEXT);
        tft->setTextSize(2);
        tft->setCursor(ACCENT_WIDTH + 5, 10);
        tft->println("National University");
        tft->setCursor(ACCENT_WIDTH + 5, sectionHeight + 10);
        tft->println("Philippines");
        tft->setTextColor(NU_DARKBLUE);
        tft->setCursor(ACCENT_WIDTH + 5, 2*sectionHeight + 10);
        tft->println("Professor's Desk Unit");
        delay(3000);
        tft->fillScreen(COLOR_BACKGROUND);
    }

    /**
     * Draws the UI framework with header, status bar, and accent
     */
    void drawUIFramework() {
        tft->fillScreen(COLOR_BACKGROUND);
        tft->fillRect(ACCENT_WIDTH, 0, tft->width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER);
        tft->fillRect(0, tft->height() - STATUS_HEIGHT, tft->width(), STATUS_HEIGHT, NU_DARKBLUE);
        tft->drawFastHLine(0, tft->height() - STATUS_HEIGHT, tft->width(), COLOR_ACCENT);
        drawGoldAccent();
    }

    /**
     * Updates the time display in the header
     * @return true if time was updated, false if NTP update failed
     */
    bool updateTimeDisplay() {
        struct tm timeinfo;
        tft->fillRect(ACCENT_WIDTH, 0, tft->width() - ACCENT_WIDTH, HEADER_HEIGHT, COLOR_HEADER);
        if(!getLocalTime(&timeinfo)){
            Serial.println("Failed to obtain time via NTP");
            // Fallback to a static or last known time if needed
            tft->setTextColor(COLOR_TEXT);
            tft->setTextSize(2);
            tft->setCursor(ACCENT_WIDTH + 5, 10);
            tft->print("Time N/A");
            drawGoldAccent();
            return false;
        }
        
        strftime(timeStringBuff, sizeof(timeStringBuff), "%H:%M:%S", &timeinfo);
        strftime(dateStringBuff, sizeof(dateStringBuff), "%Y-%m-%d", &timeinfo);
        tft->setTextColor(COLOR_TEXT);
        tft->setTextSize(2);
        tft->setCursor(ACCENT_WIDTH + 5, 10);
        tft->print(timeStringBuff);
        
        int16_t x1, y1; 
        uint16_t w, h;
        tft->getTextBounds(dateStringBuff, 0, 0, &x1, &y1, &w, &h);
        tft->setCursor(tft->width() - w - 10, 10);
        tft->print(dateStringBuff);
        drawGoldAccent();
        return true;
    }

    /**
     * Displays a message in the main message area
     * @param message The message to display
     */
    void displayMessage(const char* message) {
        updateUIArea(0); // Clear full message area
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 5);
        tft->setTextColor(COLOR_ACCENT);
        tft->setTextSize(2);
        tft->println("New Message:");
        tft->drawFastHLine(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + MESSAGE_TITLE_HEIGHT - 5, 
                          tft->width() - ACCENT_WIDTH - 10, COLOR_ACCENT);
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_TEXT_TOP);
        tft->setTextColor(COLOR_TEXT);
        tft->setTextSize(2);
        
        // Word wrapping algorithm
        int16_t x1, y1; 
        uint16_t w, h;
        int maxWidth = tft->width() - ACCENT_WIDTH - 10;
        
        // Create a copy of the message we can modify
        char messageCopy[MAX_DISPLAY_MESSAGE_SIZE];
        strncpy(messageCopy, message, sizeof(messageCopy) - 1);
        messageCopy[sizeof(messageCopy) - 1] = '\0';
        
        // Keep track of current position
        char* token;
        char* saveptr;
        int yPos = MESSAGE_TEXT_TOP;
        
        // First tokenize by newlines
        token = strtok_r(messageCopy, "\n", &saveptr);
        while (token != NULL) {
            // Now handle word wrapping within each line
            String line = "";
            char* word;
            char* lineSavePtr;
            word = strtok_r(token, " ", &lineSavePtr);
            
            while (word != NULL) {
                String tempLine = line;
                if (tempLine.length() > 0) {
                    tempLine += " ";
                }
                tempLine += word;
                
                tft->getTextBounds(tempLine.c_str(), 0, 0, &x1, &y1, &w, &h);
                
                if (w > maxWidth) {
                    // Line would be too long, print current line and start a new one
                    tft->setCursor(ACCENT_WIDTH + 5, yPos);
                    tft->println(line);
                    yPos += h + 2;
                    line = word;
                } else {
                    // Word fits, add it to the line
                    line = tempLine;
                }
                
                word = strtok_r(NULL, " ", &lineSavePtr);
            }
            
            // Print the last line for this section
            if (line.length() > 0) {
                tft->setCursor(ACCENT_WIDTH + 5, yPos);
                tft->println(line);
                yPos += h + 2;
            }
            
            // Get next line from original message
            token = strtok_r(NULL, "\n", &saveptr);
        }
        
        // Store last message
        strncpy(lastMessage, message, sizeof(lastMessage) - 1);
        lastMessage[sizeof(lastMessage) - 1] = '\0';
    }

    /**
     * Displays a status message in the status bar
     * @param status The status to display
     */
    void displaySystemStatus(const char* status) {
        tft->fillRect(0, tft->height() - STATUS_HEIGHT, tft->width(), STATUS_HEIGHT, NU_DARKBLUE);
        tft->setCursor(ACCENT_WIDTH + 5, tft->height() - STATUS_HEIGHT + 5);
        tft->setTextColor(COLOR_STATUS_GOOD);
        tft->setTextSize(1);
        tft->println(status);
        tft->drawFastHLine(0, tft->height() - STATUS_HEIGHT, tft->width(), COLOR_ACCENT);
    }

    /**
     * Updates a specific area of the UI
     * @param area The area to update (0=full message area, 1=title only, 2=content only, 3=status bar)
     * @param message Optional message to display in the area
     */
    void updateUIArea(int area, const char* message = NULL) {
        switch (area) {
            case 0: // Full message area
                tft->fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP,
                            tft->width() - ACCENT_WIDTH,
                            tft->height() - MESSAGE_AREA_TOP - STATUS_HEIGHT,
                            COLOR_MESSAGE_BG);
                drawGoldAccent();
                if (message != NULL) {
                    tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
                    tft->setTextSize(2);
                    tft->setTextColor(NU_GOLD);
                    tft->println(message);
                }
                break;

            case 1: // Message title area only
                tft->fillRect(ACCENT_WIDTH, MESSAGE_AREA_TOP,
                            tft->width() - ACCENT_WIDTH,
                            MESSAGE_TITLE_HEIGHT,
                            COLOR_MESSAGE_BG);
                drawGoldAccent();
                if (message != NULL) {
                    tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
                    tft->setTextSize(2);
                    tft->setTextColor(NU_GOLD);
                    tft->println(message);
                }
                break;

            case 2: // Message content area only
                tft->fillRect(ACCENT_WIDTH, MESSAGE_TEXT_TOP,
                            tft->width() - ACCENT_WIDTH,
                            tft->height() - MESSAGE_TEXT_TOP - STATUS_HEIGHT,
                            COLOR_MESSAGE_BG);
                drawGoldAccent();
                break;

            case 3: // Status bar only
                if (message != NULL) {
                    displaySystemStatus(message);
                }
                break;
        }
    }

    /**
     * Draws the NU logo
     * @param centerX X coordinate of logo center
     * @param centerY Y coordinate of logo center
     * @param size Logo size
     */
    void drawNULogo(int centerX, int centerY, int size) {
        int circleSize = size;
        int innerSize1 = size * 0.8;
        int innerSize2 = size * 0.6;
        int innerSize3 = size * 0.4;
        
        tft->fillCircle(centerX, centerY, circleSize, NU_GOLD);
        tft->fillCircle(centerX, centerY, innerSize1, NU_DARKBLUE);
        tft->fillCircle(centerX, centerY, innerSize2, TFT_WHITE);
        tft->fillCircle(centerX, centerY, innerSize3, NU_BLUE);
        
        tft->setTextColor(NU_GOLD);
        tft->setTextSize(1);
        tft->setCursor(centerX - 5, centerY - 3);
        tft->print("NU");
    }

    /**
     * Displays the welcome screen
     * @param username The name of the current user
     */
    void showWelcomeScreen(const char* username) {
        int centerX = tft->width() / 2;
        int logoY = MESSAGE_AREA_TOP + 60;
        
        drawGoldAccent();
        drawNULogo(centerX, logoY, 35);
        
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        tft->setTextColor(NU_GOLD);
        tft->setTextSize(2);
        
        char welcomeMsg[50];
        snprintf(welcomeMsg, sizeof(welcomeMsg), "Welcome, %s", username);
        tft->println(welcomeMsg);
        
        tft->setCursor(ACCENT_WIDTH + 5, logoY + 50);
        tft->setTextSize(1.5);
        tft->setTextColor(TFT_TEXT);
        tft->println("National University");
        
        tft->setCursor(ACCENT_WIDTH + 5, logoY + 70);
        tft->println("Professor's Desk Unit");
        
        tft->setCursor(ACCENT_WIDTH + 5, logoY + 100);
        tft->setTextColor(NU_GOLD);
        tft->println("System Initializing...");
    }

    /**
     * Displays WiFi connection status
     * @param ssid The WiFi SSID
     * @param status Status message
     * @param dots Number of dots for the animation
     */
    void showWiFiConnecting(const char* ssid, const char* status, int dots) {
        tft->fillRect(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 60, tft->width() - ACCENT_WIDTH - 10, 20, COLOR_BACKGROUND);
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 60);
        tft->setTextColor(COLOR_TEXT);
        tft->print("Connecting");
        
        for (int i = 0; i < 6; i++) {
            if (i < dots) {
                tft->setTextColor((i % 2 == 0) ? NU_GOLD : NU_LIGHTGOLD);
                tft->print(".");
            } else {
                tft->print(" ");
            }
        }
    }

    /**
     * Displays WiFi connection success
     * @param ssid The connected SSID
     * @param ipAddress The assigned IP address
     */
    void showWiFiConnected(const char* ssid, const char* ipAddress) {
        updateUIArea(0);
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        tft->setTextSize(2);
        tft->setTextColor(NU_GOLD);
        tft->println("WiFi Connected");
        
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 50);
        tft->setTextSize(1);
        tft->setTextColor(COLOR_TEXT);
        tft->print("SSID: ");
        tft->println(ssid);
        
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 70);
        tft->print("IP: ");
        tft->println(ipAddress);
        
        displaySystemStatus("WiFi connected successfully");
    }

    /**
     * Displays WiFi connection failure
     * @param statusCode The WiFi status code
     * @param retryCount The current retry count
     * @param errorMsg The error message
     */
    void showWiFiError(int statusCode, int retryCount, const char* errorMsg) {
        updateUIArea(0);
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 10);
        tft->setTextSize(2);
        tft->setTextColor(ST77XX_RED);
        tft->println("WiFi Connection Failed");
        
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 50);
        tft->setTextSize(1);
        tft->setTextColor(COLOR_TEXT);
        tft->print("Status code: ");
        tft->println(statusCode);
        
        tft->setCursor(ACCENT_WIDTH + 5, MESSAGE_AREA_TOP + 70);
        tft->print("Retry count: ");
        tft->println(retryCount);
        
        displaySystemStatus(errorMsg);
    }
};

#endif // DISPLAY_MANAGER_H 