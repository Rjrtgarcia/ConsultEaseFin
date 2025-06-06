from central_system.config import get_config  # , initialize_config, log_config_load_status
from central_system.utils.theme import ConsultEaseTheme
from central_system.utils import (
    apply_stylesheet,
    WindowTransitionManager,
    get_keyboard_manager,
    install_keyboard_manager,
    KeyboardManager,
    initialize_icons
)
from central_system.views import (
    LoginWindow,
    DashboardWindow,
    AdminLoginWindow,
    AdminDashboardWindow
)
from central_system.controllers import (
    RFIDController,
    FacultyController,
    ConsultationController,
    AdminController
)
from central_system.models import init_db
import sys
import os
import logging
import subprocess
from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QSplashScreen, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject
from PyQt5.QtGui import QPixmap, QFont
import signal
from logging.handlers import RotatingFileHandler

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import configuration system

# Initialize configuration early
# initialize_config() # This was causing the error
config = get_config()
# log_config_load_status()

# Configure logging
log_level = getattr(logging, config.get('logging.level', 'INFO').upper())
log_file = config.get('logging.file', 'consultease.log')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_max_size = config.get('logging.max_size', 10485760)  # 10MB default
log_backup_count = config.get('logging.backup_count', 5)  # 5 backups default

# Create a logger for the main module
logger = logging.getLogger(__name__)

# Ensure logs directory exists
log_dir = os.path.dirname(log_file)
if log_dir:  # Only call makedirs if log_dir is not an empty string
    try:
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"Ensured log directory exists: {log_dir}")
    except PermissionError as e:
        print(f"ERROR: Cannot create log directory {log_dir}: Permission denied")
        print(f"The application may continue but logs cannot be written to {log_file}")
        print(f"Please check folder permissions or run the application with appropriate privileges")
        # Fall back to current directory
        log_file = "consultease.log"
        print(f"Attempting to use current directory for log file: {log_file}")

try:
    # Create a rotating file handler for logging
    handler = RotatingFileHandler(
        log_file,
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    handler.setFormatter(logging.Formatter(log_format))

    # Add the handler to the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers if any
    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)

    # Add the new rotating handler
    root_logger.addHandler(handler)

    # Optional: Add a console handler as well
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    logger.info(f"Logging configured with level {log_level}, rotating file handler to {log_file} " +
                f"(max size: {log_max_size/1024/1024:.1f}MB, backups: {log_backup_count})")
except Exception as e:
    print(f"ERROR: Failed to configure logging: {e}")
    # Set up basic console logging as fallback
    logging.basicConfig(level=log_level, format=log_format)
    logger.warning(f"Using basic console logging due to error: {e}")

# Import models and controllers

# Import views

# Import utilities
# Import theme system

# Event filter for auto-showing keyboard


class FocusEventFilter(QObject):
    def __init__(self, keyboard_manager, parent=None):
        super().__init__(parent)
        self.keyboard_manager = keyboard_manager
        self.logger = logging.getLogger(__name__ + ".FocusEventFilter")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            if isinstance(obj, (QLineEdit, QTextEdit)):
                # Check if the widget wants keyboard on focus (optional, for more control)
                # For now, always show for QLineEdit and QTextEdit
                self.logger.debug(
                    f"FocusIn event on {obj.__class__.__name__} ({obj.objectName()}). Showing keyboard.")
                self.keyboard_manager.show_keyboard()
        # elif event.type() == QEvent.FocusOut:
        #     if isinstance(obj, (QLineEdit, QTextEdit)):
        #         # Potentially hide keyboard if no other input field has focus.
        #         # This can be complex; for now, rely on manual hide or keyboard's own behavior.
        #         self.logger.debug(f"FocusOut event on {obj.__class__.__name__}. Considering hiding keyboard.")
        #         pass # Logic to hide keyboard if no other input has focus would go here
        return super().eventFilter(obj, event)


class ConsultEaseApp:
    """
    Main application class for ConsultEase.
    """

    def __init__(self, fullscreen=False):
        """
        Initialize the ConsultEase application.
        """
        logger.info("Initializing ConsultEase application")
        self.config = get_config()  # Store config instance

        # Create QApplication instance
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("ConsultEase")

        # Set up icons and modern UI (after QApplication is created)
        initialize_icons()
        logger.info("Initialized icons")

        # Apply centralized theme stylesheet
        try:
            # Apply base stylesheet from theme system
            self.app.setStyleSheet(ConsultEaseTheme.get_base_stylesheet())
            logger.info("Applied centralized theme stylesheet")
        except Exception as e:
            logger.error(f"Failed to apply theme stylesheet: {e}")
            # Fall back to old stylesheet as backup
            try:
                theme = self._get_theme_preference()
                apply_stylesheet(self.app, theme)
                logger.info(f"Applied fallback {theme} theme stylesheet")
            except Exception as e2:
                logger.error(f"Failed to apply fallback stylesheet: {e2}")

        # Initialize unified keyboard manager for touch input
        try:
            self.keyboard_handler = get_keyboard_manager()
            # Install keyboard manager to handle focus events
            install_keyboard_manager(self.app)
            logger.info(
                f"Initialized keyboard manager with {self.keyboard_handler.active_keyboard} keyboard")
        except Exception as e:
            logger.error(f"Failed to initialize keyboard manager: {e}")
            self.keyboard_handler = None

        # Initialize database
        init_db()

        # Initialize controllers
        self.rfid_controller = RFIDController.instance()
        self.faculty_controller = FacultyController.instance()
        self.consultation_controller = ConsultationController.instance()
        self.admin_controller = AdminController.instance()

        # Ensure default admin exists
        self.admin_controller.ensure_default_admin()

        # Initialize windows
        self.login_window = None  # Main RFID/Login window
        self.dashboard_window = None  # Main student/faculty dashboard
        self.admin_login_window = None  # Instance for AdminLoginWindow
        self.admin_dashboard_window = None  # Instance for AdminDashboardWindow

        # Start controllers
        logger.info("Starting RFID controller")
        self.rfid_controller.start()
        self.rfid_controller.register_callback(self.handle_rfid_scan)

        logger.info("Starting faculty controller")
        self.faculty_controller.start()

        logger.info("Starting consultation controller")
        self.consultation_controller.start()

        # Make sure at least one faculty is available for testing, if configured
        if self.config.get('system.ensure_test_faculty_available', False):
            logger.info("Configuration requests ensuring test faculty is available.")
            self._ensure_dr_john_smith_available()
        else:
            logger.info("Skipping ensure_test_faculty_available as per configuration.")

        # Current student
        self.current_student = None

        # Initialize transition manager
        transition_duration = self.config.get('ui.transition_duration', 300)
        self.transition_manager = WindowTransitionManager(duration=transition_duration)
        logger.info("Initialized window transition manager")

        # Verify RFID controller is properly initialized
        try:
            from .services import get_rfid_service
            rfid_service = get_rfid_service()
            logger.info(
                f"RFID service initialized: {rfid_service}, simulation mode: {rfid_service.simulation_mode}")

            # Log registered callbacks
            logger.info(f"RFID service callbacks: {len(rfid_service.callbacks)}")
            for i, callback in enumerate(rfid_service.callbacks):
                callback_name = getattr(callback, '__name__', str(callback))
                logger.info(f"  Callback {i}: {callback_name}")
        except Exception as e:
            logger.error(f"Error verifying RFID service: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # Connect cleanup method
        self.app.aboutToQuit.connect(self.cleanup)

        # Show login window
        self.show_login_window()

        # Store fullscreen preference for use in window creation
        self.fullscreen = self.config.get('ui.fullscreen', False)

        # Initialize KeyboardManager
        self.keyboard_manager = get_keyboard_manager()
        self.app.keyboard_manager = self.keyboard_manager  # Make it accessible globally if needed

        # Install focus event filter for auto keyboard display
        self.focus_filter = FocusEventFilter(self.keyboard_manager)
        self.app.installEventFilter(self.focus_filter)
        logger.info("Installed focus event filter for automatic keyboard.")

    def _get_theme_preference(self):
        """
        Get the user's theme preference.

        Returns:
            str: Theme name ('light' or 'dark')
        """
        # Default to light theme as per the technical context document
        theme = self.config.get('ui.theme', 'light')

        # Log the theme being used
        logger.info(f"Using {theme} theme based on preference from configuration")

        return theme

    def _ensure_dr_john_smith_available(self):
        """
        Make sure Dr. John Smith is available for testing.
        """
        try:
            # Use the faculty controller to ensure at least one faculty is available
            available_faculty = self.faculty_controller.ensure_available_faculty()

            if available_faculty:
                logger.info(
                    f"Ensured faculty availability: {available_faculty.name} (ID: {available_faculty.id}) is now available")
            else:
                logger.warning("Could not ensure faculty availability")
        except Exception as e:
            logger.error(f"Error ensuring faculty availability: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def run(self):
        """
        Run the application.
        """
        logger.info("Starting ConsultEase application")
        return self.app.exec_()

    def cleanup(self):
        """
        Clean up resources before exiting.
        """
        logger.info("Cleaning up resources before exit...")

        # Set cleanup flag to prevent new operations during shutdown
        self.is_shutting_down = True

        # Gracefully close all database connections
        try:
            from .models.base import close_db
            logger.info("Closing database connections...")
            close_db()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

        # Stop RFID service
        try:
            if self.rfid_service:
                logger.info("Stopping RFID service...")
                self.rfid_service.stop()
                logger.info("RFID service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping RFID service: {e}")

        # Disconnect MQTT service
        try:
            from .services import get_mqtt_service
            mqtt_service = get_mqtt_service()
            if mqtt_service:
                logger.info("Disconnecting MQTT service...")
                mqtt_service.disconnect()
                logger.info("MQTT service disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting MQTT service: {e}")

        # Clean up keyboard manager
        try:
            from .utils.keyboard_manager import get_keyboard_manager
            keyboard_manager = get_keyboard_manager()
            if keyboard_manager:
                logger.info("Cleaning up keyboard manager...")
                keyboard_manager.hide_keyboard()
                # Check if cleanup method exists
                if hasattr(keyboard_manager, 'cleanup'):
                    keyboard_manager.cleanup()
                logger.info("Keyboard manager cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up keyboard manager: {e}")

        # Explicitly call garbage collection to release resources
        try:
            import gc
            gc.collect()
            logger.info("Garbage collection completed")
        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")

        logger.info("Cleanup complete. Exiting application.")

    def show_login_window(self):
        """
        Show the login window.
        """
        if self.login_window is None:
            self.login_window = LoginWindow()
            self.login_window.student_authenticated.connect(self.handle_student_authenticated)
            self.login_window.change_window.connect(self.handle_window_change)

        # Determine which window is currently visible
        current_window = None
        if self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to LoginWindow")
            # Ensure login window is ready for fullscreen
            self.login_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.login_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing login window without transition")
            self.login_window.show()
            self.login_window.showFullScreen()  # Force fullscreen again to ensure it takes effect

    def show_dashboard_window(self, student=None):
        """
        Show the dashboard window.
        """
        self.current_student = student

        if self.dashboard_window is None:
            # Create a new dashboard window
            self.dashboard_window = DashboardWindow(student)
            self.dashboard_window.change_window.connect(self.handle_window_change)
            self.dashboard_window.consultation_requested.connect(self.handle_consultation_request)
        else:
            # Update student info and reinitialize the UI
            logger.info(
                f"Updating dashboard with new student: {student.name if student else 'None'}")

            # Store the new student reference
            self.dashboard_window.student = student

            # Reinitialize the UI to update the welcome message and other student-specific elements
            self.dashboard_window.init_ui()

            # Update the consultation panel with the new student
            if hasattr(self.dashboard_window, 'consultation_panel'):
                self.dashboard_window.consultation_panel.set_student(student)
                self.dashboard_window.consultation_panel.refresh_history()

        # Populate faculty grid
        faculties = self.faculty_controller.get_all_faculty()
        self.dashboard_window.populate_faculty_grid(faculties)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(
                f"Transitioning from {current_window.__class__.__name__} to DashboardWindow")
            # Ensure dashboard window is ready for fullscreen
            self.dashboard_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.dashboard_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing dashboard window without transition")
            self.dashboard_window.show()
            self.dashboard_window.showFullScreen()  # Force fullscreen to ensure it takes effect

        # Log that we've shown the dashboard
        logger.info(f"Showing dashboard for student: {student.name if student else 'Unknown'}")

    def show_admin_login_window(self):
        """Show the admin login window."""
        logger.info("Showing admin login window")
        if not self.admin_login_window:
            self.admin_login_window = AdminLoginWindow()
            # Connect the signal from AdminLoginWindow to a handler in ConsultEaseApp
            self.admin_login_window.admin_authenticated.connect(self.handle_admin_authenticated)
            # Connect the change_window signal if AdminLoginWindow needs to navigate (e.g. back)
            # self.admin_login_window.change_window.connect(self.handle_window_change)
            # The AdminLoginWindow has a 'Back' button that emits change_window('login', None)
            # This should ideally go back to the main login/RFID screen, or a selection screen.
            # For now, let's assume 'login' in change_window means the main RFID login.
            if hasattr(self.admin_login_window, 'change_window'):  # Check if signal exists
                self.admin_login_window.change_window.connect(self.handle_window_change)
            else:
                logger.warning("AdminLoginWindow does not have a 'change_window' signal.")

        current_active_window = self.app.activeWindow() or self.login_window  # Fallback if no active window

        # Ensure the window is properly sized and centered or fullscreen
        if self.config.get('ui.fullscreen', False):
            self.admin_login_window.showFullScreen()
        else:
            self.admin_login_window.show_normal_centered()
            # self.admin_login_window.show() # Fallback

        # Use transition manager if a previous window was active
        if current_active_window and current_active_window != self.admin_login_window and current_active_window.isVisible():
            self.transition_manager.fade_out_in(current_active_window, self.admin_login_window)
        else:
            self.admin_login_window.show()  # Directly show if no prior window or it's the same
            if self.config.get('ui.fullscreen', False):
                self.admin_login_window.showFullScreen()
            else:
                self.admin_login_window.show_normal_centered()

        # Optional: If keyboard manager is used and focus isn't set automatically by AdminLoginWindow.showEvent
        # QTimer.singleShot(100, lambda: self.admin_login_window.username_input.setFocus() if self.admin_login_window and hasattr(self.admin_login_window, 'username_input') else None)

    def show_admin_dashboard_window(self, admin=None):
        """
        Show the admin dashboard window.
        """
        if self.admin_dashboard_window is None:
            self.admin_dashboard_window = AdminDashboardWindow(admin)
            self.admin_dashboard_window.change_window.connect(self.handle_window_change)
            self.admin_dashboard_window.faculty_updated.connect(self.handle_faculty_updated)
            self.admin_dashboard_window.student_updated.connect(self.handle_student_updated)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(
                f"Transitioning from {current_window.__class__.__name__} to AdminDashboardWindow")
            # Ensure admin dashboard window is ready for fullscreen
            self.admin_dashboard_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.admin_dashboard_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing admin dashboard window without transition")
            self.admin_dashboard_window.show()
            self.admin_dashboard_window.showFullScreen()  # Force fullscreen

    def handle_rfid_scan(self, student, rfid_uid, error_message=None):
        """
        Handle RFID scan events from RFIDController.
        Args:
            student: Authenticated student object, or None on failure.
            rfid_uid: The scanned RFID UID.
            error_message: Error message if authentication failed.
        """
        if student:
            logger.info(f"RFID scan successful: Student {student.name} (UID: {rfid_uid})")
            self.current_student = student
            self.show_dashboard_window(student)
            # Sound/UI feedback for success should be handled within
            # show_dashboard_window or by DashboardWindow itself
        else:
            logger.warning(f"RFID scan failed: UID '{rfid_uid}'. Error: {error_message}")
            # Display error message on the current relevant window (e.g., LoginWindow)
            if self.login_window and self.login_window.isVisible():
                display_error = error_message if error_message else f"Invalid RFID card ('{rfid_uid}')."
                self.login_window.show_error(display_error)
            elif self.dashboard_window and self.dashboard_window.isVisible():
                # If already on dashboard (e.g. admin scanned an unknown card), show a
                # temporary notification
                display_error = error_message if error_message else f"Unknown RFID card ('{rfid_uid}')."
                self.dashboard_window.show_notification(display_error, 'error')
            else:
                # Fallback if no specific window is active to show the error
                logger.error(
                    f"RFID Authentication failed for UID '{rfid_uid}': {error_message}. No active window to display error.")
            # Sound/UI feedback for error should be handled by the window showing the error

    def handle_student_authenticated(self, student):
        """
        Handle student authentication event.

        Args:
            student (Student): Authenticated student
        """
        logger.info(f"Student authenticated: {student.name if student else 'Unknown'}")

        # Store the current student
        self.current_student = student

        # Show the dashboard window
        self.show_dashboard_window(student)

    def handle_admin_authenticated(self, admin_user_object):
        """
        Handle successful admin authentication.
        The admin_user_object is expected to be the authenticated admin model instance.
        """
        logger.info(
            f"Admin authenticated: {getattr(admin_user_object, 'username', 'Unknown Admin')}")
        self.current_admin = admin_user_object  # Store admin session
        # Potentially hide the admin login window if it's still visible or manage via transitions
        if self.admin_login_window and self.admin_login_window.isVisible():
            # self.admin_login_window.hide() # Hide will be handled by transition manager
            pass  # Transition manager will handle hiding

        self.show_admin_dashboard_window(admin=admin_user_object)

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request event.

        Args:
            faculty (object): Faculty object or dictionary
            message (str): Consultation message
            course_code (str): Course code
        """
        if not self.current_student:
            logger.error("Cannot request consultation: no student authenticated")
            return

        # Handle both Faculty object and dictionary
        if isinstance(faculty, dict):
            faculty_name = faculty['name']
            faculty_id = faculty['id']
        else:
            faculty_name = faculty.name
            faculty_id = faculty.id

        logger.info(f"Consultation requested with: {faculty_name}")

        # Create consultation request using the correct method
        consultation = self.consultation_controller.create_consultation(
            student_id=self.current_student.id,
            faculty_id=faculty_id,
            request_message=message,
            course_code=course_code
        )

        # Show success/error message
        if consultation:
            logger.info(f"Successfully created consultation request: {consultation.id}")
            # No need to show notification as DashboardWindow already shows a message box
        else:
            logger.error("Failed to create consultation request")
            # Show error message if the dashboard window has a show_notification method
            if hasattr(self.dashboard_window, 'show_notification'):
                self.dashboard_window.show_notification(
                    "Failed to send consultation request. Please try again.",
                    "error"
                )

    def handle_faculty_updated(self):
        """
        Handle faculty data updated event.
        """
        logger.info("Faculty data updated, refreshing dashboard if visible.")
        if self.dashboard_window and self.dashboard_window.isVisible():
            self.dashboard_window.refresh_faculty_status()

    def handle_student_updated(self):
        """
        Handle student data updates from admin dashboard.
        Refreshes RFID service cache and relevant UI components.
        """
        logger.info("Student data updated, attempting to refresh RFID service cache.")
        try:
            from .services import get_rfid_service  # Import here to avoid circular dependency at top level
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()
            logger.info("RFID service cache refreshed successfully via main app handler.")
        except Exception as e:
            logger.error(
                f"Error refreshing RFID service cache from main app: {str(e)}",
                exc_info=True)

        # Potentially refresh other UI elements if needed
        # For example, if a student list is displayed on the main dashboard (not currently the case)
        # if self.dashboard_window and self.dashboard_window.isVisible():
        #     self.dashboard_window.refresh_student_related_ui()

    def handle_window_change(self, window_name, data=None):
        """Handle requests to change the current window."""
        logger.info(f"Handling window change request to '{window_name}' with data: {data}")
        current_active_window = self.app.activeWindow()

        if window_name == "login":
            # This typically means the main RFID/student login
            self.current_student = None  # Clear student session
            self.current_admin = None  # Clear admin session
            self.show_login_window()
        elif window_name == "dashboard":
            if isinstance(data, dict) and "student" in data:
                self.show_dashboard_window(student=data["student"])
            elif self.current_student:  # Fallback to current student if any
                self.show_dashboard_window(student=self.current_student)
            else:
                logger.warning(
                    "Dashboard change requested without student data and no current student session. Showing main login.")
                self.show_login_window()
        elif window_name == "admin_login" or window_name == "admin_login_requested":  # Added condition
            self.current_admin = None  # Clear admin session before showing login
            self.show_admin_login_window()
        elif window_name == "admin_dashboard":
            if self.current_admin:  # Check if an admin session exists
                self.show_admin_dashboard_window(admin=self.current_admin)
            # Check if data is an admin object
            elif isinstance(data, AdminController.instance().get_admin_model_class()):
                self.current_admin = data
                self.show_admin_dashboard_window(admin=self.current_admin)
            else:
                logger.warning(
                    "Admin dashboard change requested without admin data or session. Showing admin login.")
                self.show_admin_login_window()
        else:
            logger.warning(f"Unknown window name '{window_name}' requested.")


if __name__ == "__main__":
    # Config object is already initialized globally when config is imported
    # Logging is configured globally using config values

    # Enable debug logging for RFID service (can also be driven by config)
    rfid_log_level_str = config.get('logging.rfid_level', 'INFO').upper()
    rfid_log_level = getattr(logging, rfid_log_level_str, logging.INFO)
    rfid_logger = logging.getLogger('central_system.services.rfid_service')
    rfid_logger.setLevel(rfid_log_level)  # Use configured level

    # Set environment variables if needed - REMOVED, should be set externally or in config.json
    # import os

    # Configure RFID - enable simulation mode since we're on Raspberry Pi
    # os.environ['RFID_SIMULATION_MODE'] = 'true'  # REMOVED
    # Set the theme to light as per the technical context document
    # os.environ['CONSULTEASE_THEME'] = 'light' # REMOVED
    # Use SQLite for development and testing
    # os.environ['DB_TYPE'] = 'sqlite' # REMOVED
    # os.environ['DB_PATH'] = 'consultease.db'  # REMOVED

    # Check if we're running in fullscreen mode
    # fullscreen = os.environ.get('CONSULTEASE_FULLSCREEN', 'false').lower()
    # == 'true' # Now handled by self.fullscreen in __init__
    fullscreen_from_config = config.get('ui.fullscreen', False)

    # Start the application
    app = ConsultEaseApp(fullscreen=fullscreen_from_config)  # Pass config value
    signal.signal(signal.SIGINT, lambda sig, frame: app.cleanup())  # Ensure cleanup on Ctrl+C
    sys.exit(app.run())
