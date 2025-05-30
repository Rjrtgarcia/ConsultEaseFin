/**
 * ConsultEase - Display Mock
 * 
 * This file provides a mock implementation of the Adafruit_ST7789 display
 * for testing purposes without requiring the actual hardware.
 */

#ifndef DISPLAY_MOCK_H
#define DISPLAY_MOCK_H

#include <Arduino.h>
#include <string>
#include <vector>
#include <map>

// Mock implementation of Adafruit_ST7789
class Adafruit_ST7789_Mock {
private:
    // Screen buffer to store what would be displayed
    std::vector<uint16_t> frameBuffer;
    
    // Properties
    int16_t _width;
    int16_t _height;
    int16_t _rotation;
    int16_t cursor_x;
    int16_t cursor_y;
    uint16_t textcolor;
    uint16_t textbgcolor;
    uint8_t textsize_x;
    uint8_t textsize_y;
    bool wrap;
    
    // Logging to track what methods are called
    std::vector<std::string> methodCallLog;
    
    // Store text that would be displayed
    std::vector<std::string> displayedText;
    
    // Store rectangles that would be drawn
    struct Rectangle {
        int16_t x;
        int16_t y;
        int16_t w;
        int16_t h;
        uint16_t color;
    };
    std::vector<Rectangle> rectangles;

public:
    // Constructor
    Adafruit_ST7789_Mock(int8_t cs = -1, int8_t dc = -1, int8_t mosi = -1, int8_t sclk = -1, int8_t rst = -1) :
        _width(0),
        _height(0),
        _rotation(0),
        cursor_x(0),
        cursor_y(0),
        textcolor(0xFFFF),  // White
        textbgcolor(0x0000),  // Black
        textsize_x(1),
        textsize_y(1),
        wrap(true) {
        
        methodCallLog.push_back("Adafruit_ST7789_Mock constructor called");
        Serial.println("Mock display created");
    }
    
    // Initialize the display
    void init(uint16_t width, uint16_t height, uint8_t mode = 0) {
        _width = width;
        _height = height;
        
        // Initialize frame buffer with background color
        frameBuffer.resize(width * height, 0);
        
        methodCallLog.push_back("init(" + String(width) + ", " + String(height) + ")");
        Serial.println("Mock display initialized with dimensions: " + String(width) + "x" + String(height));
    }
    
    // Set rotation
    void setRotation(uint8_t rotation) {
        _rotation = rotation;
        methodCallLog.push_back("setRotation(" + String(rotation) + ")");
    }
    
    // Fill the screen with a color
    void fillScreen(uint16_t color) {
        std::fill(frameBuffer.begin(), frameBuffer.end(), color);
        methodCallLog.push_back("fillScreen(0x" + String(color, HEX) + ")");
    }
    
    // Draw a filled rectangle
    void fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color) {
        methodCallLog.push_back("fillRect(" + String(x) + ", " + String(y) + ", " + 
                               String(w) + ", " + String(h) + ", 0x" + String(color, HEX) + ")");
        
        // Store rectangle information
        rectangles.push_back({x, y, w, h, color});
        
        // Update frame buffer
        for (int16_t j = y; j < y + h && j < _height; j++) {
            for (int16_t i = x; i < x + w && i < _width; i++) {
                if (i >= 0 && j >= 0) {
                    frameBuffer[j * _width + i] = color;
                }
            }
        }
    }
    
    // Draw a single pixel
    void drawPixel(int16_t x, int16_t y, uint16_t color) {
        if (x >= 0 && x < _width && y >= 0 && y < _height) {
            frameBuffer[y * _width + x] = color;
        }
    }
    
    // Draw a horizontal line
    void drawFastHLine(int16_t x, int16_t y, int16_t w, uint16_t color) {
        methodCallLog.push_back("drawFastHLine(" + String(x) + ", " + String(y) + ", " + 
                               String(w) + ", 0x" + String(color, HEX) + ")");
        
        for (int16_t i = 0; i < w; i++) {
            drawPixel(x + i, y, color);
        }
    }
    
    // Draw a vertical line
    void drawFastVLine(int16_t x, int16_t y, int16_t h, uint16_t color) {
        methodCallLog.push_back("drawFastVLine(" + String(x) + ", " + String(y) + ", " + 
                               String(h) + ", 0x" + String(color, HEX) + ")");
        
        for (int16_t i = 0; i < h; i++) {
            drawPixel(x, y + i, color);
        }
    }
    
    // Set text cursor position
    void setCursor(int16_t x, int16_t y) {
        cursor_x = x;
        cursor_y = y;
        methodCallLog.push_back("setCursor(" + String(x) + ", " + String(y) + ")");
    }
    
    // Set text color
    void setTextColor(uint16_t color) {
        textcolor = color;
        methodCallLog.push_back("setTextColor(0x" + String(color, HEX) + ")");
    }
    
    // Set text size
    void setTextSize(uint8_t size) {
        textsize_x = textsize_y = size;
        methodCallLog.push_back("setTextSize(" + String(size) + ")");
    }
    
    // Print a string
    size_t print(const char* str) {
        methodCallLog.push_back("print(\"" + String(str) + "\")");
        displayedText.push_back(str);
        
        // For a real implementation, we would actually draw the text
        // but for this mock we just store it
        cursor_x += strlen(str) * 6 * textsize_x;
        
        return strlen(str);
    }
    
    // Print a string with newline
    size_t println(const char* str) {
        methodCallLog.push_back("println(\"" + String(str) + "\")");
        displayedText.push_back(String(str));
        
        // Move cursor to next line
        cursor_x = 0;
        cursor_y += 8 * textsize_y;
        
        return strlen(str) + 1; // +1 for newline
    }
    
    // Print an integer
    size_t print(int n) {
        String s = String(n);
        return print(s.c_str());
    }
    
    // Print an integer with newline
    size_t println(int n) {
        String s = String(n);
        return println(s.c_str());
    }
    
    // Print a string
    size_t print(const String &s) {
        return print(s.c_str());
    }
    
    // Print a string with newline
    size_t println(const String &s) {
        return println(s.c_str());
    }
    
    // Calculate text bounds
    void getTextBounds(const char *str, int16_t x, int16_t y, int16_t *x1, int16_t *y1, uint16_t *w, uint16_t *h) {
        *x1 = x;
        *y1 = y;
        *w = strlen(str) * 6 * textsize_x;
        *h = 8 * textsize_y;
        
        methodCallLog.push_back("getTextBounds(\"" + String(str) + "\", " + String(x) + ", " + String(y) + ")");
    }
    
    // Get width
    int16_t width() const {
        return _width;
    }
    
    // Get height
    int16_t height() const {
        return _height;
    }
    
    // Get method call log
    const std::vector<std::string>& getMethodCallLog() const {
        return methodCallLog;
    }
    
    // Clear method call log
    void clearMethodCallLog() {
        methodCallLog.clear();
    }
    
    // Get displayed text
    const std::vector<std::string>& getDisplayedText() const {
        return displayedText;
    }
    
    // Get drawn rectangles
    const std::vector<Rectangle>& getDrawnRectangles() const {
        return rectangles;
    }
    
    // Check if a specific color exists at a location
    bool hasColorAt(int16_t x, int16_t y, uint16_t color) {
        if (x >= 0 && x < _width && y >= 0 && y < _height) {
            return frameBuffer[y * _width + x] == color;
        }
        return false;
    }
    
    // Print a summary of what's currently on the display
    void printDisplaySummary() {
        Serial.println("\n----- Mock Display Summary -----");
        Serial.print("Dimensions: ");
        Serial.print(_width);
        Serial.print("x");
        Serial.println(_height);
        
        Serial.print("Rotation: ");
        Serial.println(_rotation);
        
        Serial.println("Text content:");
        for (const auto& text : displayedText) {
            Serial.print("  \"");
            Serial.print(text.c_str());
            Serial.println("\"");
        }
        
        Serial.print("Rectangles drawn: ");
        Serial.println(rectangles.size());
        
        Serial.println("-------------------------------");
    }
};

// Use this typedef to easily switch between mock and real implementations
typedef Adafruit_ST7789_Mock MockDisplay;

#endif // DISPLAY_MOCK_H 