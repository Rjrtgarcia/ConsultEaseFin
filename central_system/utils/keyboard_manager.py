"""
Unified keyboard manager for ConsultEase.
Provides a single, robust solution for on-screen keyboard management with fallback mechanisms.
"""
import os
import sys
import time
import logging
import subprocess
import threading
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QEvent
from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit

# Import config
from central_system.config import get_config

logger = logging.getLogger(__name__)


class KeyboardManager(QObject):
    """
    Unified keyboard manager for on-screen keyboards.
    Provides a single interface for managing different on-screen keyboards with fallback mechanisms.
    """
    # Signal emitted when keyboard visibility changes
    keyboard_visibility_changed = pyqtSignal(bool)

    # Singleton instance
    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the keyboard manager."""
        if cls._instance is None:
            cls._instance = KeyboardManager()
        return cls._instance

    def __init__(self):
        """Initialize the keyboard manager."""
        super().__init__()

        # Prevent multiple initialization of the singleton
        if KeyboardManager._instance is not None:
            return

        # Get central config
        self.config = get_config()

        # Set up keyboard properties
        self.keyboard_visible = False
        self.keyboard_process = None
        self.dbus_available = self._check_dbus_available()

        # Determine preferred keyboard type from config
        self.preferred_keyboard = self.config.get('keyboard.type', 'squeekboard')
        self.fallback_keyboard = self.config.get('keyboard.fallback', 'onboard')

        # Detect available keyboards
        self._detect_available_keyboards()

        # Set up auto-hide timer
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.timeout.connect(self.hide_keyboard)
        self.auto_hide_timer.setSingleShot(True)

        # Log initialization
        logger.info(f"Keyboard manager initialized with {self.active_keyboard} keyboard")

    def _detect_available_keyboards(self):
        """Detect which keyboards are available on the system."""
        try:
            # Check for squeekboard
            self.squeekboard_available = self._is_squeekboard_available()
            logger.info(f"Squeekboard available: {self.squeekboard_available}")

            # Check for onboard
            self.onboard_available = self._check_keyboard_available('onboard')
            logger.info(f"Onboard available: {self.onboard_available}")

            # Determine which keyboard to use
            self.active_keyboard = self._determine_active_keyboard()
            logger.info(f"Active keyboard: {self.active_keyboard}")
        except Exception as e:
            logger.error(f"Error detecting available keyboards: {e}")
            # Set defaults for graceful degradation
            self.squeekboard_available = False
            self.onboard_available = False
            self.active_keyboard = None
            logger.warning(
                "Using fallback mode with no on-screen keyboard due to initialization error")

    def _check_keyboard_available(self, keyboard_type):
        """Check if a specific keyboard is available on the system."""
        try:
            if keyboard_type == 'squeekboard':
                # Check if squeekboard is installed
                result = subprocess.run(['which', 'squeekboard'],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                return result.returncode == 0
            elif keyboard_type == 'onboard':
                # Check if onboard is installed
                result = subprocess.run(['which', 'onboard'],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                return result.returncode == 0
            else:
                return False
        except Exception as e:
            logger.error(f"Error checking {keyboard_type} availability: {e}")
            return False

    def _determine_active_keyboard(self):
        """Determine which keyboard to use based on availability and preference."""
        # First try preferred keyboard
        if self.preferred_keyboard == 'squeekboard' and self.squeekboard_available:
            return 'squeekboard'
        elif self.preferred_keyboard == 'onboard' and self.onboard_available:
            return 'onboard'

        # Then try fallback keyboard if specified and different from preferred
        if self.fallback_keyboard and self.fallback_keyboard != self.preferred_keyboard:
            if self.fallback_keyboard == 'squeekboard' and self.squeekboard_available:
                logger.info(
                    f"Preferred keyboard '{self.preferred_keyboard}' not available or misconfigured, using fallback '{self.fallback_keyboard}'.")
                return 'squeekboard'
            elif self.fallback_keyboard == 'onboard' and self.onboard_available:
                logger.info(
                    f"Preferred keyboard '{self.preferred_keyboard}' not available or misconfigured, using fallback '{self.fallback_keyboard}'.")
                return 'onboard'

        # If fallback also not available or not specified, try any available
        if self.squeekboard_available:
            logger.info(
                f"Preferred keyboard '{self.preferred_keyboard}' and fallback '{self.fallback_keyboard}' not available/configured, using available 'squeekboard'.")
            return 'squeekboard'
        elif self.onboard_available:
            logger.info(
                f"Preferred keyboard '{self.preferred_keyboard}' and fallback '{self.fallback_keyboard}' not available/configured, using available 'onboard'.")
            return 'onboard'

        # No keyboard available
        logger.warning("No on-screen keyboard available")
        return None

    def _check_dbus_available(self):
        """Check if DBus is available for controlling squeekboard."""
        try:
            result = subprocess.run(['which', 'dbus-send'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def show_keyboard(self):
        """Show the on-screen keyboard."""
        if self.keyboard_visible:
            return

        logger.info(f"Showing keyboard: {self.active_keyboard}")

        if not self.active_keyboard:
            logger.warning("No keyboard available to show")
            return

        if self.active_keyboard == 'squeekboard':
            self._show_squeekboard()
        elif self.active_keyboard == 'onboard':
            self._show_onboard()
        else:
            logger.warning(f"Unknown keyboard type: {self.active_keyboard}")
            return

        self.keyboard_visible = True
        self.keyboard_visibility_changed.emit(True)

    def hide_keyboard(self):
        """Hide the on-screen keyboard."""
        if not self.keyboard_visible:
            return

        logger.info(f"Hiding keyboard: {self.active_keyboard}")

        if not self.active_keyboard:
            return

        if self.active_keyboard == 'squeekboard':
            self._hide_squeekboard()
        elif self.active_keyboard == 'onboard':
            self._hide_onboard()
        else:
            logger.warning(f"Unknown keyboard type: {self.active_keyboard}")
            return

        self.keyboard_visible = False
        self.keyboard_visibility_changed.emit(False)

    def toggle_keyboard(self):
        """Toggle the on-screen keyboard visibility."""
        if self.keyboard_visible:
            self.hide_keyboard()
        else:
            self.show_keyboard()

    def _show_squeekboard(self):
        """Show squeekboard keyboard."""
        logger.info("Attempting to show squeekboard keyboard")

        # First ensure squeekboard is running
        if not self._is_squeekboard_running():
            logger.info("Squeekboard not running, starting it...")
            try:
                # Kill any existing zombie processes first
                subprocess.run(['pkill', '-f', 'squeekboard'],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)

                # Set up environment variables
                env = dict(os.environ)
                env['SQUEEKBOARD_FORCE'] = '1'
                env['GDK_BACKEND'] = 'wayland,x11'
                env['QT_QPA_PLATFORM'] = 'wayland;xcb'

                # Start squeekboard with appropriate options
                subprocess.Popen(['squeekboard'],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 env=env,
                                 start_new_session=True)

                # Give it a moment to start
                time.sleep(0.5)
                logger.info("Started squeekboard process")
            except Exception as e:
                logger.error(f"Error starting squeekboard: {e}")
                # Try to use the keyboard-show.sh script as fallback
                self._try_keyboard_script()
                return

        # Now show the keyboard via DBus
        if self.dbus_available:
            try:
                # Try multiple times with different DBus commands to ensure it works
                success = False

                # Method 1: Standard DBus call
                try:
                    cmd = [
                        "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                        "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                    ]
                    result = subprocess.run(
                        cmd,
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
                    if result.returncode == 0:
                        success = True
                        logger.info("Showed squeekboard via standard DBus call")
                except Exception as e:
                    logger.warning(f"Standard DBus call failed: {e}")

                # Method 2: Try with session bus explicitly
                if not success:
                    try:
                        cmd = [
                            "dbus-send", "--session", "--type=method_call", "--dest=sm.puri.OSK0",
                            "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                        ]
                        result = subprocess.run(
                            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if result.returncode == 0:
                            success = True
                            logger.info("Showed squeekboard via session DBus call")
                    except Exception as e:
                        logger.warning(f"Session DBus call failed: {e}")

                # Method 3: Try with print-reply to see any errors
                if not success:
                    try:
                        cmd = [
                            "dbus-send", "--print-reply", "--type=method_call", "--dest=sm.puri.OSK0",
                            "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        logger.info(
                            f"DBus print-reply result: {result.stdout}, errors: {result.stderr}")
                        success = True
                    except Exception as e:
                        logger.warning(f"Print-reply DBus call failed: {e}")

                if not success:
                    # Try the keyboard script as a last resort
                    self._try_keyboard_script()
            except Exception as e:
                logger.error(f"All DBus methods failed: {e}")
                # Try the keyboard script as a last resort
                self._try_keyboard_script()
        else:
            logger.warning("DBus not available, trying alternative methods")
            # Try the keyboard script as a fallback
            self._try_keyboard_script()

    def _try_keyboard_script(self):
        """Try to use the keyboard-show.sh script as a fallback method."""
        try:
            # Check if the keyboard script exists
            home_dir = os.path.expanduser("~")
            script_path = os.path.join(home_dir, "keyboard-show.sh")

            if os.path.exists(script_path):
                logger.info(f"Using keyboard script at {script_path}")
                subprocess.Popen([script_path],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return True
            else:
                logger.warning(f"Keyboard script not found at {script_path}")
                return False
        except Exception as e:
            logger.error(f"Error using keyboard script: {e}")
            return False

    def _hide_squeekboard(self):
        """Hide squeekboard keyboard."""
        if self.dbus_available:
            try:
                cmd = [
                    "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                    "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:false"
                ]
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
                logger.info("Hid squeekboard via DBus")
            except Exception as e:
                logger.error(f"Error hiding squeekboard via DBus: {e}")
        else:
            logger.warning("DBus not available, cannot hide squeekboard reliably")

    def _is_squeekboard_running(self):
        """Check if squeekboard is running."""
        try:
            result = subprocess.run(['pgrep', '-f', 'squeekboard'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def _show_onboard(self):
        """Show onboard keyboard."""
        try:
            # Check if onboard is already running
            if not self._is_onboard_running():
                # Start onboard with appropriate options
                subprocess.Popen(
                    ['onboard', '--size=small', '--layout=Phone', '--enable-background-transparency'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                logger.info("Started onboard")
        except Exception as e:
            logger.error(f"Error showing onboard: {e}")

    def _hide_onboard(self):
        """Hide onboard keyboard."""
        try:
            # Just kill the process
            subprocess.run(['pkill', '-f', 'onboard'],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            logger.info("Killed onboard process")
        except Exception as e:
            logger.error(f"Error hiding onboard: {e}")

    def _is_onboard_running(self):
        """Check if onboard is running."""
        try:
            result = subprocess.run(['pgrep', '-f', 'onboard'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def force_show_keyboard(self):
        """Force show the keyboard, ensuring it attempts to become visible."""
        logger.info(f"Force showing keyboard: {self.active_keyboard}")
        # Reset visibility flag to ensure show_keyboard logic runs
        self.keyboard_visible = False
        self.show_keyboard()
        # The show_keyboard method itself contains fallbacks (e.g., script for
        # squeekboard if DBus fails)

    def _is_squeekboard_available(self):
        """Check if squeekboard is available on the system."""
        if not self._is_linux():
            return False

        try:
            # Define full path to which command
            WHICH_PATH = "/usr/bin/which"

            # Check if which command exists
            if not os.path.exists(WHICH_PATH):
                logger.warning(f"which command not found at {WHICH_PATH}")
                return False

            # Check if squeekboard is installed
            result = subprocess.run([WHICH_PATH, 'squeekboard'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking for squeekboard: {e}")
            return False

# Convenience function to get the keyboard manager instance


def get_keyboard_manager():
    """Get the keyboard manager instance."""
    return KeyboardManager.instance()


def install_keyboard_manager(app):
    """
    Install the keyboard manager for the application.
    This sets up event filters to show/hide the keyboard when text input widgets receive focus.

    Args:
        app: QApplication instance
    """
    from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QApplication
    from PyQt5.QtCore import QEvent, QObject

    keyboard = get_keyboard_manager()

    # Create a global event filter to catch all focus events
    class GlobalFocusFilter(QObject):
        def eventFilter(self, obj, event):
            # Check for focus events on input widgets
            if event.type() == QEvent.FocusIn:
                # Check if this is an input widget
                if isinstance(obj, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox)):
                    logger.debug(f"Focus gained on {obj.__class__.__name__}")
                    # Show keyboard with a slight delay to ensure window is ready
                    QTimer.singleShot(100, keyboard.show_keyboard)

            # Always return False to allow the event to be processed by other filters
            return False

    # Create and install the global filter
    global_filter = GlobalFocusFilter()
    app.installEventFilter(global_filter)

    # Store a reference to prevent garbage collection
    app.global_focus_filter = global_filter

    # Original focus in/out event handlers
    original_focus_in = QLineEdit.focusInEvent
    original_focus_out = QLineEdit.focusOutEvent

    # Override focus in event for QLineEdit
    def line_edit_focus_in(self, event):
        # Call original handler
        original_focus_in(self, event)
        # Show keyboard
        logger.debug(f"QLineEdit focus event in {self.objectName()}")
        keyboard.show_keyboard()

    # Override focus out event for QLineEdit
    def line_edit_focus_out(self, event):
        # Call original handler
        original_focus_out(self, event)
        # Don't hide keyboard on focus out - let it be handled manually
        # This prevents the keyboard from disappearing when switching between fields
        # keyboard.hide_keyboard()

    # Apply overrides
    QLineEdit.focusInEvent = line_edit_focus_in
    QLineEdit.focusOutEvent = line_edit_focus_out

    # Do the same for QTextEdit
    original_text_focus_in = QTextEdit.focusInEvent
    original_text_focus_out = QTextEdit.focusOutEvent

    def text_edit_focus_in(self, event):
        original_text_focus_in(self, event)
        logger.debug(f"QTextEdit focus event in {self.objectName()}")
        keyboard.show_keyboard()

    def text_edit_focus_out(self, event):
        original_text_focus_out(self, event)
        # Don't hide keyboard on focus out
        # keyboard.hide_keyboard()

    QTextEdit.focusInEvent = text_edit_focus_in
    QTextEdit.focusOutEvent = text_edit_focus_out

    # And for QPlainTextEdit
    original_plain_focus_in = QPlainTextEdit.focusInEvent
    original_plain_focus_out = QPlainTextEdit.focusOutEvent

    def plain_text_focus_in(self, event):
        original_plain_focus_in(self, event)
        logger.debug(f"QPlainTextEdit focus event in {self.objectName()}")
        keyboard.show_keyboard()

    def plain_text_focus_out(self, event):
        original_plain_focus_out(self, event)
        # Don't hide keyboard on focus out
        # keyboard.hide_keyboard()

    QPlainTextEdit.focusInEvent = plain_text_focus_in
    QPlainTextEdit.focusOutEvent = plain_text_focus_out

    # And for QComboBox
    original_combo_focus_in = QComboBox.focusInEvent
    original_combo_focus_out = QComboBox.focusOutEvent

    def combo_focus_in(self, event):
        original_combo_focus_in(self, event)
        logger.debug(f"QComboBox focus event in {self.objectName()}")
        keyboard.show_keyboard()

    def combo_focus_out(self, event):
        original_combo_focus_out(self, event)
        # Don't hide keyboard on focus out
        # keyboard.hide_keyboard()

    QComboBox.focusInEvent = combo_focus_in
    QComboBox.focusOutEvent = combo_focus_out

    # Add a method to manually hide the keyboard when clicking outside input fields
    def app_focus_changed(old, now):
        if now is None or not isinstance(now, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox)):
            # Clicked outside an input field, hide keyboard after a short delay
            # to allow for switching between fields
            QTimer.singleShot(500, keyboard.hide_keyboard)

    # Connect to application's focus change signal
    app.focusChanged.connect(app_focus_changed)

    logger.info("Enhanced keyboard manager installed for application")
    return keyboard
