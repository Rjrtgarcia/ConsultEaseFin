import logging
import datetime
import time # Added for sleep in create_consultation
from ..services import get_mqtt_service
from ..models.consultation import Consultation, ConsultationStatus # Direct model imports
from ..models.student import Student # Direct model imports
from ..models.faculty import Faculty # Direct model imports
from ..models.base import get_db, close_db, db_operation_with_retry # Corrected imports
from ..utils.mqtt_topics import MQTTTopics
from sqlalchemy.orm import joinedload # Add this import

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # REMOVED
logger = logging.getLogger(__name__)

class ConsultationController:
    """
    Controller for managing consultation requests.
    """
    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the ConsultationController."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        Initialize the consultation controller.
        """
        if ConsultationController._instance is not None:
            raise RuntimeError("ConsultationController is a singleton, use ConsultationController.instance()")

        self.mqtt_service = get_mqtt_service()
        self.callbacks = []
        self._db_retry_decorator = db_operation_with_retry() # Store an instance of the decorator
        ConsultationController._instance = self

    def start(self):
        """
        Start the consultation controller.
        """
        logger.info("Starting Consultation controller")
        if not self.mqtt_service.is_connected:
            self.mqtt_service.connect()

    def stop(self):
        """
        Stop the consultation controller.
        """
        logger.info("Stopping Consultation controller")

    def register_callback(self, callback):
        """
        Register a callback to be called when a consultation status changes.
        """
        self.callbacks.append(callback)
        logger.info(f"Registered Consultation controller callback: {getattr(callback, '__name__', 'unnamed_callback')}")

    def unregister_callback(self, callback):
        """
        Unregister a previously registered callback.

        Args:
            callback (callable): Function to unregister
        """
        try:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
                logger.info(f"Unregistered Consultation controller callback: {getattr(callback, '__name__', 'unknown')}")
            else:
                logger.warning(f"Attempted to unregister a callback that was not found: {getattr(callback, '__name__', 'unknown')}")
        except Exception as e:
            logger.error(f"Error unregistering Consultation controller callback {getattr(callback, '__name__', 'unknown')}: {str(e)}")

    def _notify_callbacks(self, consultation):
        """
        Notify all registered callbacks.
        """
        for callback in self.callbacks:
            try:
                callback(consultation)
            except Exception as e:
                logger.error(f"Error in Consultation controller callback: {str(e)}")

    def _ensure_mqtt_connected(self, operation_description: str = "operation") -> bool:
        """
        Ensures MQTT service is connected, attempting to connect if necessary.
        Includes a timeout for the connection attempt.

        Args:
            operation_description (str): Description of the operation requiring MQTT (for logging).

        Returns:
            bool: True if connected, False otherwise.
        """
        if not self.mqtt_service.is_connected:
            logger.warning(f"MQTT not connected before {operation_description}. Attempting to connect.")
            self.mqtt_service.connect() # connect() should be non-blocking or have its own timeout management
            
            # Allow some time for connection to establish, especially if connect() is async
            # This loop is a fallback/check, assuming connect() initiates connection.
            connect_timeout = 5  # seconds
            start_time = time.time()
            while not self.mqtt_service.is_connected and (time.time() - start_time) < connect_timeout:
                time.sleep(0.1) # Brief pause before re-checking
            
            if not self.mqtt_service.is_connected:
                logger.error(f"MQTT: Failed to connect within timeout before {operation_description}.")
                return False
            logger.info(f"MQTT: Successfully connected before {operation_description}.")
        return True

    @db_operation_with_retry()
    def _create_consultation_in_db(self, db, student_id, faculty_id, request_message, course_code=None):
        """
        Helper to create consultation in DB. `db` is from decorator.
        """
        consultation = Consultation(
            student_id=student_id, faculty_id=faculty_id, request_message=request_message,
            course_code=course_code, status=ConsultationStatus.PENDING,
            requested_at=datetime.datetime.now()
        )
        db.add(consultation)
        # db.flush() # Ensure ID is populated if needed before commit by decorator
        return consultation

    def create_consultation(self, student_id, faculty_id, request_message, course_code=None):
        """
        Create a new consultation request, store in DB, then publish.
        """
        logger.info(f"Attempting to create consultation (Student: {student_id}, Faculty: {faculty_id})")
        consultation = None
        try:
            consultation = self._create_consultation_in_db(student_id, faculty_id, request_message, course_code)
            if consultation and consultation.id: # Check if ID is populated (meaning commit was successful)
                logger.info(f"DB: Created consultation request: {consultation.id}")
                
                if self._ensure_mqtt_connected(f"publishing consultation {consultation.id}"):
                    publish_success = self._publish_consultation_to_mqtt(consultation.id)
                    if publish_success:
                        logger.info(f"MQTT: Successfully published consultation {consultation.id}")
                    else:
                        logger.error(f"MQTT: Failed to publish consultation {consultation.id}. It is saved in DB.")
                else:
                    # _ensure_mqtt_connected already logs the failure to connect
                    logger.error(f"MQTT: Not connected. Consultation {consultation.id} saved in DB but not published.")
                
                # Re-fetch the consultation to ensure all relationships are loaded for signal emission
                loaded_consultation = self.get_consultation_by_id(consultation.id)
                if loaded_consultation:
                    self._notify_callbacks(loaded_consultation)
                    return loaded_consultation
                else:
                    logger.error(f"Failed to re-load consultation {consultation.id} after creation. Callbacks not notified with full data.")
                    # Fallback to returning the original instance, which might lack relationships
                    self._notify_callbacks(consultation)
                    return consultation
            else:
                logger.error(f"DB: Failed to create consultation or retrieve ID after commit.")
                return None
        except Exception as e:
            logger.error(f"Error in create_consultation controller method: {str(e)}")
            # The decorator on _create_consultation_in_db handles DB rollback
            return None

    def _publish_consultation_to_mqtt(self, consultation_id):
        """
        Publish consultation to MQTT. Fetches fresh data for publishing.
        """
        db = get_db()
        try:
            # Fetch the consultation with related objects for publishing
            # No need for force_new=True if this session is short-lived and only for this publish
            consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
            if not consultation:
                logger.error(f"MQTT Publish: Consultation {consultation_id} not found.")
                return False

            student = consultation.student # Assuming relationships are loaded or accessible
            faculty = consultation.faculty
            if not student or not faculty:
                logger.error(f"MQTT Publish: Student or Faculty not found for Consultation {consultation_id}.")
                return False

            # Primary message format for modern faculty desk units (JSON to specific topic)
            message_for_display = f"Student: {student.name}\n"
            if consultation.course_code: message_for_display += f"Course: {consultation.course_code}\n"
            message_for_display += f"Request: {consultation.request_message}"

            payload = {
                'id': consultation.id, 'student_id': student.id, 'student_name': student.name,
                'student_department': student.department, 'faculty_id': faculty.id, 'faculty_name': faculty.name,
                'request_message': consultation.request_message, 'course_code': consultation.course_code,
                'status': consultation.status.value,
                'requested_at': consultation.requested_at.isoformat() if consultation.requested_at else None,
                'message': message_for_display # ESP32 prefers this for direct display
            }
            specific_topic = MQTTTopics.get_faculty_requests_topic(faculty.id)
            success_specific = self.mqtt_service.publish(specific_topic, payload)
            if success_specific: logger.info(f"MQTT: Published to specific topic {specific_topic}")
            else: logger.error(f"MQTT: Failed to publish to specific topic {specific_topic}")

            # Fallback/Legacy: Plain text message to a general legacy topic (if deemed absolutely necessary)
            # Consider phasing this out if all desk units support the specific JSON topic.
            # For now, keeping one legacy publish as per previous intense desire for it.
            legacy_topic = MQTTTopics.LEGACY_FACULTY_MESSAGES
            success_legacy_raw = self.mqtt_service.publish_raw(legacy_topic, message_for_display)
            if success_legacy_raw: logger.info(f"MQTT: Published to legacy raw topic {legacy_topic}")
            else: logger.error(f"MQTT: Failed to publish to legacy raw topic {legacy_topic}")
            
            # Return true if primary specific publish worked, or if legacy fallback worked
            return success_specific or success_legacy_raw 
        except Exception as e:
            logger.error(f"Error in _publish_consultation_to_mqtt for C_ID {consultation_id}: {str(e)}")
            return False
        finally:
            close_db()

    @db_operation_with_retry()
    def update_consultation_status(self, db, consultation_id, status):
        """
        Update consultation status in DB. `db` is from decorator.
        Also handles subsequent MQTT publishing if successful.
        """
        consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
        if not consultation:
            # Error will be handled by decorator (rollback, retry)
            raise ValueError(f"Consultation not found for status update: {consultation_id}")

        consultation.status = status
        if status == ConsultationStatus.ACCEPTED: consultation.accepted_at = datetime.datetime.now()
        elif status == ConsultationStatus.COMPLETED: consultation.completed_at = datetime.datetime.now()
        # db.commit() handled by decorator

        logger.info(f"DB: Updated consultation {consultation.id} to status {status}")
        
        # After successful DB commit (handled by decorator), try to publish
        # This runs outside the decorator's DB transaction, so MQTT failure won't roll back DB change.
        # This is generally desired: DB state is source of truth.
        if self._ensure_mqtt_connected(f"publishing status for C_ID {consultation.id}"):
            publish_success_update = self._publish_consultation_to_mqtt(consultation.id)
            if publish_success_update:
                logger.info(f"MQTT: Published status update for consultation {consultation.id}")
            else:
                logger.error(f"MQTT: Failed to publish status update for {consultation.id}. DB is updated.")
        else:
            # _ensure_mqtt_connected already logs the failure to connect
            logger.error(f"MQTT: Not connected. Status update for {consultation.id} saved in DB but not published.")

        self._notify_callbacks(consultation) # Notify UI, etc.
        return consultation # Return the updated consultation object

    def cancel_consultation(self, consultation_id):
        """
        Cancel a consultation request.
        """
        try:
            return self.update_consultation_status(consultation_id, ConsultationStatus.CANCELLED)
        except Exception as e:
            # update_consultation_status (decorated) will handle logging of DB errors
            logger.error(f"Error in cancel_consultation controller method for C_ID {consultation_id}: {e}")
            return None

    def get_consultations(self, student_id=None, faculty_id=None, status=None):
        """
        Get consultations, optionally filtered.
        Eagerly loads related student and faculty data.
        """
        db = get_db()
        try:
            query = db.query(Consultation).options(
                joinedload(Consultation.student),
                joinedload(Consultation.faculty)
            )
            if student_id:
                query = query.filter(Consultation.student_id == student_id)
            if faculty_id:
                query = query.filter(Consultation.faculty_id == faculty_id)
            if status:
                query = query.filter(Consultation.status == status)
            
            consultations = query.order_by(Consultation.requested_at.desc()).all()
            return consultations
        except Exception as e:
            logger.error(f"Error getting consultations: {str(e)}", exc_info=True)
            return []
        finally:
            close_db()

    def get_consultation_by_id(self, consultation_id):
        """
        Get a consultation by ID.
        Eagerly loads related student and faculty data.
        """
        db = get_db()
        try:
            consultation = db.query(Consultation).options(
                joinedload(Consultation.student),
                joinedload(Consultation.faculty)
            ).filter(Consultation.id == consultation_id).first()
            return consultation
        except Exception as e:
            logger.error(f"Error getting consultation by ID: {str(e)}")
            return None
        finally:
            close_db()

    def test_faculty_desk_connection(self, faculty_id):
        """
        Test the connection to a faculty desk unit by sending a test message.
        """
        db = get_db()
        try:
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
            if not faculty:
                logger.error(f"Faculty not found for test message: {faculty_id}")
                return False
            
            message = f"Test message from ConsultEase central system.\nTimestamp: {datetime.datetime.now().isoformat()}"
            payload = {
                'id': 0, 'student_name': "System Test", 'faculty_name': faculty.name,
                'request_message': message, 'message': message # Ensure message field for ESP32
            }
            
            specific_topic = MQTTTopics.get_faculty_requests_topic(faculty.id)
            success_json = self.mqtt_service.publish(specific_topic, payload)
            
            legacy_topic = MQTTTopics.LEGACY_FACULTY_MESSAGES
            success_raw_legacy = self.mqtt_service.publish_raw(legacy_topic, message)
            
            logger.info(f"Test message sent to faculty {faculty.name}. JSON Specific: {success_json}, Raw Legacy: {success_raw_legacy}")
            return success_json or success_raw_legacy
        except Exception as e:
            logger.error(f"Error testing faculty desk connection: {str(e)}")
            return False
        finally:
            close_db()

    @db_operation_with_retry()
    def accept_consultation_request(self, db, consultation_id: int, faculty_id: int):
        """
        Mark a consultation request as ACCEPTED by the faculty.
        `db` is provided by the decorator.
        """
        logger.info(f"Faculty {faculty_id} attempting to accept consultation {consultation_id}")
        consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

        if not consultation:
            logger.error(f"Accept failed: Consultation {consultation_id} not found.")
            return None
        
        if consultation.faculty_id != faculty_id:
            logger.error(f"Accept failed: Faculty {faculty_id} not authorized for consultation {consultation_id} (belongs to faculty {consultation.faculty_id}).")
            return None

        if consultation.status != ConsultationStatus.PENDING:
            logger.warning(f"Consultation {consultation_id} is already in status {consultation.status.value}, cannot accept again.")
            # Optionally return the consultation if already accepted, or None/error if it was cancelled/completed
            if consultation.status == ConsultationStatus.ACCEPTED:
                return consultation # Or return an error/message indicating it's already accepted
            return None 

        consultation.status = ConsultationStatus.ACCEPTED
        consultation.accepted_at = datetime.datetime.now()
        # db.commit() is handled by the decorator
        logger.info(f"Consultation {consultation_id} status updated to ACCEPTED by faculty {faculty_id}.")
        
        # Re-fetch for callbacks to ensure relationships are loaded
        loaded_consultation = db.query(Consultation).options(joinedload('*_related')).filter(Consultation.id == consultation.id).first()
        self._notify_callbacks(loaded_consultation if loaded_consultation else consultation)
        
        # Notify student
        if loaded_consultation and loaded_consultation.student_id:
            self._notify_student_of_status_change(loaded_consultation)

        return loaded_consultation if loaded_consultation else consultation

    @db_operation_with_retry()
    def reject_consultation_request(self, db, consultation_id: int, faculty_id: int):
        """
        Mark a consultation request as REJECTED by the faculty.
        `db` is provided by the decorator.
        """
        logger.info(f"Faculty {faculty_id} attempting to reject consultation {consultation_id}")
        consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

        if not consultation:
            logger.error(f"Reject failed: Consultation {consultation_id} not found.")
            return None
        
        if consultation.faculty_id != faculty_id:
            logger.error(f"Reject failed: Faculty {faculty_id} not authorized for consultation {consultation_id} (belongs to faculty {consultation.faculty_id}).")
            return None
            
        if consultation.status not in [ConsultationStatus.PENDING, ConsultationStatus.ACCEPTED]:
            logger.warning(f"Consultation {consultation_id} is in status {consultation.status.value}, cannot reject if not PENDING or already ACCEPTED (to change mind). Current status: {consultation.status.value}")
            # If it's already completed or cancelled, can't reject.
            if consultation.status in [ConsultationStatus.COMPLETED, ConsultationStatus.CANCELLED_BY_STUDENT, ConsultationStatus.CANCELLED_BY_FACULTY]:
                 return None
            # Allow rejection if it was PENDING or ACCEPTED (faculty changed their mind before starting)

        consultation.status = ConsultationStatus.REJECTED_BY_FACULTY # Assuming this enum value exists
        # db.commit() is handled by the decorator
        logger.info(f"Consultation {consultation_id} status updated to REJECTED_BY_FACULTY by faculty {faculty_id}.")

        # Re-fetch for callbacks
        loaded_consultation = db.query(Consultation).options(joinedload('*_related')).filter(Consultation.id == consultation.id).first()
        self._notify_callbacks(loaded_consultation if loaded_consultation else consultation)
        
        # Notify student
        if loaded_consultation and loaded_consultation.student_id:
            self._notify_student_of_status_change(loaded_consultation)

        return loaded_consultation if loaded_consultation else consultation

    @db_operation_with_retry()
    def start_consultation(self, db, consultation_id: int, faculty_id: int):
        """
        Mark a consultation as STARTED by the faculty.
        `db` is provided by the decorator.
        """
        logger.info(f"Faculty {faculty_id} attempting to start consultation {consultation_id}")
        consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

        if not consultation:
            logger.error(f"Start failed: Consultation {consultation_id} not found.")
            return None
        if consultation.faculty_id != faculty_id:
            logger.error(f"Start failed: Faculty {faculty_id} not authorized for consultation {consultation_id}.")
            return None
        if consultation.status != ConsultationStatus.ACCEPTED:
            logger.warning(f"Cannot start consultation {consultation_id}: current status is {consultation.status.value}, not ACCEPTED.")
            return None

        consultation.status = ConsultationStatus.STARTED
        # Optionally set a started_at timestamp if your model has one
        logger.info(f"Consultation {consultation_id} status updated to STARTED by faculty {faculty_id}.")
        loaded_consultation = db.query(Consultation).options(joinedload('*_related')).filter(Consultation.id == consultation.id).first()
        self._notify_callbacks(loaded_consultation if loaded_consultation else consultation)
        
        # Notify student
        if loaded_consultation and loaded_consultation.student_id:
            self._notify_student_of_status_change(loaded_consultation)

        return loaded_consultation if loaded_consultation else consultation

    @db_operation_with_retry()
    def complete_consultation(self, db, consultation_id: int, faculty_id: int):
        """
        Mark a consultation as COMPLETED by the faculty.
        `db` is provided by the decorator.
        """
        logger.info(f"Faculty {faculty_id} attempting to complete consultation {consultation_id}")
        consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

        if not consultation:
            logger.error(f"Complete failed: Consultation {consultation_id} not found.")
            return None
        if consultation.faculty_id != faculty_id:
            logger.error(f"Complete failed: Faculty {faculty_id} not authorized for consultation {consultation_id}.")
            return None
        # Allow completion if STARTED or if ACCEPTED (e.g., quick verbal confirmation then complete)
        if consultation.status not in [ConsultationStatus.STARTED, ConsultationStatus.ACCEPTED]:
            logger.warning(f"Cannot complete consultation {consultation_id}: current status is {consultation.status.value}, not STARTED or ACCEPTED.")
            return None

        consultation.status = ConsultationStatus.COMPLETED
        consultation.completed_at = datetime.datetime.now()
        logger.info(f"Consultation {consultation_id} status updated to COMPLETED by faculty {faculty_id}.")
        loaded_consultation = db.query(Consultation).options(joinedload('*_related')).filter(Consultation.id == consultation.id).first()
        self._notify_callbacks(loaded_consultation if loaded_consultation else consultation)
        
        # Notify student
        if loaded_consultation and loaded_consultation.student_id:
            self._notify_student_of_status_change(loaded_consultation)

        return loaded_consultation if loaded_consultation else consultation

    @db_operation_with_retry()
    def cancel_consultation_by_faculty(self, db, consultation_id: int, faculty_id: int):
        """
        Mark a consultation as CANCELLED_BY_FACULTY.
        `db` is provided by the decorator.
        """
        logger.info(f"Faculty {faculty_id} attempting to cancel consultation {consultation_id}")
        consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

        if not consultation:
            logger.error(f"Faculty cancel failed: Consultation {consultation_id} not found.")
            return None
        if consultation.faculty_id != faculty_id:
            logger.error(f"Faculty cancel failed: Faculty {faculty_id} not authorized for consultation {consultation_id}.")
            return None
        
        # Prevent cancelling if already completed or cancelled by student
        if consultation.status in [ConsultationStatus.COMPLETED, ConsultationStatus.CANCELLED_BY_STUDENT, ConsultationStatus.REJECTED_BY_FACULTY]:
            logger.warning(f"Cannot cancel consultation {consultation_id}: current status is {consultation.status.value}.")
            return None # Or return the consultation itself if no state change

        consultation.status = ConsultationStatus.CANCELLED_BY_FACULTY
        # Optionally clear accepted_at or set a cancelled_at timestamp
        logger.info(f"Consultation {consultation_id} status updated to CANCELLED_BY_FACULTY by faculty {faculty_id}.")
        loaded_consultation = db.query(Consultation).options(joinedload('*_related')).filter(Consultation.id == consultation.id).first()
        self._notify_callbacks(loaded_consultation if loaded_consultation else consultation)
        
        # Notify student
        if loaded_consultation and loaded_consultation.student_id:
            self._notify_student_of_status_change(loaded_consultation)

        return loaded_consultation if loaded_consultation else consultation

    def _notify_student_of_status_change(self, consultation: Consultation):
        """
        Publishes a notification to the student about a change in consultation status.
        """
        if not consultation or not consultation.student_id or not consultation.faculty:
            logger.warning(f"_notify_student_of_status_change: Missing data for consultation {consultation.id if consultation else 'Unknown'}")
            return

        try:
            topic = MQTTTopics.get_student_notification_topic(consultation.student_id)
            payload = {
                "type": "consultation_update",
                "consultation_id": consultation.id,
                "new_status": consultation.status.value,
                "faculty_name": consultation.faculty.name,
                "request_message_snippet": (consultation.request_message[:50] + '...') if len(consultation.request_message) > 50 else consultation.request_message,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Create a user-friendly message
            status_text = consultation.status.value.replace("_", " ").title()
            message = f"Consultation with {consultation.faculty.name} has been {status_text}."
            if consultation.status == ConsultationStatus.REJECTED_BY_FACULTY:
                message = f"Consultation with {consultation.faculty.name} was regrettably rejected."
            elif consultation.status == ConsultationStatus.CANCELLED_BY_FACULTY:
                message = f"Consultation with {consultation.faculty.name} has been cancelled by the faculty."
            
            payload["display_message"] = message

            logger.info(f"Notifying student {consultation.student_id} on topic {topic} with payload: {payload}")
            self.mqtt_service.publish(topic, payload, qos=1) # Use QoS 1 for important notifications
        except Exception as e:
            logger.error(f"Error in _notify_student_of_status_change for C_ID {consultation.id}: {e}", exc_info=True)