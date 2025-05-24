from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon
import os
import logging

from .base_window import BaseWindow
from central_system.utils.theme import ConsultEaseTheme
from ..controllers import RFIDController, StudentController # Import the controllers

class LoginWindow(BaseWindow):
    """
    Login window for student RFID authentication.
    """
    # Signal to notify when a student is authenticated
    student_authenticated = pyqtSignal(object)

    def __init__(self, parent=None):
        self.config = get_config() # Moved BEFORE super().__init__
        super().__init__(parent)
        self.rfid_controller = RFIDController.instance() # Use singleton
        self.student_controller = StudentController.instance() # Assuming it's needed

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing LoginWindow")

        self.init_ui()

        # Initialize state variables
        # self.rfid_reading = False # No longer managed here
        self.scanning_timer = QTimer(self)
        self.scanning_timer.timeout.connect(self.update_scanning_animation)
        self.scanning_animation_frame = 0
        self.scan_active = False # To control animation and status updates

    def init_ui(self):
        """
        Initialize the login UI components.
        """
        # Set up main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create content widget with proper margin
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(50, 30, 50, 30)
        content_layout.setSpacing(20)

        # Dark header background
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {ConsultEaseTheme.PRIMARY_COLOR}; color: {ConsultEaseTheme.TEXT_LIGHT};")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("ConsultEase")
        title_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_XXLARGE}pt; font-weight: bold; color: {ConsultEaseTheme.TEXT_LIGHT};")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        # Instruction label
        instruction_label = QLabel("Please scan your RFID card to authenticate")
        instruction_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_LARGE}pt; color: {ConsultEaseTheme.TEXT_LIGHT};")
        instruction_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(instruction_label)

        # Add header to main layout
        main_layout.addWidget(header_frame, 0)

        # Content area - white background
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f5f5f5;")
        content_frame_layout = QVBoxLayout(content_frame)
        content_frame_layout.setContentsMargins(50, 50, 50, 50)

        # RFID scanning indicator
        self.scanning_frame = QFrame()
        self.scanning_frame.setStyleSheet(f'''
            QFrame {{
                background-color: {ConsultEaseTheme.BG_SECONDARY};
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_LARGE}px;
                border: 2px solid #ccc;
            }}
        ''')
        scanning_layout = QVBoxLayout(self.scanning_frame)
        scanning_layout.setContentsMargins(30, 30, 30, 30)
        scanning_layout.setSpacing(20)

        self.scanning_status_label = QLabel("Ready to Scan")
        self.scanning_status_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_XLARGE}pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.scanning_status_label.setAlignment(Qt.AlignCenter)
        scanning_layout.addWidget(self.scanning_status_label)

        self.rfid_icon_label = QLabel()
        # Ideally, we would have an RFID icon image here
        self.rfid_icon_label.setText("🔄")
        self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.rfid_icon_label.setAlignment(Qt.AlignCenter)
        scanning_layout.addWidget(self.rfid_icon_label)

        # Add manual RFID input field
        manual_input_layout = QHBoxLayout()

        self.rfid_input = QLineEdit()
        self.rfid_input.setPlaceholderText("Enter RFID manually")
        self.rfid_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid #ccc;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px;
                font-size: {ConsultEaseTheme.FONT_SIZE_NORMAL}pt;
                background-color: {ConsultEaseTheme.BG_PRIMARY};
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ConsultEaseTheme.PRIMARY_COLOR};
            }}
        """)
        self.rfid_input.returnPressed.connect(self.handle_manual_rfid_entry)
        manual_input_layout.addWidget(self.rfid_input, 3)

        submit_button = QPushButton("Submit")
        submit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ConsultEaseTheme.PRIMARY_COLOR};
                color: {ConsultEaseTheme.TEXT_LIGHT};
                border: none;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px {ConsultEaseTheme.PADDING_LARGE}px;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                font-weight: bold;
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QPushButton:hover {{
                background-color: #1a4b7c;
            }}
        """)
        submit_button.clicked.connect(self.handle_manual_rfid_entry)
        manual_input_layout.addWidget(submit_button, 1)

        scanning_layout.addLayout(manual_input_layout)

        # Add the simulate button inside the scanning frame
        self.simulate_button = QPushButton("Simulate RFID Scan")
        self.simulate_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ConsultEaseTheme.SECONDARY_COLOR};
                color: {ConsultEaseTheme.TEXT_PRIMARY};
                border: none;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px {ConsultEaseTheme.PADDING_LARGE}px;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                font-weight: bold;
                margin-top: 15px;
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
                color: {ConsultEaseTheme.TEXT_LIGHT};
            }}
        """)
        self.simulate_button.clicked.connect(self.simulate_rfid_scan)
        scanning_layout.addWidget(self.simulate_button)

        content_frame_layout.addWidget(self.scanning_frame, 1)

        # Add content to main layout
        main_layout.addWidget(content_frame, 1)

        # Footer with admin login button
        footer_frame = QFrame()
        footer_frame.setStyleSheet(f"background-color: {ConsultEaseTheme.PRIMARY_COLOR};")
        footer_frame.setFixedHeight(70)
        footer_layout = QHBoxLayout(footer_frame)

        # Admin login button
        admin_button = QPushButton("Admin Login")
        admin_button.setStyleSheet(f'''
            QPushButton {{
                background-color: {ConsultEaseTheme.BG_DARK};
                color: {ConsultEaseTheme.TEXT_LIGHT};
                border: none;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px {ConsultEaseTheme.PADDING_LARGE}px;
                max-width: 200px;
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QPushButton:hover {{
                background-color: #3a4b5c;
            }}
        ''')
        admin_button.clicked.connect(self.admin_login)

        footer_layout.addStretch()
        footer_layout.addWidget(admin_button)
        footer_layout.addStretch()

        main_layout.addWidget(footer_frame, 0)

        # Set the main layout to a widget and make it the central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def showEvent(self, event):
        """
        Called when the window is shown.
        Focus RFID input and register for RFID scans.
        """
        super().showEvent(event) # Call base class method
        self.rfid_input.setFocus()
        self.logger.info("LoginWindow shown, registering RFID callback.")
        self.rfid_controller.register_callback(self.handle_rfid_read)
        self.reset_scan_ui() # Reset UI to initial scanning state
        self.scanning_timer.start(500) # Start animation
        self.scan_active = True
        # Removed any direct keyboard invocation logic (e.g., process management, environment variable setting)
        # Keyboard focus is handled by the global FocusEventFilter

    def hideEvent(self, event):
        """
        Called when the window is hidden.
        Unregister RFID callback.
        """
        self.logger.info("LoginWindow hidden, unregistering RFID callback.")
        self.rfid_controller.unregister_callback(self.handle_rfid_read)
        self.scanning_timer.stop() # Stop animation
        self.scan_active = False
        super().hideEvent(event) # Call base class method

    def resizeEvent(self, event):
        """
        Adjust UI elements on window resize.
        """
        super().resizeEvent(event) # Call base class method for global handling

    def reset_scan_ui(self):
        """Resets the scanning UI to its initial state."""
        self.scanning_status_label.setText("Ready to Scan")
        self.scanning_status_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_XLARGE}pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.rfid_icon_label.setText("🔄")
        self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.rfid_input.clear()
        self.rfid_input.setFocus()
        self.scan_active = True
        if not self.scanning_timer.isActive():
            self.scanning_timer.start(500)

    def update_scanning_animation(self):
        """
        Update the scanning animation frame.
        """
        if not self.scan_active: # Only animate if scanning is supposed to be active
            self.rfid_icon_label.setText("➖") # Idle state
            self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: #ccc;")
            return

        animation_frames = ["🔄", "🔁", "🔃", "🔂"]
        self.scanning_animation_frame = (self.scanning_animation_frame + 1) % len(animation_frames)
        self.rfid_icon_label.setText(animation_frames[self.scanning_animation_frame])
        self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")

    def handle_rfid_read(self, student, rfid_uid, error_message=None):
        """
        Handle RFID read events from the RFIDController.
        The 'student' object is now directly provided by RFIDController.
        """
        self.scanning_timer.stop() # Stop animation
        self.scan_active = False

        if error_message:
            self.logger.error(f"RFID Error: {error_message} for UID: {rfid_uid}")
            self.show_error(error_message)
            # Optionally, restart scanning after a delay
            QTimer.singleShot(3000, self.reset_scan_ui)
            return

        if student:
            self.logger.info(f"Student {student.name} authenticated via RFID UID: {rfid_uid}")
            self.student_authenticated.emit(student)
            self.show_success(f"Welcome, {student.name}!")
            # No need for further DB lookup here, student object is already validated by RFIDController
        else:
            # This case should ideally be handled by RFIDController returning an error_message
            # if the UID is unknown or invalid, but we'll keep a fallback.
            self.logger.warning(f"Unknown RFID UID scanned: {rfid_uid}. Student not found by RFIDController.")
            self.show_error("RFID card not recognized. Please register your card or try again.")
            # Optionally, restart scanning after a delay
            QTimer.singleShot(3000, self.reset_scan_ui)

    def show_success(self, message):
        """
        Show success message and visual feedback.
        """
        self.scanning_status_label.setText("Authenticated")
        self.scanning_status_label.setStyleSheet("font-size: 20pt; color: #4caf50;")
        self.scanning_frame.setStyleSheet('''
            QFrame {
                background-color: #e8f5e9;
                border-radius: 10px;
                border: 2px solid #4caf50;
            }
        ''')
        self.rfid_icon_label.setText("✅")

        # Show message in a popup
        QMessageBox.information(self, "Authentication Success", message)

    def show_error(self, message):
        """
        Show an error message in the UI.
        """
        self.logger.error(f"Login UI Error: {message}")
        self.scanning_status_label.setText(message)
        self.scanning_status_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_LARGE}pt; color: {ConsultEaseTheme.ERROR_COLOR};")
        # self.rfid_icon_label.setText("❌") # Icon set by handle_rfid_read
        # self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: {ConsultEaseTheme.ERROR_COLOR};")

    def admin_login(self):
        """
        Handle admin login button click.
        """
        self.change_window.emit("admin_login", None)

    def simulate_rfid_scan(self):
        """
        Simulate an RFID scan for testing purposes.
        """
        if not self.scan_active:
            self.reset_scan_ui() # Ensure UI is ready for a new scan

        self.logger.info("Simulating RFID scan...")
        self.scanning_status_label.setText("Simulating Scan...")
        self.rfid_icon_label.setText("⏳")
        self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        
        # Call the controller's simulation method
        # The controller will then invoke the registered callback (handle_rfid_read)
        self.rfid_controller.simulate_scan()

    def handle_manual_rfid_entry(self):
        """
        Handle manual RFID UID entry.
        """
        uid = self.rfid_input.text().strip().upper()
        if not uid:
            self.show_error("Please enter an RFID UID.")
            # QTimer.singleShot(2000, self.reset_scan_ui) # Allow re-entry
            return

        if not self.scan_active:
            self.reset_scan_ui() # Ensure UI is ready for a new scan

        self.logger.info(f"Manual RFID entry submitted: {uid}")
        self.scanning_status_label.setText(f"Processing UID: {uid}...")
        self.rfid_icon_label.setText("⏳")
        self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        
        # Clear the input field after submission
        self.rfid_input.clear()
        
        # Let the RFIDController process this UID.
        # The controller will invoke the registered callback (handle_rfid_read)
        # with the student object or an error.
        self.rfid_controller.process_manual_uid(uid)