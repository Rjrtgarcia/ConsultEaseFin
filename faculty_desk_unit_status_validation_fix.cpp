// Add these constants at the top of the file (global scope)
// Consultation status constants
const char* CONSULT_STATUS_PENDING = "pending";
const char* CONSULT_STATUS_ACCEPTED = "accepted"; 
const char* CONSULT_STATUS_STARTED = "started";
const char* CONSULT_STATUS_COMPLETED = "completed";
const char* CONSULT_STATUS_CANCELLED = "cancelled";
const char* CONSULT_STATUS_UNKNOWN = "unknown";

// Add this validation function before setup()
/**
 * Validates if the provided status string is one of the known consultation statuses
 * @param status The status string to validate
 * @return true if valid, false otherwise
 */
bool isValidConsultationStatus(const String& status) {
  return status == CONSULT_STATUS_PENDING ||
         status == CONSULT_STATUS_ACCEPTED ||
         status == CONSULT_STATUS_STARTED ||
         status == CONSULT_STATUS_COMPLETED ||
         status == CONSULT_STATUS_CANCELLED;
}

// Replace the current validation code around line 189 with this:
// Original code:
/*
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
*/

// Improved validation code:
if (doc.containsKey("consultation_status")) {
  // Validate the field exists and is a string
  if (doc["consultation_status"].is<const char*>()) {
    current_consultation_status = doc["consultation_status"].as<String>();
    
    // Validate the status value
    if (!isValidConsultationStatus(current_consultation_status)) {
      Serial.println("Unknown consultation status: " + current_consultation_status);
      current_consultation_status = CONSULT_STATUS_UNKNOWN;
      // Update display to show error
      displaySystemStatus("Invalid consultation status received");
    }
  } else {
    Serial.println("consultation_status field is not a string");
    current_consultation_status = CONSULT_STATUS_UNKNOWN;
    displaySystemStatus("Invalid status format received");
  }
} else {
  // Field is missing entirely
  Serial.println("consultation_status field is missing");
  current_consultation_status = CONSULT_STATUS_UNKNOWN;
  displaySystemStatus("Missing status information");
}

// Also update the handleConsultationActionButtons function to use the constants
// Example:
if (current_consultation_status == CONSULT_STATUS_PENDING) {
  action = "accepted";
  displayMsgAction = "ACCEPTED";
} else if (current_consultation_status == CONSULT_STATUS_ACCEPTED) {
  action = "started";
  displayMsgAction = "STARTED";
} else if (current_consultation_status == CONSULT_STATUS_STARTED) {
  action = "completed";
  displayMsgAction = "COMPLETED";
} 