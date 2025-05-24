import logging
import inspect
import threading
import time
from ..models.base import close_db
from ..services import get_rfid_service
from ..config import get_config

# Set up logging
logger = logging.getLogger(__name__)

class RFIDController:
    """
    Controller for handling RFID card scanning and student verification.
    """
    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the RFID controller."""
        if cls._instance is None:
            cls._instance = RFIDController()
        return cls._instance

    def __init__(self):
        """
        Initialize the RFID controller.
        """
        if RFIDController._instance is not None:
            # Ensure singleton pattern is respected
            raise RuntimeError("RFIDController is a singleton, use RFIDController.instance()")
        
        self.rfid_service = get_rfid_service()
        self.callbacks = []
        RFIDController._instance = self # Set the instance after checks

    def start(self):
        """
        Start the RFID service and register callback.
        """
        logger.info("Starting RFID controller")
        self.rfid_service.register_callback(self.on_rfid_read)
        self.rfid_service.start()

    def stop(self):
        """
        Stop the RFID service and unregister callbacks.
        """
        logger.info("Stopping RFID controller")
        # Unregister our callback from the RFID service
        try:
            self.rfid_service.unregister_callback(self.on_rfid_read)
        except Exception as e:
            logger.error(f"Error unregistering RFID callback: {str(e)}")

        # Stop the RFID service
        self.rfid_service.stop()

    def register_callback(self, callback):
        """
        Register a callback to be called when a student is verified.

        Args:
            callback (callable): Function that takes a Student object as argument
        """
        self.callbacks.append(callback)
        logger.info(f"Registered RFID controller callback: {callback.__name__}")

    def _notify_callbacks(self, student, rfid_uid, error_message=None):
        """
        Notify all callbacks with the student and RFID information.

        Args:
            student: The authenticated student object or None if not authenticated
            rfid_uid (str): The RFID UID that was read or None on error
            error_message (str, optional): Error message if authentication failed
        """
        for callback in self.callbacks:
            try:
                callback(student, rfid_uid, error_message)
            except Exception as e:
                logger.error(f"Error in RFID callback {getattr(callback, '__name__', 'unknown')}: {str(e)}")

    def on_rfid_read(self, student, rfid_uid):
        """
        Callback for RFID read events from RFIDService.
        The RFIDService has already attempted to validate the student using its cache.

        Args:
            student: Student object if validated by RFIDService, None otherwise.
            rfid_uid (str): The RFID UID that was read.
        """
        logger.info(f"RFID Controller received scan: UID='{rfid_uid}', Student from service: '{student.name if student else None}'")

        if student:
            self.handle_authenticated_student(student)
        else:
            # RFIDService did not find a student for this UID in its cache
            err_msg = f"Unknown or unregistered RFID card ('{rfid_uid}')"
            logger.warning(f"No student associated with RFID UID: '{rfid_uid}'. Error: {err_msg}")
            self.handle_authentication_failure(rfid_uid, err_msg)

    def simulate_scan(self, rfid_uid=None):
        """
        Simulate an RFID scan for development purposes.

        Args:
            rfid_uid (str, optional): RFID UID to simulate. If None, a random UID is generated.

        Returns:
            str: The simulated RFID UID
        """
        # The RFIDService's simulate_card_read method will fetch/generate UID,
        # find the student, and then call the registered on_rfid_read callback (this class's method)
        return self.rfid_service.simulate_card_read(rfid_uid)

    def process_manual_uid(self, rfid_uid):
        """
        Process an RFID UID entered manually.
        Looks up the student and triggers the on_rfid_read callback flow.
        Args:
            rfid_uid (str): The RFID UID entered manually.
        """
        if not rfid_uid or not rfid_uid.strip():
            logger.warning("Manual RFID entry: UID is empty.")
            self.on_rfid_read(None, rfid_uid) # Trigger failure notification
            return

        logger.info(f"Processing manually entered RFID UID: {rfid_uid}")
        student = self.rfid_service.get_student_by_rfid(rfid_uid) # Use service to get student
        self.on_rfid_read(student, rfid_uid) # Call own handler to unify event flow

    def handle_authenticated_student(self, student):
        """
        Handle successful student authentication.

        Args:
            student: The authenticated student object
        """
        logger.info(f"Student authenticated: {student.name} (ID: {student.id})")

        # Notify callbacks with authenticated student
        self._notify_callbacks(student, student.rfid_uid)

    def handle_authentication_failure(self, rfid_uid, error_message):
        """
        Handle failed student authentication.

        Args:
            rfid_uid (str): The RFID UID that was scanned.
            error_message (str): The error message explaining the failure
        """
        logger.warning(f"Authentication failed for UID '{rfid_uid}': {error_message}")

        # Notify callbacks with failure
        self._notify_callbacks(None, rfid_uid, error_message)