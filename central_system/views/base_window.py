from PyQt5.QtWidgets import (QMainWindow, QDesktopWidget, QShortcut, QPushButton,
                             QStatusBar, QApplication, QLineEdit, QTextEdit,
                             QPlainTextEdit, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QEvent
from PyQt5.QtGui import QKeySequence, QIcon
import logging
import sys
import os

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import utilities
from central_system.utils.icons import IconProvider, Icons  # Import IconProvider and Icons

logger = logging.getLogger(__name__)

class BaseWindow(QMainWindow):
    """
    Base window class for ConsultEase.
    All windows should inherit from this class.
    """
    # Signal for changing windows
    change_window = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Basic window setup
        self.setWindowTitle("ConsultEase")
        self.setGeometry(100, 100, 1024, 768) # Default size

        # Set application icon (use helper from icons module)
        app_icon = IconProvider.get_icon(Icons.APP_ICON if hasattr(Icons, 'APP_ICON') else "app", QSize(64, 64))
        if app_icon and not app_icon.isNull():
            self.setWindowIcon(app_icon)
        else:
            logger.warning("Could not load application icon.")

        # Initialize UI (must be called after basic setup)
        self.init_ui()

        # Add F11 shortcut to toggle fullscreen
        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        # Store fullscreen state preference (will be set by ConsultEaseApp)
        self.fullscreen = False

    def init_ui(self):
        """
        Initialize the UI components.
        This method should be overridden by subclasses.
        """
        # Set window properties
        self.setMinimumSize(800, 480)  # Minimum size for Raspberry Pi 7" touchscreen
        self.apply_touch_friendly_style()

        # Add keyboard toggle button to the status bar
        self.statusBar().setStyleSheet("QStatusBar { border-top: 1px solid #cccccc; }")

        # Create keyboard toggle button with icon if available
        self.keyboard_toggle_button = QPushButton("⌨ Keyboard")
        self.keyboard_toggle_button.setFixedSize(140, 40)
        self.keyboard_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #f4d35e;  /* Gold accent color for visibility */
                color: #0d3b66;  /* Dark blue text for contrast */
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 12pt;
                border: 2px solid #0d3b66;  /* Border for better visibility */
            }
            QPushButton:hover {
                background-color: #f7e07e;  /* Lighter gold on hover */
            }
            QPushButton:pressed {
                background-color: #e6c54a;  /* Darker gold when pressed */
            }
        """)

        # Try to set an icon if available
        try:
            keyboard_icon = IconProvider.get_icon("keyboard")
            if keyboard_icon and not keyboard_icon.isNull():
                self.keyboard_toggle_button.setIcon(keyboard_icon)
        except:
            # If icon not available, just use text
            pass

        self.keyboard_toggle_button.clicked.connect(self._toggle_keyboard)
        self.statusBar().addPermanentWidget(self.keyboard_toggle_button)

        # Center window on screen
        self.center()

    def apply_touch_friendly_style(self):
        """
        Apply touch-friendly styles to the application
        """
        self.setStyleSheet('''
            /* General styles */
            QWidget {
                font-size: 14pt;
            }

            QMainWindow {
                background-color: #f0f0f0;
            }

            /* Touch-friendly buttons */
            QPushButton {
                min-height: 50px;
                padding: 10px 20px;
                font-size: 14pt;
                border-radius: 5px;
                background-color: #4a86e8;
                color: white;
            }

            QPushButton:hover {
                background-color: #5a96f8;
            }

            QPushButton:pressed {
                background-color: #3a76d8;
            }

            /* Touch-friendly input fields */
            QLineEdit, QTextEdit, QComboBox {
                min-height: 40px;
                padding: 5px 10px;
                font-size: 14pt;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }

            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #4a86e8;
            }

            /* Table headers and cells */
            QTableWidget {
                font-size: 12pt;
            }

            QTableWidget::item {
                padding: 8px;
            }

            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 8px;
                font-size: 12pt;
                font-weight: bold;
            }

            /* Tabs for better touch */
            QTabBar::tab {
                min-width: 120px;
                min-height: 40px;
                padding: 8px 16px;
                font-size: 14pt;
            }

            /* Dialog buttons */
            QDialogButtonBox > QPushButton {
                min-width: 100px;
                min-height: 40px;
            }
        ''')
        logger.info("Applied touch-optimized UI settings")

    def center(self):
        """
        Center the window on the screen.
        """
        frame_geometry = self.frameGeometry()
        screen_center = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

    def keyPressEvent(self, event):
        """
        Handle key press events.
        """
        # Handle ESC key to go back to main menu
        if event.key() == Qt.Key_Escape:
            self.change_window.emit('login', None)
        # F5 key to toggle on-screen keyboard manually
        elif event.key() == Qt.Key_F5:
            self._toggle_keyboard()
        # Let F11 handle fullscreen toggle via QShortcut
        elif event.key() == Qt.Key_F11:
            pass # Handled by self.fullscreen_shortcut
        else:
            super().keyPressEvent(event)

    def _toggle_keyboard(self):
        """
        Toggle the on-screen keyboard visibility using the global KeyboardManager.
        """
        app = QApplication.instance()
        if hasattr(app, 'keyboard_manager') and app.keyboard_manager:
            logger.info("Toggling keyboard via global KeyboardManager.")
            app.keyboard_manager.toggle()
            # Update button text based on new state
            is_now_visible = app.keyboard_manager.is_visible()
            self.keyboard_toggle_button.setText(f"⌨ {'Hide' if is_now_visible else 'Show'} Keyboard")
        else:
            logger.warning("KeyboardManager not found on QApplication instance. Cannot toggle keyboard.")

    def toggle_fullscreen(self):
        """
        Toggle between fullscreen and normal window state.
        """
        if self.isFullScreen():
            logger.info("Exiting fullscreen mode")
            self.showNormal()
            # Re-center after exiting fullscreen
            self.center()
            self.fullscreen = False
        else:
            logger.info("Entering fullscreen mode")
            self.showFullScreen()
            self.fullscreen = True

    def showEvent(self, event):
        """
        Override showEvent to apply fullscreen if needed.
        """
        # This ensures the window respects the initial fullscreen setting
        # The `fullscreen` flag is set by ConsultEaseApp
        if hasattr(self, 'fullscreen') and self.fullscreen:
            if not self.isFullScreen(): # Avoid toggling if already fullscreen
                self.showFullScreen()

        # The old _initialize_keyboard() call is removed from here.
        # Keyboard focus events are now handled by the global FocusEventFilter in main.py

        super().showEvent(event)

    def closeEvent(self, event):
        """
        Handle close events.
        """
        # ... existing code ...