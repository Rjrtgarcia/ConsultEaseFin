import logging
import json
import time
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from central_system.models.base import session_scope, db_operation_with_retry
from central_system.models.faculty import Faculty
from central_system.services.mqtt_service import get_mqtt_service
from central_system.utils.mqtt_topics import (
    get_faculty_status_topic,
    get_faculty_request_topic,
    FACULTY_STATUS_PATTERN,
    FACULTY_AVAILABILITY_PATTERN,
    LEGACY_FACULTY_STATUS_TOPIC
)
from central_system.config import get_config

logger = logging.getLogger(__name__)


class FacultyController:
    """Controller for faculty operations."""

    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of FacultyController."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize the faculty controller."""
        self.mqtt_service = get_mqtt_service()
        self.config = get_config()

        # Subscribe to faculty status updates
        self.mqtt_service.subscribe(
            FACULTY_STATUS_PATTERN,
            handler=self.handle_faculty_status_update)
        self.mqtt_service.subscribe(
            FACULTY_AVAILABILITY_PATTERN,
            handler=self.handle_faculty_availability_update)
            
        # Subscribe to legacy topics for backward compatibility
        self.mqtt_service.subscribe(
            LEGACY_FACULTY_STATUS_TOPIC,
            handler=self.handle_faculty_status_update)

        logger.info("FacultyController initialized")

    def handle_faculty_status_update(self, topic, payload):
        """Handle faculty status updates from MQTT."""
        try:
            # Parse the payload
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')

            data = json.loads(payload)

            # Extract faculty_id from topic or payload
            faculty_id = None

            # Try to get faculty_id from topic first
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3 and topic_parts[1] == 'faculty':
                try:
                    faculty_id = int(topic_parts[2])
                except (ValueError, IndexError):
                    pass

            # If not found in topic, try payload
            if faculty_id is None and 'faculty_id' in data:
                try:
                    faculty_id = int(data['faculty_id'])
                except (ValueError, TypeError):
                    logger.error(f"Invalid faculty_id in payload: {data.get('faculty_id')}")
                    return

            if faculty_id is None:
                logger.error(f"Could not determine faculty_id from topic {topic} or payload {data}")
                return

            # Determine presence status based on payload format
            available = False
            ble_presence = False
            in_grace_period = False
            grace_period_remaining = 0
            
            # Handle different payload formats
            if 'present' in data:
                # New format
                available = data.get('present', False)
                ble_presence = data.get('present', False)  # Use same value if ble_presence not specified
                
                # Check for grace period information
                if 'grace_period_remaining' in data:
                    in_grace_period = True
                    grace_period_remaining = data.get('grace_period_remaining', 0)
                    logger.debug(f"Faculty {faculty_id} in grace period. Remaining: {grace_period_remaining}ms")
            
            elif 'available' in data:
                # Alternative format
                available = data.get('available', False)
                ble_presence = data.get('ble_presence', available)
            
            elif 'status' in data:
                # Legacy format - just look at status string
                status_str = data.get('status', '').upper()
                available = 'AVAILABLE' in status_str
                ble_presence = 'AVAILABLE' in status_str
            
            # Update faculty status in database with grace period info if available
            self.update_faculty_status(faculty_id, available, ble_presence, in_grace_period, grace_period_remaining)

        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from faculty status update: {payload}")
        except Exception as e:
            logger.error(f"Error handling faculty status update: {e}", exc_info=True)

    def handle_faculty_availability_update(self, topic, payload):
        """Handle faculty availability updates from MQTT."""
        try:
            # Parse the payload
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')

            data = json.loads(payload)

            # Extract faculty_id from topic
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3 and topic_parts[1] == 'faculty':
                try:
                    faculty_id = int(topic_parts[2])

                    # Update faculty availability in database
                    available = data.get('available', False)
                    self.update_faculty_availability(faculty_id, available)

                except (ValueError, IndexError):
                    logger.error(f"Could not extract faculty_id from topic: {topic}")

        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from faculty availability update: {payload}")
        except Exception as e:
            logger.error(f"Error handling faculty availability update: {e}", exc_info=True)

    @db_operation_with_retry
    def update_faculty_status(self, faculty_id, available, ble_presence, 
                              in_grace_period=False, grace_period_remaining=0):
        """Update faculty status in the database."""
        with session_scope() as session:
            faculty = session.query(Faculty).filter_by(id=faculty_id).first()

            if faculty:
                # If faculty has always_available set, respect that setting
                if faculty.always_available:
                    available = True
                
                # Update the status fields
                faculty.is_available = available
                faculty.ble_presence_detected = ble_presence
                faculty.last_status_update = datetime.now()
                
                # Update grace period status if faculty has entered or exited grace period
                if in_grace_period:
                    faculty.update_grace_period_status(True, grace_period_remaining)
                elif faculty.in_grace_period:  # If was in grace period but now isn't
                    faculty.update_grace_period_status(False)
                
                # Additional logging for grace period
                if in_grace_period:
                    logger.info(
                        f"Faculty {faculty_id} in grace period: remaining {grace_period_remaining}ms")

                logger.info(
                    f"Updated faculty {faculty_id} status: available={available}, ble_presence={ble_presence}")
            else:
                logger.warning(f"Faculty with ID {faculty_id} not found in database")

    @db_operation_with_retry
    def update_faculty_availability(self, faculty_id, available):
        """Update faculty availability in the database."""
        with session_scope() as session:
            faculty = session.query(Faculty).filter_by(id=faculty_id).first()

            if faculty:
                # If faculty has always_available set, respect that setting
                if faculty.always_available:
                    available = True
                    
                faculty.is_available = available
                faculty.last_status_update = datetime.now()

                logger.info(f"Updated faculty {faculty_id} availability: {available}")
            else:
                logger.warning(f"Faculty with ID {faculty_id} not found in database")

    def get_all_faculty(self):
        """Get all faculty from the database."""
        try:
            with session_scope() as session:
                faculty_list = session.query(Faculty).all()

                # Convert to list of dictionaries
                result = []
                for faculty in faculty_list:
                    result.append({
                        'id': faculty.id,
                        'name': faculty.name,
                        'department': faculty.department,
                        'is_available': faculty.is_available,
                        'ble_presence_detected': faculty.ble_presence_detected,
                        'last_status_update': faculty.last_status_update.isoformat() if faculty.last_status_update else None
                    })

                return result
        except SQLAlchemyError as e:
            logger.error(f"Database error getting all faculty: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting all faculty: {e}")
            return []

    def get_faculty_by_id(self, faculty_id):
        """Get a faculty member by their ID."""
        try:
            with session_scope() as session:
                faculty = session.query(Faculty).filter_by(id=faculty_id).first()

                if faculty:
                    return {
                        'id': faculty.id,
                        'name': faculty.name,
                        'department': faculty.department,
                        'is_available': faculty.is_available,
                        'ble_presence_detected': faculty.ble_presence_detected,
                        'last_status_update': faculty.last_status_update.isoformat() if faculty.last_status_update else None
                    }
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting faculty by ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting faculty by ID: {e}")
            return None

    def get_available_faculty(self):
        """Get all available faculty."""
        try:
            with session_scope() as session:
                faculty_list = session.query(Faculty).filter_by(is_available=True).all()

                # Convert to list of dictionaries
                result = []
                for faculty in faculty_list:
                    result.append({
                        'id': faculty.id,
                        'name': faculty.name,
                        'department': faculty.department,
                        'ble_presence_detected': faculty.ble_presence_detected,
                        'last_status_update': faculty.last_status_update.isoformat() if faculty.last_status_update else None
                    })

                return result
        except SQLAlchemyError as e:
            logger.error(f"Database error getting available faculty: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting available faculty: {e}")
            return []

    @db_operation_with_retry
    def add_faculty(self, name, department, rfid_uid=None, ble_id=None):
        """Add a new faculty member."""
        with session_scope() as session:
            # Check if faculty with same name and department already exists
            existing = session.query(Faculty).filter_by(name=name, department=department).first()
            if existing:
                logger.warning(
                    f"Faculty with name '{name}' in department '{department}' already exists")
                return existing.id

            # Create new faculty
            faculty = Faculty(
                name=name,
                department=department,
                rfid_uid=rfid_uid,
                ble_id=ble_id,
                is_available=False,
                ble_presence_detected=False,
                last_status_update=datetime.now()
            )

            session.add(faculty)
            session.flush()  # Get the ID

            logger.info(f"Added new faculty: {name} (ID: {faculty.id})")
            return faculty.id

    @db_operation_with_retry
    def update_faculty(self, faculty_id, name=None, department=None, rfid_uid=None, ble_id=None):
        """Update a faculty member."""
        with session_scope() as session:
            faculty = session.query(Faculty).filter_by(id=faculty_id).first()

            if faculty:
                if name is not None:
                    faculty.name = name
                if department is not None:
                    faculty.department = department
                if rfid_uid is not None:
                    faculty.rfid_uid = rfid_uid
                if ble_id is not None:
                    faculty.ble_id = ble_id

                logger.info(f"Updated faculty ID {faculty_id}")
                return True
            else:
                logger.warning(f"Faculty with ID {faculty_id} not found for update")
                return False

    @db_operation_with_retry
    def delete_faculty(self, faculty_id):
        """Delete a faculty member."""
        with session_scope() as session:
            faculty = session.query(Faculty).filter_by(id=faculty_id).first()

            if faculty:
                session.delete(faculty)
                logger.info(f"Deleted faculty ID {faculty_id}")
                return True
            else:
                logger.warning(f"Faculty with ID {faculty_id} not found for deletion")
                return False

    def send_consultation_request(self, faculty_id, consultation_data):
        """Send a consultation request to a faculty member via MQTT."""
        try:
            # Check if faculty exists and is available
            faculty = self.get_faculty_by_id(faculty_id)
            if not faculty:
                logger.error(f"Cannot send request to non-existent faculty ID {faculty_id}")
                return False

            if not faculty.get('is_available', False):
                logger.warning(f"Faculty ID {faculty_id} is not available for consultation")
                return False

            # Format message for faculty desk unit
            message = self._format_consultation_request(consultation_data)

            # Send the request via MQTT
            topic = get_faculty_request_topic(faculty_id)
            success = self.mqtt_service.publish(topic, json.dumps(message), qos=1)

            if success:
                logger.info(f"Sent consultation request to faculty ID {faculty_id}")
            else:
                logger.error(f"Failed to send consultation request to faculty ID {faculty_id}")

            return success
        except Exception as e:
            logger.error(f"Error sending consultation request: {e}", exc_info=True)
            return False

    def _format_consultation_request(self, consultation_data):
        """Format consultation data for the faculty desk unit."""
        # Extract required fields
        student_name = consultation_data.get('student_name', 'Unknown Student')
        student_id = consultation_data.get('student_id')
        consultation_id = consultation_data.get('id')
        request_message = consultation_data.get('request_message', '')
        course_code = consultation_data.get('course_code', '')

        # Create a formatted message for display
        display_message = f"Student: {student_name}\n"
        if course_code:
            display_message += f"Course: {course_code}\n"
        display_message += f"Request: {request_message}"

        # Create the full payload
        formatted_data = {
            'consultation_id': consultation_id,
            'student_id': student_id,
            'student_name': student_name,
            'course_code': course_code,
            'request_message': request_message,
            'message': display_message,  # Formatted for display
            'timestamp': time.time()
        }

        return formatted_data

# Helper function to get the singleton instance


def get_faculty_controller():
    """Get the singleton instance of FacultyController."""
    return FacultyController.instance()
