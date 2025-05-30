/**
 * ConsultEase - Faculty Constants
 * 
 * This file provides standardized faculty-related constants and
 * ensures consistent handling of faculty IDs between components.
 */

#ifndef FACULTY_CONSTANTS_H
#define FACULTY_CONSTANTS_H

// Faculty ID Format Types - To ensure consistent handling
// The system should consistently use ONE of these formats:

// Option 1: String IDs (e.g., "faculty_001")
// This is the format currently used in the system
// Faculty ID should be a string in all messages and topics

// Option 2: Numeric IDs (e.g., 1, 2, 3)
// If changing to numeric IDs, modify FACULTY_ID in config.h accordingly
// and update all topic handlers to convert between string/number as needed

// Faculty Status Definitions
#define FACULTY_STATUS_AVAILABLE "available"
#define FACULTY_STATUS_UNAVAILABLE "unavailable"
#define FACULTY_STATUS_IN_CONSULTATION "in_consultation"
#define FACULTY_STATUS_AWAY "away"
#define FACULTY_STATUS_UNKNOWN "unknown"

// Consultation Status Definitions
#define CONSULT_STATUS_PENDING "pending"
#define CONSULT_STATUS_ACCEPTED "accepted"
#define CONSULT_STATUS_STARTED "started"
#define CONSULT_STATUS_COMPLETED "completed"
#define CONSULT_STATUS_CANCELLED "cancelled"
#define CONSULT_STATUS_REJECTED "rejected"
#define CONSULT_STATUS_UNKNOWN "unknown"

// Actions for consultation responses
#define CONSULT_ACTION_ACCEPT "accepted"
#define CONSULT_ACTION_REJECT "rejected_by_faculty" 
#define CONSULT_ACTION_START "started"
#define CONSULT_ACTION_COMPLETE "completed"
#define CONSULT_ACTION_CANCEL "cancelled_by_faculty"

// Faculty information
#define FACULTY_ID "F12345"              // Unique faculty identifier in the system
#define FACULTY_NAME "Dr. John Smith"    // Faculty name for display purposes
#define FACULTY_DEPARTMENT "Computer Science" // Faculty department
#define FACULTY_OFFICE "Room 302"        // Faculty office location
#define FACULTY_EMAIL "jsmith@university.edu" // Faculty email address

// Faculty BLE beacon MAC address (used for presence detection)
#define FACULTY_BEACON_MAC "11:22:33:44:55:66"  // MAC address of faculty's mobile device or dedicated beacon

// Faculty-specific MQTT topics (using the standard format)
char FACULTY_STATUS_TOPIC[50];   // Will be set to consultease/faculty/{FACULTY_ID}/status
char FACULTY_REQUESTS_TOPIC[50]; // Will be set to consultease/faculty/{FACULTY_ID}/requests
char FACULTY_RESPONSES_TOPIC[50]; // Will be set to consultease/faculty/{FACULTY_ID}/responses

// Faculty working hours (24-hour format)
#define FACULTY_WORKING_HOURS_START 8   // 8:00 AM
#define FACULTY_WORKING_HOURS_END 17    // 5:00 PM

// Faculty consultation schedule - days of the week when faculty is available
// 0 = Sunday, 1 = Monday, 2 = Tuesday, etc.
#define FACULTY_AVAILABLE_DAYS {1, 2, 3, 4, 5} // Monday through Friday

// Default faculty availability settings
#define FACULTY_DEFAULT_AVAILABLE true    // Faculty is available by default during working hours
#define FACULTY_ALWAYS_AVAILABLE false    // Override BLE detection and always show as available

// Faculty consultation parameters
#define FACULTY_MAX_CONSULTATIONS 5      // Maximum number of consultations to queue
#define FACULTY_CONSULTATION_DURATION 30 // Default consultation duration in minutes

#endif // FACULTY_CONSTANTS_H 