"""
MQTT topics utility module for ConsultEase system.
Provides constants and helper functions for MQTT topic construction.
"""

# Base topic prefix for the ConsultEase system
BASE_TOPIC = "consultease"

# System-wide topics
SYSTEM_STATUS_TOPIC = f"{BASE_TOPIC}/system/status"
SYSTEM_NOTIFICATION_TOPIC = f"{BASE_TOPIC}/system/notification"

# Faculty topics (general)
FACULTY_STATUS_TOPIC = f"{BASE_TOPIC}/faculty/status"
FACULTY_AVAILABILITY_TOPIC = f"{BASE_TOPIC}/faculty/availability"
FACULTY_REQUEST_TOPIC = f"{BASE_TOPIC}/faculty/request"
FACULTY_RESPONSE_TOPIC = f"{BASE_TOPIC}/faculty/response"

# Helper functions for faculty-specific topics


def get_faculty_status_topic(faculty_id):
    """Get the topic for a specific faculty's status."""
    return f"{BASE_TOPIC}/faculty/{faculty_id}/status"


def get_faculty_availability_topic(faculty_id):
    """Get the topic for a specific faculty's availability."""
    return f"{BASE_TOPIC}/faculty/{faculty_id}/availability"


def get_faculty_request_topic(faculty_id):
    """Get the topic for sending consultation requests to a specific faculty."""
    return f"{BASE_TOPIC}/faculty/{faculty_id}/request"


def get_faculty_response_topic(faculty_id):
    """Get the topic for receiving responses from a specific faculty."""
    return f"{BASE_TOPIC}/faculty/{faculty_id}/response"


def get_faculty_heartbeat_topic(faculty_id):
    """Get the topic for receiving heartbeats from a specific faculty desk unit."""
    return f"{BASE_TOPIC}/faculty/{faculty_id}/heartbeat"


# Wildcard topic patterns (for subscribing)
FACULTY_STATUS_PATTERN = f"{BASE_TOPIC}/faculty/+/status"
FACULTY_AVAILABILITY_PATTERN = f"{BASE_TOPIC}/faculty/+/availability"
FACULTY_REQUEST_PATTERN = f"{BASE_TOPIC}/faculty/+/request"
FACULTY_RESPONSE_PATTERN = f"{BASE_TOPIC}/faculty/+/response"
FACULTY_HEARTBEAT_PATTERN = f"{BASE_TOPIC}/faculty/+/heartbeat"

# Student topics
STUDENT_NOTIFICATION_TOPIC = f"{BASE_TOPIC}/student/notification"


def get_student_notification_topic(student_id):
    """Get the topic for sending notifications to a specific student."""
    return f"{BASE_TOPIC}/student/{student_id}/notification"


# Legacy topics (for backward compatibility)
LEGACY_FACULTY_STATUS_TOPIC = "professor/status"
LEGACY_FACULTY_MESSAGE_TOPIC = "professor/messages"

# Desk unit specific topics (for backward compatibility)
FACULTY_DESK_STATUS_TOPIC = "faculty/1/status"
FACULTY_DESK_MESSAGES_TOPIC = "faculty/1/messages"
FACULTY_DESK_HEARTBEAT_TOPIC = "faculty/1/heartbeat"
FACULTY_DESK_RESPONSES_TOPIC = "faculty/1/responses"

# Message types
MESSAGE_TYPE_STATUS_UPDATE = "status_update"
MESSAGE_TYPE_AVAILABILITY_UPDATE = "availability_update"
MESSAGE_TYPE_CONSULTATION_REQUEST = "consultation_request"
MESSAGE_TYPE_CONSULTATION_RESPONSE = "consultation_response"
MESSAGE_TYPE_SYSTEM_NOTIFICATION = "system_notification"
MESSAGE_TYPE_HEARTBEAT = "heartbeat"
