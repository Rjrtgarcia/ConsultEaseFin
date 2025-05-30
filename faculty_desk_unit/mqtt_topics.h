/**
 * ConsultEase - MQTT Topic Definitions
 * 
 * This file provides standardized MQTT topic definitions that match
 * the central system's mqtt_topics.py file structure.
 */

#ifndef MQTT_TOPICS_H
#define MQTT_TOPICS_H

// Base topic prefix for the ConsultEase system
#define BASE_TOPIC "consultease"

// System-wide topics
#define SYSTEM_STATUS_TOPIC BASE_TOPIC "/system/status"
#define SYSTEM_NOTIFICATION_TOPIC BASE_TOPIC "/system/notification"

// Faculty topics (general)
#define FACULTY_STATUS_TOPIC_GENERAL BASE_TOPIC "/faculty/status"
#define FACULTY_AVAILABILITY_TOPIC_GENERAL BASE_TOPIC "/faculty/availability"
#define FACULTY_REQUEST_TOPIC_GENERAL BASE_TOPIC "/faculty/request"
#define FACULTY_RESPONSE_TOPIC_GENERAL BASE_TOPIC "/faculty/response"

// Helper macros for faculty-specific topics
#define FACULTY_STATUS_TOPIC(id) BASE_TOPIC "/faculty/" id "/status"
#define FACULTY_AVAILABILITY_TOPIC(id) BASE_TOPIC "/faculty/" id "/availability"
#define FACULTY_REQUEST_TOPIC(id) BASE_TOPIC "/faculty/" id "/request"
#define FACULTY_RESPONSE_TOPIC(id) BASE_TOPIC "/faculty/" id "/response"
#define FACULTY_HEARTBEAT_TOPIC(id) BASE_TOPIC "/faculty/" id "/heartbeat"

// Legacy topics (for backward compatibility)
#define LEGACY_FACULTY_STATUS_TOPIC "professor/status"
#define LEGACY_FACULTY_MESSAGE_TOPIC "professor/messages"

// Desk unit specific topics (legacy faculty 1 hard-coded topics)
#define DESK_UNIT_STATUS_TOPIC "faculty/1/status"
#define DESK_UNIT_MESSAGES_TOPIC "faculty/1/messages"
#define DESK_UNIT_HEARTBEAT_TOPIC "faculty/1/heartbeat"
#define DESK_UNIT_RESPONSES_TOPIC "faculty/1/responses"

// Message types
#define MESSAGE_TYPE_STATUS_UPDATE "status_update"
#define MESSAGE_TYPE_AVAILABILITY_UPDATE "availability_update"
#define MESSAGE_TYPE_CONSULTATION_REQUEST "consultation_request"
#define MESSAGE_TYPE_CONSULTATION_RESPONSE "consultation_response"
#define MESSAGE_TYPE_SYSTEM_NOTIFICATION "system_notification"
#define MESSAGE_TYPE_HEARTBEAT "heartbeat"

#endif // MQTT_TOPICS_H 