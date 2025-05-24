import logging
import datetime
from sqlalchemy import or_
from ..services import get_mqtt_service
from ..models.base import get_db, close_db
from ..models.faculty import Faculty
from ..models.base import db_operation_with_retry
from ..utils.mqtt_topics import MQTTTopics

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # REMOVED
logger = logging.getLogger(__name__)

class FacultyController:
    """
    Controller for managing faculty data and status.
    """
    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the FacultyController."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        Initialize the faculty controller.
        """
        if FacultyController._instance is not None:
            raise RuntimeError("FacultyController is a singleton, use FacultyController.instance()")
        
        self.mqtt_service = get_mqtt_service()
        self.callbacks = []
        FacultyController._instance = self

    def start(self):
        """
        Start the faculty controller and subscribe to faculty status updates.
        """
        logger.info("Starting Faculty controller")

        # Subscribe to faculty status updates using standardized topic
        self.mqtt_service.register_topic_handler(
            MQTTTopics.FACULTY_STATUS.format(faculty_id="+"),  # Use MQTTTopics class method
            self.handle_faculty_status_update
        )

        # Connect MQTT service
        if not self.mqtt_service.is_connected:
            self.mqtt_service.connect()

    def stop(self):
        """
        Stop the faculty controller.
        """
        logger.info("Stopping Faculty controller")

    def register_callback(self, callback):
        """
        Register a callback to be called when faculty status changes.

        Args:
            callback (callable): Function that takes a Faculty object as argument
        """
        self.callbacks.append(callback)
        logger.info(f"Registered Faculty controller callback: {getattr(callback, '__name__', 'unnamed_callback')}")

    def unregister_callback(self, callback):
        """
        Unregister a previously registered callback.

        Args:
            callback (callable): Function to unregister
        """
        try:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
                logger.info(f"Unregistered Faculty controller callback: {getattr(callback, '__name__', 'unknown')}")
            else:
                logger.warning(f"Attempted to unregister a callback that was not found: {getattr(callback, '__name__', 'unknown')}")
        except Exception as e:
            logger.error(f"Error unregistering Faculty controller callback {getattr(callback, '__name__', 'unknown')}: {str(e)}")

    def _notify_callbacks(self, faculty):
        """
        Notify all registered callbacks with the updated faculty information.

        Args:
            faculty (Faculty): Updated faculty object
        """
        for callback in self.callbacks:
            try:
                callback(faculty)
            except Exception as e:
                logger.error(f"Error in Faculty controller callback: {str(e)}")

    def handle_faculty_status_update(self, topic, data):
        faculty_id_to_update = None
        new_status_bool = None
        db = get_db()
        try:
            logger.debug(f"MQTT status update: Topic='{topic}', Data='{data}'")
            
            # Try parsing specific topic first: "consultease/faculty/{id}/status"
            if topic.startswith("consultease/faculty/") and topic.endswith("/status"):
                parts = topic.split('/')
                if len(parts) == 4: # Should be ["consultease", "faculty", "{id}", "status"]
                    try:
                        faculty_id_to_update = int(parts[2])
                    except ValueError: 
                        logger.error(f"Invalid faculty ID '{parts[2]}' in topic: {topic}"); return
                    
                    if isinstance(data, dict):
                        if data.get('keychain_connected') is True: new_status_bool = True
                        elif data.get('keychain_disconnected') is True: new_status_bool = False
                        elif 'status' in data and isinstance(data['status'], bool): new_status_bool = data['status']
                    elif isinstance(data, str): # Simple string on specific topic
                        if data.lower() in ["true", "on", "available", "keychain_connected"]: new_status_bool = True
                        elif data.lower() in ["false", "off", "unavailable", "keychain_disconnected"]: new_status_bool = False
                    
                    if new_status_bool is not None:
                         logger.info(f"Parsed specific topic: faculty_id={faculty_id_to_update}, status={new_status_bool}")
                    else:
                        logger.warning(f"Could not determine status from data on specific topic: {topic}, data: {data}")
                else:
                    logger.warning(f"Malformed specific topic received: {topic}")
            else:
                # If it's not the specific topic format we expect, log it as unhandled.
                logger.warning(f"Message on unhandled MQTT topic: {topic}"); return

            if faculty_id_to_update is not None and new_status_bool is not None:
                updated_faculty = self.update_faculty_status_in_db(faculty_id_to_update, new_status_bool)
                if updated_faculty:
                    self._notify_callbacks(updated_faculty)
                    # Consider publishing a system notification about the update
                    system_notification = {
                        "type": "faculty_status_updated",
                        "faculty_id": updated_faculty.id,
                        "name": updated_faculty.name,
                        "status": updated_faculty.status
                    }
                    self.mqtt_service.publish(MQTTTopics.SYSTEM_NOTIFICATIONS, system_notification)
                    logger.info(f"Published system notification for faculty {updated_faculty.id} status change.")
                else:
                    logger.error(f"Failed to update status in DB for faculty_id={faculty_id_to_update}")
            elif topic.startswith("consultease/faculty/") and topic.endswith("/status"): 
                # Only log 'no valid id/status' if it was a specific topic that failed parsing,
                # otherwise the 'unhandled topic' log already covered it.
                logger.warning(f"No valid faculty_id or status determined from topic='{topic}', data='{data}'. No update.")
        
        except Exception as e:
            logger.error(f"Error in handle_faculty_status_update: {e}", exc_info=True)
        finally:
            close_db()

    @db_operation_with_retry()
    def update_faculty_status_in_db(self, db, faculty_id, status_bool):
        """
        Update faculty status in the database. Intended to be called by handle_faculty_status_update.
        `db` is provided by the decorator.
        """
        faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
        if not faculty:
            logger.error(f"DB: Faculty with ID {faculty_id} not found for status update.")
            return None 
        
        if faculty.status == status_bool:
            logger.info(f"DB: Status for faculty {faculty.name} (ID: {faculty.id}) is already {status_bool}. No change.")
            return faculty # Return faculty even if no change, so callbacks can be notified if needed.

        faculty.status = status_bool
        faculty.last_seen = datetime.datetime.now() # Keep last_seen for presence, update on any status change too
        logger.info(f"DB: Updated status for faculty {faculty.name} (ID: {faculty.id}) to {status_bool}")
        return faculty

    def get_all_faculty(self, filter_available=None, search_term=None):
        """
        Get all faculty, optionally filtered by availability or search term.
        """
        db = get_db()
        try:
            query = db.query(Faculty)
            if filter_available is not None:
                query = query.filter(Faculty.status == filter_available)
            if search_term:
                search_val = f"%{search_term}%"
                query = query.filter(or_(Faculty.name.ilike(search_val), Faculty.department.ilike(search_val)))
            faculties = query.all()
            return faculties
        except Exception as e:
            logger.error(f"Error getting faculty list: {str(e)}")
            return []
        finally:
            close_db()

    def get_faculty_by_id(self, faculty_id):
        """
        Get a faculty member by ID.
        """
        db = get_db()
        try:
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
            return faculty
        except Exception as e:
            logger.error(f"Error getting faculty by ID: {str(e)}")
            return None
        finally:
            close_db()

    def get_faculty_by_ble_id(self, ble_id):
        """
        Get a faculty member by BLE ID.
        """
        db = get_db()
        try:
            faculty = db.query(Faculty).filter(Faculty.ble_id == ble_id).first()
            if faculty:
                logger.info(f"Found faculty with BLE ID {ble_id}: {faculty.name} (ID: {faculty.id})")
            else:
                logger.warning(f"No faculty found with BLE ID: {ble_id}")
            return faculty
        except Exception as e:
            logger.error(f"Error getting faculty by BLE ID: {str(e)}")
            return None
        finally:
            close_db()

    @db_operation_with_retry()
    def add_faculty(self, db, name, department, email, ble_id=None, image_path=None, always_available=False): # 'always_available' is present but ignored
        """
        Add a new faculty member. `db` is provided by the decorator.
        The `always_available` parameter is deprecated and its value is ignored. BLE presence dictates availability.
        """
        # Check for existing faculty with the same email or non-empty BLE ID
        existing_faculty_check = or_(Faculty.email == email)
        if ble_id and ble_id.strip() != "": # Only include BLE ID in check if it's not None or empty
            existing_faculty_check = or_(Faculty.email == email, Faculty.ble_id == ble_id)
        
        if db.query(Faculty).filter(existing_faculty_check).first():
            error_msg = f"Faculty with email '{email}'"
            if ble_id and ble_id.strip() != "":
                error_msg += f" or BLE ID '{ble_id}'"
            error_msg += " already exists."
            raise ValueError(error_msg)

        faculty = Faculty(
            name=name, 
            department=department, 
            email=email, 
            ble_id=ble_id if ble_id and ble_id.strip() != "" else None, # Store None if empty/whitespace
            image_path=image_path, 
            status=False,  # New faculty defaults to not available
            always_available=False # Deprecated, set to False
        )
        db.add(faculty)
        # db.commit() and db.refresh(faculty) handled by decorator
        logger.info(f"DB: Added faculty: {faculty.name} (ID: {faculty.id})")
        
        # Publish notification
        try:
            # Ensure faculty ID is available after commit (decorator handles refresh)
            db.flush() # Ensure ID is populated if not already by commit
            notification = {
                'type': 'faculty_added',
                'faculty_id': faculty.id,
                'faculty_name': faculty.name,
                'department': faculty.department,
                'email': faculty.email,
                'status': faculty.status 
            }
            self.mqtt_service.publish(MQTTTopics.SYSTEM_NOTIFICATIONS, notification)
            logger.info(f"Published faculty_added notification for {faculty.name}")
        except Exception as e_mqtt:
            logger.error(f"Error publishing faculty added notification for {faculty.name}: {str(e_mqtt)}")
        
        return faculty


    @db_operation_with_retry()
    def update_faculty(self, db, faculty_id, name=None, department=None, email=None, ble_id=None, image_path=None, always_available=None): # 'always_available' is present but ignored
        """
        Update an existing faculty member. `db` is provided by the decorator.
        The `always_available` parameter is deprecated and its value is ignored.
        """
        faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
        if not faculty:
            raise ValueError(f"Faculty ID {faculty_id} not found for update.")

        updated_fields = []

        if name is not None and faculty.name != name:
            faculty.name = name
            updated_fields.append("name")
        if department is not None and faculty.department != department:
            faculty.department = department
            updated_fields.append("department")
        if email is not None and faculty.email != email:
            # Check if new email is already used by another faculty
            if db.query(Faculty).filter(Faculty.email == email, Faculty.id != faculty_id).first(): 
                raise ValueError(f"Email '{email}' already used by another faculty.")
            faculty.email = email
            updated_fields.append("email")
        
        # Handle BLE ID update carefully: allow setting to None/empty or a new value
        # If ble_id is an empty string or None, set it to None in DB.
        # If ble_id has a value, check for uniqueness.
        current_ble_id = faculty.ble_id if faculty.ble_id else ""
        new_ble_id = ble_id if ble_id else ""

        if new_ble_id != current_ble_id:
            if new_ble_id.strip() != "": # New BLE ID is not empty
                if db.query(Faculty).filter(Faculty.ble_id == new_ble_id, Faculty.id != faculty_id).first(): 
                    raise ValueError(f"BLE ID '{new_ble_id}' already used by another faculty.")
                faculty.ble_id = new_ble_id
            else: # New BLE ID is empty or None, so set to None
                faculty.ble_id = None
            updated_fields.append("ble_id")

        if image_path is not None and faculty.image_path != image_path:
            faculty.image_path = image_path
            updated_fields.append("image_path")
        
        # always_available is deprecated, ensure it's False if for some reason it was True
        if faculty.always_available:
            faculty.always_available = False
            updated_fields.append("always_available (deprecated, set to False)")

        if updated_fields:
            logger.info(f"DB: Updated faculty ID {faculty_id}. Changed fields: {', '.join(updated_fields)}")
            # db.commit() and db.refresh(faculty) handled by decorator
            
            # Publish notification
            try:
                # Ensure faculty ID is available after commit (decorator handles refresh)
                db.flush() 
                notification = {
                    'type': 'faculty_updated',
                    'faculty_id': faculty.id,
                    'name': faculty.name, # Send current name
                    'updated_fields': updated_fields
                }
                self.mqtt_service.publish(MQTTTopics.SYSTEM_NOTIFICATIONS, notification)
                logger.info(f"Published faculty_updated notification for {faculty.name}")
            except Exception as e_mqtt:
                logger.error(f"Error publishing faculty updated notification for {faculty.name}: {str(e_mqtt)}")
        else:
            logger.info(f"DB: No changes for faculty ID {faculty_id}.")
            
        return faculty

    @db_operation_with_retry()
    def delete_faculty(self, db, faculty_id):
        """
        Delete a faculty member. `db` is provided by the decorator.
        """
        faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
        if not faculty:
            # Allow graceful failure if faculty not found, or raise ValueError if strict
            logger.warning(f"DB: Faculty ID {faculty_id} not found for deletion. No action taken.")
            return False # Indicate faculty was not found/deleted

        faculty_name = faculty.name # Store for logging before deletion
        db.delete(faculty)
        # db.commit() handled by decorator
        logger.info(f"DB: Deleted faculty ID {faculty_id}, Name: {faculty_name}")
        
        # Publish notification
        try:
            notification = {
                'type': 'faculty_deleted',
                'faculty_id': faculty_id, # ID is known
                'faculty_name': faculty_name 
            }
            self.mqtt_service.publish(MQTTTopics.SYSTEM_NOTIFICATIONS, notification)
            logger.info(f"Published faculty_deleted notification for {faculty_name} (ID: {faculty_id})")
        except Exception as e_mqtt:
            logger.error(f"Error publishing faculty deleted notification for {faculty_name}: {str(e_mqtt)}")
            
        return True # Indicate successful deletion


    def ensure_available_faculty(self): # Marked for testing purposes as per memory
        """
        TESTING/DEMO: Ensures at least one faculty member is marked as available.
        This should ideally be replaced by actual BLE-based status updates.
        """
        db = get_db()
        try:
            logger.debug("Testing: Attempting to ensure an available faculty member.")
            # Check if any faculty is already available
            available_faculty = db.query(Faculty).filter(Faculty.status == True).first()
            if available_faculty:
                logger.info(f"Testing: Found available faculty: {available_faculty.name} (ID: {available_faculty.id}). No changes made.")
                return available_faculty

            # If no one is available, try to make one available (e.g., Dr. John Smith or the first one)
            # This is placeholder logic for testing without real BLE.
            target_faculty = db.query(Faculty).filter(Faculty.name == "Dr. John Smith").first()
            if not target_faculty:
                target_faculty = db.query(Faculty).order_by(Faculty.id).first() # Get the first faculty

            if target_faculty:
                logger.warning(f"Testing: No faculty currently available. Making '{target_faculty.name}' (ID: {target_faculty.id}) available for testing.")
                target_faculty.status = True
                target_faculty.last_seen = datetime.datetime.now()
                db.commit()
                self._notify_callbacks(target_faculty) # Notify about this test-induced change
                return target_faculty
            else:
                logger.warning("Testing: No faculty members found in the database to make available.")
                return None
        except Exception as e:
            logger.error(f"Testing: Error in ensure_available_faculty: {e}", exc_info=True)
            if db: db.rollback() # Rollback on error
            return None
        finally:
            close_db()