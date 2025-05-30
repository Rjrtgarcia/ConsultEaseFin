/**
 * ConsultEase - Button Manager
 * 
 * This module handles button interactions for the Faculty Desk Unit,
 * including debouncing, state tracking, and event dispatching.
 */

#ifndef BUTTON_MANAGER_H
#define BUTTON_MANAGER_H

#include <Arduino.h>
#include "config.h"

// Debounce delay in milliseconds
#define BUTTON_DEBOUNCE_DELAY 50

class ButtonManager {
private:
    // Button pins
    int manualOverridePin;
    int acceptPin;
    int rejectPin;
    
    // Button states
    int manualOverrideState;
    int lastManualOverrideState;
    unsigned long lastManualOverrideDebounceTime;
    
    int acceptState;
    int lastAcceptState;
    unsigned long lastAcceptDebounceTime;
    
    int rejectState;
    int lastRejectState;
    unsigned long lastRejectDebounceTime;
    
    // Button event flags
    bool manualOverridePressed;
    bool acceptPressed;
    bool rejectPressed;

public:
    /**
     * Constructor
     */
    ButtonManager() :
        manualOverridePin(BUTTON_PIN),
        acceptPin(ACCEPT_BUTTON_PIN),
        rejectPin(REJECT_BUTTON_PIN),
        manualOverrideState(HIGH),
        lastManualOverrideState(HIGH),
        lastManualOverrideDebounceTime(0),
        acceptState(HIGH),
        lastAcceptState(HIGH),
        lastAcceptDebounceTime(0),
        rejectState(HIGH),
        lastRejectState(HIGH),
        lastRejectDebounceTime(0),
        manualOverridePressed(false),
        acceptPressed(false),
        rejectPressed(false)
    {
    }
    
    /**
     * Initialize the button manager
     * @return true if successful, false otherwise
     */
    bool initialize() {
        Serial.println("Initializing Button Manager...");
        
        // Configure button pins
#ifdef BUTTON_PIN
        pinMode(manualOverridePin, INPUT_PULLUP);
        Serial.printf("Manual override button initialized on pin %d\n", manualOverridePin);
#endif

#ifdef ACCEPT_BUTTON_PIN
        pinMode(acceptPin, INPUT_PULLUP);
        Serial.printf("Accept button initialized on pin %d\n", acceptPin);
#endif

#ifdef REJECT_BUTTON_PIN
        pinMode(rejectPin, INPUT_PULLUP);
        Serial.printf("Reject button initialized on pin %d\n", rejectPin);
#endif

        return true;
    }
    
    /**
     * Update button states (should be called in each loop iteration)
     */
    void update() {
        // Reset button event flags
        manualOverridePressed = false;
        acceptPressed = false;
        rejectPressed = false;
        
        // Read and process manual override button
#ifdef BUTTON_PIN
        int manualOverrideReading = digitalRead(manualOverridePin);
        
        if (manualOverrideReading != lastManualOverrideState) {
            lastManualOverrideDebounceTime = millis();
        }
        
        if ((millis() - lastManualOverrideDebounceTime) > BUTTON_DEBOUNCE_DELAY) {
            if (manualOverrideReading != manualOverrideState) {
                manualOverrideState = manualOverrideReading;
                
                if (manualOverrideState == LOW) { // Button pressed (LOW due to INPUT_PULLUP)
                    manualOverridePressed = true;
                    Serial.println("Manual override button pressed");
                }
            }
        }
        
        lastManualOverrideState = manualOverrideReading;
#endif

        // Read and process accept button
#ifdef ACCEPT_BUTTON_PIN
        int acceptReading = digitalRead(acceptPin);
        
        if (acceptReading != lastAcceptState) {
            lastAcceptDebounceTime = millis();
        }
        
        if ((millis() - lastAcceptDebounceTime) > BUTTON_DEBOUNCE_DELAY) {
            if (acceptReading != acceptState) {
                acceptState = acceptReading;
                
                if (acceptState == LOW) { // Button pressed (LOW due to INPUT_PULLUP)
                    acceptPressed = true;
                    Serial.println("Accept button pressed");
                }
            }
        }
        
        lastAcceptState = acceptReading;
#endif

        // Read and process reject button
#ifdef REJECT_BUTTON_PIN
        int rejectReading = digitalRead(rejectPin);
        
        if (rejectReading != lastRejectState) {
            lastRejectDebounceTime = millis();
        }
        
        if ((millis() - lastRejectDebounceTime) > BUTTON_DEBOUNCE_DELAY) {
            if (rejectReading != rejectState) {
                rejectState = rejectReading;
                
                if (rejectState == LOW) { // Button pressed (LOW due to INPUT_PULLUP)
                    rejectPressed = true;
                    Serial.println("Reject button pressed");
                }
            }
        }
        
        lastRejectState = rejectReading;
#endif
    }
    
    /**
     * Check if the manual override button was pressed in the last update
     * @return true if pressed, false otherwise
     */
    bool wasManualOverridePressed() const {
        return manualOverridePressed;
    }
    
    /**
     * Check if the accept button was pressed in the last update
     * @return true if pressed, false otherwise
     */
    bool wasAcceptPressed() const {
        return acceptPressed;
    }
    
    /**
     * Check if the reject button was pressed in the last update
     * @return true if pressed, false otherwise
     */
    bool wasRejectPressed() const {
        return rejectPressed;
    }
};

#endif // BUTTON_MANAGER_H 