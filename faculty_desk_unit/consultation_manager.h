/**
 * ConsultEase - Consultation Manager
 * 
 * This module handles consultation-related functionality for the Faculty Desk Unit,
 * including request processing, status tracking, and response generation.
 */

#ifndef CONSULTATION_MANAGER_H
#define CONSULTATION_MANAGER_H

#include <ArduinoJson.h>
#include "config.h"
#include "faculty_constants.h"
#include "display_manager.h"
#include "network_manager.h"

class ConsultationManager {
private:
    // Current consultation state
    long currentConsultationId;
    String currentConsultationStatus;
    char currentStudentName[50];
    char currentRequestMessage[MAX_MESSAGE_SIZE];
    bool pendingRequest;
    DisplayManager* display;
    NetworkManager* network;

public:
    /**
     * Constructor
     */
    ConsultationManager(DisplayManager* disp, NetworkManager* net) :
        currentConsultationId(-1),
        currentConsultationStatus(CONSULT_STATUS_UNKNOWN),
        pendingRequest(false),
        display(disp),
        network(net)
    {
        memset(currentStudentName, 0, sizeof(currentStudentName));
        memset(currentRequestMessage, 0, sizeof(currentRequestMessage));
    }
    
    /**
     * Initialize the consultation manager
     * @return true if successful, false otherwise
     */
    bool initialize() {
        Serial.println("Initializing Consultation Manager...");
        return true;
    }
    
    /**
     * Process a consultation request message
     * @param payload The JSON payload of the request
     * @return true if successfully processed, false otherwise
     */
    bool processConsultationRequest(const char* payload) {
        // Parse the JSON message
        StaticJsonDocument<512> doc;
        DeserializationError error = deserializeJson(doc, payload);
        
        if (error) {
            Serial.print("Failed to parse consultation request: ");
            Serial.println(error.c_str());
            return false;
        }
        
        // Check if this request is for this faculty
        const char* targetFacultyId = doc["faculty_id"];
        if (targetFacultyId && strcmp(targetFacultyId, FACULTY_ID) != 0) {
            Serial.println("Request is for a different faculty");
            return false;
        }
        
        // Extract consultation information
        long consultationId = doc["consultation_id"] | doc["id"]; // Support both field names
        if (consultationId <= 0) {
            Serial.println("Invalid consultation ID");
            return false;
        }
        
        currentConsultationId = consultationId;
        
        // Get student name
        const char* studentName = doc["student_name"];
        if (studentName) {
            strncpy(currentStudentName, studentName, sizeof(currentStudentName) - 1);
            currentStudentName[sizeof(currentStudentName) - 1] = '\0';
        } else {
            strcpy(currentStudentName, "Unknown Student");
        }
        
        // Get the status
        const char* status = doc["consultation_status"];
        if (status) {
            if (isValidConsultationStatus(status)) {
                currentConsultationStatus = status;
            } else {
                currentConsultationStatus = CONSULT_STATUS_UNKNOWN;
                Serial.print("Invalid consultation status: ");
                Serial.println(status);
                display->displaySystemStatus("Invalid status received");
            }
        } else {
            currentConsultationStatus = CONSULT_STATUS_PENDING; // Default status
        }
        
        // Get the message content
        const char* requestMsg = NULL;
        
        // First check for a formatted message field
        if (doc.containsKey("message")) {
            requestMsg = doc["message"];
        } 
        // Then check for request_message field
        else if (doc.containsKey("request_message")) {
            requestMsg = doc["request_message"];
        }
        
        if (requestMsg) {
            strncpy(currentRequestMessage, requestMsg, sizeof(currentRequestMessage) - 1);
            currentRequestMessage[sizeof(currentRequestMessage) - 1] = '\0';
        } else {
            strcpy(currentRequestMessage, "No message provided");
        }
        
        // Set pending request flag
        pendingRequest = true;
        
        // Format and display the message
        char displayMessage[MAX_DISPLAY_MESSAGE_SIZE];
        snprintf(displayMessage, sizeof(displayMessage),
                "Request ID: %ld\nStatus: %s\nStudent: %s\nMessage: %s",
                currentConsultationId,
                currentConsultationStatus.c_str(),
                currentStudentName,
                currentRequestMessage);
        
        display->displayMessage(displayMessage);
        display->displaySystemStatus("New consultation request received");
        
        return true;
    }
    
    /**
     * Validate consultation status
     * @param status The status to validate
     * @return true if valid, false otherwise
     */
    bool isValidConsultationStatus(const char* status) {
        return strcmp(status, CONSULT_STATUS_PENDING) == 0 ||
               strcmp(status, CONSULT_STATUS_ACCEPTED) == 0 ||
               strcmp(status, CONSULT_STATUS_STARTED) == 0 ||
               strcmp(status, CONSULT_STATUS_COMPLETED) == 0 ||
               strcmp(status, CONSULT_STATUS_CANCELLED) == 0 ||
               strcmp(status, CONSULT_STATUS_REJECTED) == 0 ||
               strcmp(status, CONSULT_STATUS_UNKNOWN) == 0;
    }
    
    /**
     * Accept the current consultation request
     * @return true if successful, false otherwise
     */
    bool acceptConsultation() {
        if (currentConsultationId <= 0 || currentConsultationStatus != CONSULT_STATUS_PENDING) {
            display->displaySystemStatus("No pending request to accept");
            return false;
        }
        
        bool result = network->publishConsultationResponse(currentConsultationId, CONSULT_ACTION_ACCEPT);
        
        if (result) {
            currentConsultationStatus = CONSULT_STATUS_ACCEPTED;
            display->displaySystemStatus("Request accepted");
            
            // Update the displayed message
            char displayMessage[MAX_DISPLAY_MESSAGE_SIZE];
            snprintf(displayMessage, sizeof(displayMessage),
                    "Request ID: %ld\nStatus: ACCEPTED\nStudent: %s\nMessage: %s",
                    currentConsultationId,
                    currentStudentName,
                    currentRequestMessage);
            
            display->displayMessage(displayMessage);
        } else {
            display->displaySystemStatus("Failed to accept request");
        }
        
        return result;
    }
    
    /**
     * Reject the current consultation request
     * @return true if successful, false otherwise
     */
    bool rejectConsultation() {
        if (currentConsultationId <= 0 || currentConsultationStatus != CONSULT_STATUS_PENDING) {
            display->displaySystemStatus("No pending request to reject");
            return false;
        }
        
        bool result = network->publishConsultationResponse(currentConsultationId, CONSULT_ACTION_REJECT);
        
        if (result) {
            // Clear consultation data after rejection
            resetConsultation();
            display->displaySystemStatus("Request rejected");
            display->displayMessage("No active consultation");
        } else {
            display->displaySystemStatus("Failed to reject request");
        }
        
        return result;
    }
    
    /**
     * Start the current consultation
     * @return true if successful, false otherwise
     */
    bool startConsultation() {
        if (currentConsultationId <= 0 || currentConsultationStatus != CONSULT_STATUS_ACCEPTED) {
            display->displaySystemStatus("No accepted request to start");
            return false;
        }
        
        bool result = network->publishConsultationResponse(currentConsultationId, CONSULT_ACTION_START);
        
        if (result) {
            currentConsultationStatus = CONSULT_STATUS_STARTED;
            display->displaySystemStatus("Consultation started");
            
            // Update the displayed message
            char displayMessage[MAX_DISPLAY_MESSAGE_SIZE];
            snprintf(displayMessage, sizeof(displayMessage),
                    "Request ID: %ld\nStatus: STARTED\nStudent: %s\nMessage: %s",
                    currentConsultationId,
                    currentStudentName,
                    currentRequestMessage);
            
            display->displayMessage(displayMessage);
        } else {
            display->displaySystemStatus("Failed to start consultation");
        }
        
        return result;
    }
    
    /**
     * Complete the current consultation
     * @return true if successful, false otherwise
     */
    bool completeConsultation() {
        if (currentConsultationId <= 0 || currentConsultationStatus != CONSULT_STATUS_STARTED) {
            display->displaySystemStatus("No active consultation to complete");
            return false;
        }
        
        bool result = network->publishConsultationResponse(currentConsultationId, CONSULT_ACTION_COMPLETE);
        
        if (result) {
            // Clear consultation data after completion
            resetConsultation();
            display->displaySystemStatus("Consultation completed");
            display->displayMessage("No active consultation");
        } else {
            display->displaySystemStatus("Failed to complete consultation");
        }
        
        return result;
    }
    
    /**
     * Cancel the current consultation
     * @return true if successful, false otherwise
     */
    bool cancelConsultation() {
        if (currentConsultationId <= 0 || 
            (currentConsultationStatus != CONSULT_STATUS_ACCEPTED && 
             currentConsultationStatus != CONSULT_STATUS_STARTED)) {
            display->displaySystemStatus("No consultation to cancel");
            return false;
        }
        
        bool result = network->publishConsultationResponse(currentConsultationId, CONSULT_ACTION_CANCEL);
        
        if (result) {
            // Clear consultation data after cancellation
            resetConsultation();
            display->displaySystemStatus("Consultation cancelled");
            display->displayMessage("No active consultation");
        } else {
            display->displaySystemStatus("Failed to cancel consultation");
        }
        
        return result;
    }
    
    /**
     * Reset consultation data
     */
    void resetConsultation() {
        currentConsultationId = -1;
        currentConsultationStatus = CONSULT_STATUS_UNKNOWN;
        memset(currentStudentName, 0, sizeof(currentStudentName));
        memset(currentRequestMessage, 0, sizeof(currentRequestMessage));
        pendingRequest = false;
    }
    
    /**
     * Check if there is a pending request
     * @return true if there is a pending request, false otherwise
     */
    bool hasPendingRequest() const {
        return pendingRequest && currentConsultationId > 0;
    }
    
    /**
     * Get the current consultation ID
     * @return The current consultation ID, or -1 if none
     */
    long getCurrentConsultationId() const {
        return currentConsultationId;
    }
    
    /**
     * Get the current consultation status
     * @return The current consultation status
     */
    const String& getCurrentConsultationStatus() const {
        return currentConsultationStatus;
    }
    
    /**
     * Handle consultation action buttons
     * @param acceptPressed Whether the accept button was pressed
     * @param rejectPressed Whether the reject button was pressed
     * @return true if an action was taken, false otherwise
     */
    bool handleConsultationActionButtons(bool acceptPressed, bool rejectPressed) {
        if (acceptPressed) {
            Serial.println("Accept/Start/Complete button pressed");
            
            if (currentConsultationId <= 0) {
                display->displaySystemStatus("No active consultation");
                return false;
            }
            
            if (currentConsultationStatus == CONSULT_STATUS_PENDING) {
                return acceptConsultation();
            } else if (currentConsultationStatus == CONSULT_STATUS_ACCEPTED) {
                return startConsultation();
            } else if (currentConsultationStatus == CONSULT_STATUS_STARTED) {
                return completeConsultation();
            } else {
                char statusBuffer[100];
                snprintf(statusBuffer, sizeof(statusBuffer),
                        "No valid action for status: %s",
                        currentConsultationStatus.c_str());
                display->displaySystemStatus(statusBuffer);
                return false;
            }
        }
        
        if (rejectPressed) {
            Serial.println("Reject/Cancel button pressed");
            
            if (currentConsultationId <= 0) {
                display->displaySystemStatus("No active consultation");
                return false;
            }
            
            if (currentConsultationStatus == CONSULT_STATUS_PENDING) {
                return rejectConsultation();
            } else if (currentConsultationStatus == CONSULT_STATUS_ACCEPTED || 
                      currentConsultationStatus == CONSULT_STATUS_STARTED) {
                return cancelConsultation();
            } else {
                char statusBuffer[100];
                snprintf(statusBuffer, sizeof(statusBuffer),
                        "No valid action for status: %s",
                        currentConsultationStatus.c_str());
                display->displaySystemStatus(statusBuffer);
                return false;
            }
        }
        
        return false;
    }
};

#endif // CONSULTATION_MANAGER_H 