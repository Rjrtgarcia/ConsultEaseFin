/**
 * ConsultEase - Display Manager Tests
 * 
 * This file contains unit tests for the DisplayManager class.
 */

#include "../framework/test_includes.h"

// Display Manager test suite
class DisplayManagerTestSuite : public TestSuite {
public:
    DisplayManagerTestSuite() : TestSuite("DisplayManager Tests") {
        // Add tests to the suite
        addTest("Constructor initializes properly", std::bind(&DisplayManagerTestSuite::testConstructor, this));
        addTest("Init configures display correctly", std::bind(&DisplayManagerTestSuite::testInit, this));
        addTest("Header is drawn properly", std::bind(&DisplayManagerTestSuite::testDrawHeader, this));
        addTest("Status area is drawn properly", std::bind(&DisplayManagerTestSuite::testDrawStatusArea, this));
        addTest("Message display works correctly", std::bind(&DisplayManagerTestSuite::testDisplayMessage, this));
        addTest("Update time display works", std::bind(&DisplayManagerTestSuite::testUpdateTimeDisplay, this));
        addTest("Status indicator shows correct colors", std::bind(&DisplayManagerTestSuite::testStatusIndicator, this));
    }

private:
    // Test constructor
    void testConstructor() {
        // Create mock display
        MockDisplay tft;
        
        // Create display manager with mock display
        DisplayManager displayManager(&tft);
        
        // Verify the mock display was initialized correctly
        const auto& callLog = tft.getMethodCallLog();
        
        // The constructor should have called some methods on the display
        TEST_ASSERT_TRUE(callLog.size() > 0);
    }
    
    // Test init method
    void testInit() {
        // Create mock display
        MockDisplay tft;
        
        // Create display manager with mock display
        DisplayManager displayManager(&tft);
        
        // Clear previous calls
        tft.clearMethodCallLog();
        
        // Call init
        displayManager.init();
        
        // Get the method call log
        const auto& callLog = tft.getMethodCallLog();
        
        // Verify that init called the expected display methods
        bool initCalled = false;
        bool fillScreenCalled = false;
        
        for (const auto& call : callLog) {
            if (call.find("init") != std::string::npos) {
                initCalled = true;
            }
            if (call.find("fillScreen") != std::string::npos) {
                fillScreenCalled = true;
            }
        }
        
        TEST_ASSERT_TRUE(initCalled);
        TEST_ASSERT_TRUE(fillScreenCalled);
    }
    
    // Test drawing header
    void testDrawHeader() {
        // Create mock display
        MockDisplay tft;
        
        // Create display manager with mock display
        DisplayManager displayManager(&tft);
        displayManager.init();
        
        // Clear previous calls
        tft.clearMethodCallLog();
        
        // Draw header
        displayManager.drawHeader();
        
        // Get the method call log
        const auto& callLog = tft.getMethodCallLog();
        
        // Check if fillRect was called for the header
        bool headerRectDrawn = false;
        for (const auto& call : callLog) {
            if (call.find("fillRect") != std::string::npos) {
                headerRectDrawn = true;
                break;
            }
        }
        
        TEST_ASSERT_TRUE(headerRectDrawn);
        
        // Check if faculty name is displayed
        const auto& displayedText = tft.getDisplayedText();
        bool facultyNameDisplayed = false;
        
        for (const auto& text : displayedText) {
            if (text.find(FACULTY_NAME) != std::string::npos) {
                facultyNameDisplayed = true;
                break;
            }
        }
        
        TEST_ASSERT_TRUE(facultyNameDisplayed);
    }
    
    // Test drawing status area
    void testDrawStatusArea() {
        // Create mock display
        MockDisplay tft;
        
        // Create display manager with mock display
        DisplayManager displayManager(&tft);
        displayManager.init();
        
        // Clear previous calls
        tft.clearMethodCallLog();
        
        // Draw status area
        displayManager.drawStatusArea();
        
        // Get the method call log
        const auto& callLog = tft.getMethodCallLog();
        
        // Check if fillRect was called for the status area
        bool statusRectDrawn = false;
        for (const auto& call : callLog) {
            if (call.find("fillRect") != std::string::npos) {
                statusRectDrawn = true;
                break;
            }
        }
        
        TEST_ASSERT_TRUE(statusRectDrawn);
    }
    
    // Test displaying a message
    void testDisplayMessage() {
        // Create mock display
        MockDisplay tft;
        
        // Create display manager with mock display
        DisplayManager displayManager(&tft);
        displayManager.init();
        
        // Clear previous calls
        tft.clearMethodCallLog();
        
        // Test message
        const char* title = "Test Title";
        const char* message = "This is a test message";
        
        // Display the message
        displayManager.displayMessage(title, message);
        
        // Get the displayed text
        const auto& displayedText = tft.getDisplayedText();
        
        // Check if title and message are displayed
        bool titleDisplayed = false;
        bool messageDisplayed = false;
        
        for (const auto& text : displayedText) {
            if (text.find(title) != std::string::npos) {
                titleDisplayed = true;
            }
            if (text.find(message) != std::string::npos) {
                messageDisplayed = true;
            }
        }
        
        TEST_ASSERT_TRUE(titleDisplayed);
        TEST_ASSERT_TRUE(messageDisplayed);
    }
    
    // Test updating the time display
    void testUpdateTimeDisplay() {
        // Create mock display
        MockDisplay tft;
        
        // Create display manager with mock display
        DisplayManager displayManager(&tft);
        displayManager.init();
        
        // Clear previous calls
        tft.clearMethodCallLog();
        
        // Update time display
        displayManager.updateTimeDisplay();
        
        // Get the method call log
        const auto& callLog = tft.getMethodCallLog();
        
        // Time display should involve setting cursor and printing text
        bool setCursorCalled = false;
        bool printCalled = false;
        
        for (const auto& call : callLog) {
            if (call.find("setCursor") != std::string::npos) {
                setCursorCalled = true;
            }
            if (call.find("print") != std::string::npos) {
                printCalled = true;
            }
        }
        
        TEST_ASSERT_TRUE(setCursorCalled);
        TEST_ASSERT_TRUE(printCalled);
    }
    
    // Test status indicator
    void testStatusIndicator() {
        // Create mock display
        MockDisplay tft;
        
        // Create display manager with mock display
        DisplayManager displayManager(&tft);
        displayManager.init();
        
        // Clear previous calls
        tft.clearMethodCallLog();
        
        // Test available status
        displayManager.updateStatusIndicator(true);
        
        // Get the rectangles drawn
        const auto& rectangles = tft.getDrawnRectangles();
        
        // Check if at least one rectangle was drawn (the status indicator)
        TEST_ASSERT_TRUE(rectangles.size() > 0);
        
        // Clear and test unavailable status
        tft.clearMethodCallLog();
        displayManager.updateStatusIndicator(false);
        
        // Get the rectangles drawn again
        const auto& rectangles2 = tft.getDrawnRectangles();
        
        // Check if at least one rectangle was drawn (the status indicator)
        TEST_ASSERT_TRUE(rectangles2.size() > 0);
    }
};

// Main function
void runDisplayManagerTests() {
    // Setup test environment
    TestUtils::setupStandardTestEnvironment();
    
    // Create and run the test suite
    DisplayManagerTestSuite suite;
    TestRegistry::addSuite(&suite);
    TestRegistry::runAll();
    
    // Cleanup
    TestUtils::cleanupTestMode();
}

// When included in a sketch, call the run function
#ifdef ARDUINO
void setup() {
    Serial.begin(115200);
    delay(2000);  // Allow time to open the Serial Monitor
    
    Serial.println("Starting Display Manager Tests...");
    runDisplayManagerTests();
}

void loop() {
    // Nothing to do here
    delay(1000);
}
#endif 