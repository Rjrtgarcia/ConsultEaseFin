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
from central_system.config import get_config #, initialize_config, log_config_load_status

# Initialize configuration early
# initialize_config() # This was causing the error
config = get_config()
# log_config_load_status()

# Configure logging using settings from config.py
log_level_str = config.get('logging.level', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
log_file = config.get('logging.file', 'consultease.log')
log_max_size = config.get('logging.max_size', 10*1024*1024) # Default 10MB
log_backup_count = config.get('logging.backup_count', 5)

# Ensure logs directory exists
log_dir = os.path.dirname(log_file)
if log_dir: # Only call makedirs if log_dir is not an empty string
    os.makedirs(log_dir, exist_ok=True)

# Create handlers
stream_handler = logging.StreamHandler(sys.stdout)
# Use RotatingFileHandler
file_handler = RotatingFileHandler(
    log_file, maxBytes=log_max_size, backupCount=log_backup_count
)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        stream_handler,
        file_handler
    ]
)
logger = logging.getLogger(__name__)

# Import models and controllers
from central_system.models import init_db
from central_system.controllers import (
    RFIDController,
    FacultyController,
    ConsultationController,
    AdminController
)

# Import views
from central_system.views import (
    LoginWindow,
    DashboardWindow,
    AdminLoginWindow,
    AdminDashboardWindow
)

# Import utilities
from central_system.utils import (
    apply_stylesheet,
    WindowTransitionManager,
    get_keyboard_manager,
    install_keyboard_manager,
    KeyboardManager,
    initialize_icons
)
# Import theme system
from central_system.utils.theme import ConsultEaseTheme

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
                self.logger.debug(f"FocusIn event on {obj.__class__.__name__} ({obj.objectName()}). Showing keyboard.")
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
        self.config = get_config() # Store config instance

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
            logger.info(f"Initialized keyboard manager with {self.keyboard_handler.active_keyboard} keyboard")
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
        self.login_window = None
        self.dashboard_window = None
        self.admin_login_window = None
        self.admin_dashboard_window = None

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
            logger.info(f"RFID service initialized: {rfid_service}, simulation mode: {rfid_service.simulation_mode}")

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
        self.app.keyboard_manager = self.keyboard_manager # Make it accessible globally if needed

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
                logger.info(f"Ensured faculty availability: {available_faculty.name} (ID: {available_faculty.id}) is now available")
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
        logger.info("Cleaning up ConsultEase application")

        # Stop controllers
        self.rfid_controller.stop()
        self.faculty_controller.stop()
        self.consultation_controller.stop()

        if self.keyboard_manager: # Cleanup keyboard manager
            self.keyboard_manager.cleanup()
            logger.info("Keyboard manager cleaned up.")

        # Close all windows gracefully
        self.login_window = None
        self.dashboard_window = None
        self.admin_login_window = None
        self.admin_dashboard_window = None

        logger.info("Cleanup finished.")

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
            logger.info(f"Updating dashboard with new student: {student.name if student else 'None'}")

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
            logger.info(f"Transitioning from {current_window.__class__.__name__} to DashboardWindow")
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
        """
        Show the admin login window.
        """
        if self.admin_login_window is None:
            self.admin_login_window = AdminLoginWindow()
            self.admin_login_window.admin_authenticated.connect(self.handle_admin_authenticated)
            self.admin_login_window.change_window.connect(self.handle_window_change)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Define a callback for after the transition completes
        def after_transition():
            # Force the keyboard to show
            if self.keyboard_handler:
                logger.info("Showing keyboard using improved keyboard handler")
                self.keyboard_handler.show_keyboard()

                # Focus the username input to trigger the keyboard
                QTimer.singleShot(300, lambda: self.admin_login_window.username_input.setFocus())
                # Focus again after a longer delay to ensure keyboard appears
                QTimer.singleShot(800, lambda: self.admin_login_window.username_input.setFocus())

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to AdminLoginWindow")
            # Ensure admin login window is ready for fullscreen
            self.admin_login_window.showFullScreen()
            # Apply transition with callback
            self.transition_manager.fade_out_in(current_window, self.admin_login_window, after_transition)
        else:
            # No transition needed, just show the window
            logger.info("Showing admin login window without transition")
            self.admin_login_window.show()
            self.admin_login_window.showFullScreen()  # Force fullscreen
            # Call the callback directly
            after_transition()

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
            logger.info(f"Transitioning from {current_window.__class__.__name__} to AdminDashboardWindow")
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
            # Sound/UI feedback for success should be handled within show_dashboard_window or by DashboardWindow itself
        else:
            logger.warning(f"RFID scan failed: UID '{rfid_uid}'. Error: {error_message}")
            # Display error message on the current relevant window (e.g., LoginWindow)
            if self.login_window and self.login_window.isVisible():
                display_error = error_message if error_message else f"Invalid RFID card ('{rfid_uid}')."
                self.login_window.show_error(display_error)
            elif self.dashboard_window and self.dashboard_window.isVisible():
                # If already on dashboard (e.g. admin scanned an unknown card), show a temporary notification
                display_error = error_message if error_message else f"Unknown RFID card ('{rfid_uid}')."
                self.dashboard_window.show_notification(display_error, 'error')
            else:
                # Fallback if no specific window is active to show the error
                logger.error(f"RFID Authentication failed for UID '{rfid_uid}': {error_message}. No active window to display error.")
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

    def handle_admin_authenticated(self, credentials):
        """
        Handle admin authentication event.

        Args:
            credentials (tuple): Admin credentials (username, password)
        """
        # Unpack credentials from tuple
        username, password = credentials

        # Authenticate admin
        admin = self.admin_controller.authenticate(username, password)

        if admin:
            logger.info(f"Admin authenticated: {username}")
            # Pass the admin model object directly
            self.show_admin_dashboard_window(admin)
        else:
            logger.warning(f"Admin authentication failed: {username}")
            if self.admin_login_window:
                self.admin_login_window.show_login_error("Invalid username or password")

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
            from .services import get_rfid_service # Import here to avoid circular dependency at top level
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()
            logger.info("RFID service cache refreshed successfully via main app handler.")
        except Exception as e:
            logger.error(f"Error refreshing RFID service cache from main app: {str(e)}", exc_info=True)

        # Potentially refresh other UI elements if needed
        # For example, if a student list is displayed on the main dashboard (not currently the case)
        # if self.dashboard_window and self.dashboard_window.isVisible():
        #     self.dashboard_window.refresh_student_related_ui()

    def handle_window_change(self, window_name, data=None):
        """
        Handle window change event.

        Args:
            window_name (str): Name of window to show
            data (any): Optional data to pass to the window
        """
        if window_name == "login":
            self.show_login_window()
        elif window_name == "dashboard":
            self.show_dashboard_window(data)
        elif window_name == "admin_login":
            self.show_admin_login_window()
        elif window_name == "admin_dashboard":
            self.show_admin_dashboard_window(data)
        else:
            logger.warning(f"Unknown window: {window_name}")

if __name__ == "__main__":
    # Config object is already initialized globally when config is imported
    # Logging is configured globally using config values

    # Enable debug logging for RFID service (can also be driven by config)
    rfid_log_level_str = config.get('logging.rfid_level', 'INFO').upper()
    rfid_log_level = getattr(logging, rfid_log_level_str, logging.INFO)
    rfid_logger = logging.getLogger('central_system.services.rfid_service')
    rfid_logger.setLevel(rfid_log_level) # Use configured level

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
    # fullscreen = os.environ.get('CONSULTEASE_FULLSCREEN', 'false').lower() == 'true' # Now handled by self.fullscreen in __init__
    fullscreen_from_config = config.get('ui.fullscreen', False)

    # Start the application
    app = ConsultEaseApp(fullscreen=fullscreen_from_config) # Pass config value
    signal.signal(signal.SIGINT, lambda sig, frame: app.cleanup()) # Ensure cleanup on Ctrl+C
    sys.exit(app.run())