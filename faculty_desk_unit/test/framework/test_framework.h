/**
 * ConsultEase - Test Framework
 * 
 * This file provides the core testing framework functionality for the ConsultEase
 * Faculty Desk Unit, including assertions, test case management, and utilities.
 */

#ifndef TEST_FRAMEWORK_H
#define TEST_FRAMEWORK_H

#include <Arduino.h>
#include <stdint.h>
#include <vector>
#include <functional>
#include <string>

// Define colors for test output
#define TEST_COLOR_RESET   "\033[0m"
#define TEST_COLOR_RED     "\033[31m"
#define TEST_COLOR_GREEN   "\033[32m"
#define TEST_COLOR_YELLOW  "\033[33m"
#define TEST_COLOR_BLUE    "\033[34m"
#define TEST_COLOR_MAGENTA "\033[35m"
#define TEST_COLOR_CYAN    "\033[36m"

// Test framework configuration
#define TEST_MAX_NAME_LENGTH 64
#define TEST_MAX_MESSAGE_LENGTH 256
#define TEST_DEFAULT_TIMEOUT 5000  // 5 seconds

// Forward declarations
class TestCase;
class TestSuite;

/**
 * Test Result struct to track test outcomes
 */
struct TestResult {
    bool passed;
    char message[TEST_MAX_MESSAGE_LENGTH];
    unsigned long executionTime;

    TestResult() : passed(true), executionTime(0) {
        message[0] = '\0';
    }
};

/**
 * Test Case class for individual test cases
 */
class TestCase {
private:
    char name[TEST_MAX_NAME_LENGTH];
    std::function<void()> testFunction;
    TestResult result;
    unsigned long timeout;

public:
    /**
     * Constructor
     * @param name The name of the test case
     * @param testFunction The function to run for this test
     * @param timeout Timeout in milliseconds
     */
    TestCase(const char* name, std::function<void()> testFunction, unsigned long timeout = TEST_DEFAULT_TIMEOUT) :
        testFunction(testFunction),
        timeout(timeout) {
        strncpy(this->name, name, TEST_MAX_NAME_LENGTH - 1);
        this->name[TEST_MAX_NAME_LENGTH - 1] = '\0';
    }

    /**
     * Run the test case
     * @return The test result
     */
    TestResult run() {
        Serial.print(TEST_COLOR_BLUE);
        Serial.print("RUNNING TEST: ");
        Serial.print(name);
        Serial.println(TEST_COLOR_RESET);

        unsigned long startTime = millis();
        
        // Run the test function with timeout monitoring
        try {
            testFunction();
            result.passed = true;
        } catch (const char* message) {
            result.passed = false;
            strncpy(result.message, message, TEST_MAX_MESSAGE_LENGTH - 1);
            result.message[TEST_MAX_MESSAGE_LENGTH - 1] = '\0';
        } catch (...) {
            result.passed = false;
            strncpy(result.message, "Unknown exception", TEST_MAX_MESSAGE_LENGTH - 1);
            result.message[TEST_MAX_MESSAGE_LENGTH - 1] = '\0';
        }
        
        result.executionTime = millis() - startTime;
        
        // Check for timeout
        if (result.executionTime > timeout) {
            result.passed = false;
            snprintf(result.message, TEST_MAX_MESSAGE_LENGTH, 
                     "Test timed out after %lu ms (limit: %lu ms)", 
                     result.executionTime, timeout);
        }
        
        // Print result
        if (result.passed) {
            Serial.print(TEST_COLOR_GREEN);
            Serial.print("PASS");
        } else {
            Serial.print(TEST_COLOR_RED);
            Serial.print("FAIL");
        }
        
        Serial.print(TEST_COLOR_RESET);
        Serial.print(" (");
        Serial.print(result.executionTime);
        Serial.print(" ms): ");
        Serial.println(name);
        
        if (!result.passed && result.message[0] != '\0') {
            Serial.print(TEST_COLOR_RED);
            Serial.print("       Error: ");
            Serial.print(result.message);
            Serial.println(TEST_COLOR_RESET);
        }
        
        return result;
    }
    
    /**
     * Get the test case name
     * @return The test case name
     */
    const char* getName() const {
        return name;
    }
    
    /**
     * Get the test result
     * @return The test result
     */
    const TestResult& getResult() const {
        return result;
    }
};

/**
 * Test Suite class for grouping related test cases
 */
class TestSuite {
private:
    char name[TEST_MAX_NAME_LENGTH];
    std::vector<TestCase> testCases;
    int passCount;
    int failCount;
    unsigned long totalExecutionTime;

public:
    /**
     * Constructor
     * @param name The name of the test suite
     */
    TestSuite(const char* name) : passCount(0), failCount(0), totalExecutionTime(0) {
        strncpy(this->name, name, TEST_MAX_NAME_LENGTH - 1);
        this->name[TEST_MAX_NAME_LENGTH - 1] = '\0';
    }

    /**
     * Add a test case to the suite
     * @param name The name of the test case
     * @param testFunction The function to run for this test
     * @param timeout Timeout in milliseconds
     */
    void addTest(const char* name, std::function<void()> testFunction, unsigned long timeout = TEST_DEFAULT_TIMEOUT) {
        testCases.push_back(TestCase(name, testFunction, timeout));
    }

    /**
     * Run all test cases in the suite
     */
    void run() {
        Serial.print(TEST_COLOR_CYAN);
        Serial.print("\n========== TEST SUITE: ");
        Serial.print(name);
        Serial.println(" ==========");
        Serial.println(TEST_COLOR_RESET);
        
        passCount = 0;
        failCount = 0;
        totalExecutionTime = 0;
        
        for (auto& testCase : testCases) {
            TestResult result = testCase.run();
            
            if (result.passed) {
                passCount++;
            } else {
                failCount++;
            }
            
            totalExecutionTime += result.executionTime;
        }
        
        // Print summary
        Serial.print(TEST_COLOR_CYAN);
        Serial.println("\n===== TEST SUITE SUMMARY =====");
        Serial.print(TEST_COLOR_RESET);
        
        Serial.print("Suite: ");
        Serial.println(name);
        
        Serial.print("Total Tests: ");
        Serial.println(testCases.size());
        
        Serial.print("Passed: ");
        Serial.print(TEST_COLOR_GREEN);
        Serial.print(passCount);
        Serial.println(TEST_COLOR_RESET);
        
        Serial.print("Failed: ");
        Serial.print(TEST_COLOR_RED);
        Serial.print(failCount);
        Serial.println(TEST_COLOR_RESET);
        
        Serial.print("Total Execution Time: ");
        Serial.print(totalExecutionTime);
        Serial.println(" ms");
        
        Serial.print(TEST_COLOR_CYAN);
        Serial.println("=============================\n");
        Serial.print(TEST_COLOR_RESET);
    }
    
    /**
     * Get the test suite name
     * @return The test suite name
     */
    const char* getName() const {
        return name;
    }
    
    /**
     * Get the number of passed tests
     * @return The number of passed tests
     */
    int getPassCount() const {
        return passCount;
    }
    
    /**
     * Get the number of failed tests
     * @return The number of failed tests
     */
    int getFailCount() const {
        return failCount;
    }
    
    /**
     * Get the total number of tests
     * @return The total number of tests
     */
    int getTotalCount() const {
        return testCases.size();
    }
    
    /**
     * Get the total execution time
     * @return The total execution time
     */
    unsigned long getTotalExecutionTime() const {
        return totalExecutionTime;
    }
};

/**
 * Test Registry to manage all test suites
 */
class TestRegistry {
private:
    static std::vector<TestSuite*> testSuites;

public:
    /**
     * Add a test suite to the registry
     * @param suite The test suite to add
     */
    static void addSuite(TestSuite* suite) {
        testSuites.push_back(suite);
    }
    
    /**
     * Run all test suites in the registry
     */
    static void runAll() {
        Serial.print(TEST_COLOR_MAGENTA);
        Serial.println("\n**********************************");
        Serial.println("*      STARTING ALL TESTS        *");
        Serial.println("**********************************\n");
        Serial.print(TEST_COLOR_RESET);
        
        unsigned long startTime = millis();
        int totalTests = 0;
        int totalPassed = 0;
        int totalFailed = 0;
        
        for (auto suite : testSuites) {
            suite->run();
            totalTests += suite->getTotalCount();
            totalPassed += suite->getPassCount();
            totalFailed += suite->getFailCount();
        }
        
        unsigned long totalTime = millis() - startTime;
        
        // Print global summary
        Serial.print(TEST_COLOR_MAGENTA);
        Serial.println("\n**********************************");
        Serial.println("*        TESTING COMPLETE        *");
        Serial.println("**********************************");
        Serial.print(TEST_COLOR_RESET);
        
        Serial.print("Total Test Suites: ");
        Serial.println(testSuites.size());
        
        Serial.print("Total Tests: ");
        Serial.println(totalTests);
        
        Serial.print("Total Passed: ");
        Serial.print(TEST_COLOR_GREEN);
        Serial.print(totalPassed);
        Serial.println(TEST_COLOR_RESET);
        
        Serial.print("Total Failed: ");
        Serial.print(TEST_COLOR_RED);
        Serial.print(totalFailed);
        Serial.println(TEST_COLOR_RESET);
        
        Serial.print("Total Execution Time: ");
        Serial.print(totalTime);
        Serial.println(" ms");
        
        if (totalFailed == 0) {
            Serial.print(TEST_COLOR_GREEN);
            Serial.println("\nALL TESTS PASSED!");
        } else {
            Serial.print(TEST_COLOR_RED);
            Serial.print("\nSOME TESTS FAILED (");
            Serial.print(totalFailed);
            Serial.println(" failures)");
        }
        
        Serial.print(TEST_COLOR_RESET);
    }
    
    /**
     * Clear all test suites from the registry
     */
    static void clear() {
        testSuites.clear();
    }
};

// Initialize static member
std::vector<TestSuite*> TestRegistry::testSuites;

/**
 * Memory tracking functionality for leak detection
 */
class MemoryTracker {
private:
    size_t initialFreeHeap;
    size_t initialLargestFreeBlock;
    
public:
    /**
     * Constructor - captures the current memory state
     */
    MemoryTracker() {
        capture();
    }
    
    /**
     * Capture the current memory state
     */
    void capture() {
        initialFreeHeap = ESP.getFreeHeap();
        initialLargestFreeBlock = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT);
    }
    
    /**
     * Check for memory leaks
     * @param printResults Whether to print the results
     * @return true if there are no leaks, false otherwise
     */
    bool checkForLeaks(bool printResults = true) {
        size_t currentFreeHeap = ESP.getFreeHeap();
        size_t currentLargestFreeBlock = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT);
        
        int64_t heapDiff = static_cast<int64_t>(currentFreeHeap) - static_cast<int64_t>(initialFreeHeap);
        int64_t blockDiff = static_cast<int64_t>(currentLargestFreeBlock) - static_cast<int64_t>(initialLargestFreeBlock);
        
        if (printResults) {
            Serial.println("\n--- Memory Usage Report ---");
            Serial.print("Initial Free Heap: ");
            Serial.print(initialFreeHeap);
            Serial.println(" bytes");
            
            Serial.print("Current Free Heap: ");
            Serial.print(currentFreeHeap);
            Serial.println(" bytes");
            
            Serial.print("Difference: ");
            if (heapDiff < 0) {
                Serial.print(TEST_COLOR_RED);
            } else {
                Serial.print(TEST_COLOR_GREEN);
            }
            Serial.print(heapDiff);
            Serial.print(TEST_COLOR_RESET);
            Serial.println(" bytes");
            
            Serial.print("Largest Free Block Difference: ");
            if (blockDiff < 0) {
                Serial.print(TEST_COLOR_RED);
            } else {
                Serial.print(TEST_COLOR_GREEN);
            }
            Serial.print(blockDiff);
            Serial.print(TEST_COLOR_RESET);
            Serial.println(" bytes");
            
            Serial.println("---------------------------");
        }
        
        // Consider it a leak if we've lost more than 100 bytes of heap
        return (heapDiff > -100);
    }
};

// Assertion macros
#define TEST_ASSERT(condition) \
    do { \
        if (!(condition)) { \
            char message[TEST_MAX_MESSAGE_LENGTH]; \
            snprintf(message, TEST_MAX_MESSAGE_LENGTH, "Assertion failed: %s (line %d)", #condition, __LINE__); \
            throw message; \
        } \
    } while (0)

#define TEST_ASSERT_EQUAL(expected, actual) \
    do { \
        if ((expected) != (actual)) { \
            char message[TEST_MAX_MESSAGE_LENGTH]; \
            snprintf(message, TEST_MAX_MESSAGE_LENGTH, "Assertion failed: %s == %s, expected: %d, actual: %d (line %d)", \
                    #expected, #actual, static_cast<int>(expected), static_cast<int>(actual), __LINE__); \
            throw message; \
        } \
    } while (0)

#define TEST_ASSERT_STRING_EQUAL(expected, actual) \
    do { \
        if (strcmp((expected), (actual)) != 0) { \
            char message[TEST_MAX_MESSAGE_LENGTH]; \
            snprintf(message, TEST_MAX_MESSAGE_LENGTH, "Assertion failed: %s == %s, expected: \"%s\", actual: \"%s\" (line %d)", \
                    #expected, #actual, expected, actual, __LINE__); \
            throw message; \
        } \
    } while (0)

#define TEST_ASSERT_NEAR(expected, actual, epsilon) \
    do { \
        if (abs((expected) - (actual)) > (epsilon)) { \
            char message[TEST_MAX_MESSAGE_LENGTH]; \
            snprintf(message, TEST_MAX_MESSAGE_LENGTH, "Assertion failed: abs(%s - %s) <= %s, expected: %f, actual: %f, difference: %f (line %d)", \
                    #expected, #actual, #epsilon, static_cast<double>(expected), static_cast<double>(actual), \
                    static_cast<double>(abs((expected) - (actual))), __LINE__); \
            throw message; \
        } \
    } while (0)

#define TEST_ASSERT_TRUE(condition) TEST_ASSERT(condition)
#define TEST_ASSERT_FALSE(condition) TEST_ASSERT(!(condition))

#define TEST_ASSERT_NULL(pointer) TEST_ASSERT((pointer) == nullptr)
#define TEST_ASSERT_NOT_NULL(pointer) TEST_ASSERT((pointer) != nullptr)

// Timing assertions
#define TEST_ASSERT_DURATION_LESS_THAN(block, max_ms) \
    do { \
        unsigned long start_time = millis(); \
        { block; } \
        unsigned long duration = millis() - start_time; \
        if (duration > (max_ms)) { \
            char message[TEST_MAX_MESSAGE_LENGTH]; \
            snprintf(message, TEST_MAX_MESSAGE_LENGTH, "Duration assertion failed: block took %lu ms, expected < %lu ms (line %d)", \
                    duration, static_cast<unsigned long>(max_ms), __LINE__); \
            throw message; \
        } \
    } while (0)

// Memory leak assertions
#define TEST_ASSERT_NO_MEMORY_LEAK(block) \
    do { \
        MemoryTracker memTracker; \
        { block; } \
        if (!memTracker.checkForLeaks(false)) { \
            memTracker.checkForLeaks(true); \
            throw "Memory leak detected"; \
        } \
    } while (0)

#endif // TEST_FRAMEWORK_H 