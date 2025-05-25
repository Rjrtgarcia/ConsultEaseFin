from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QFrame, QMessageBox, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon

import os
import logging
from .base_window import BaseWindow
from ..controllers import AdminController
from ..utils.keyboard_manager import get_keyboard_manager
from ..config import get_config
from ..utils.theme import ConsultEaseTheme

logger = logging.getLogger(__name__)

class AdminLoginWindow(BaseWindow):
    """
    Admin login window for secure access to the admin interface.
    """
    # Signal to notify when an admin is authenticated
    admin_authenticated = pyqtSignal(object)

    def __init__(self, parent=None):
        self.config = get_config()
        super().__init__(parent)
        self.admin_controller = AdminController.instance()
        self.keyboard_manager = get_keyboard_manager()

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Set window properties
        self.setWindowTitle('ConsultEase - Admin Login')

        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Dark header background
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {ConsultEaseTheme.BG_DARK}; color: {ConsultEaseTheme.TEXT_LIGHT};")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel('Admin Login')
        title_label.setStyleSheet(f'font-size: 36pt; font-weight: bold; color: {ConsultEaseTheme.TEXT_LIGHT};')
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        # Add header to main layout
        main_layout.addWidget(header_frame, 0)

        # Content area - white background
        content_frame = QFrame()
        content_frame.setStyleSheet(f"background-color: {ConsultEaseTheme.BG_SECONDARY};")
        content_frame_layout = QVBoxLayout(content_frame)
        content_frame_layout.setContentsMargins(50, 50, 50, 50)

        # Create form layout for inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Username input
        username_label = QLabel('Username:')
        username_label.setStyleSheet('font-size: 16pt; font-weight: bold;')
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Enter username')
        self.username_input.setMinimumHeight(50)  # Make touch-friendly
        self.username_input.setStyleSheet(f'''
            QLineEdit {{
                border: 2px solid {ConsultEaseTheme.BORDER_COLOR};
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {ConsultEaseTheme.PRIMARY_COLOR};
            }}
        ''')
        form_layout.addRow(username_label, self.username_input)

        # Password input
        password_label = QLabel('Password:')
        password_label.setStyleSheet('font-size: 16pt; font-weight: bold;')
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Enter password')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(50)  # Make touch-friendly
        self.password_input.setStyleSheet(f'''
            QLineEdit {{
                border: 2px solid {ConsultEaseTheme.BORDER_COLOR};
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {ConsultEaseTheme.PRIMARY_COLOR};
            }}
        ''')
        form_layout.addRow(password_label, self.password_input)

        # Add form layout to content layout
        content_frame_layout.addLayout(form_layout)

        # Add error message label (hidden by default)
        self.error_label = QLabel('')
        self.error_label.setStyleSheet(f'color: {ConsultEaseTheme.ERROR_COLOR}; font-weight: bold; font-size: 14pt;')
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setVisible(False)
        content_frame_layout.addWidget(self.error_label)

        # Add spacer
        content_frame_layout.addStretch()

        # Add content to main layout
        main_layout.addWidget(content_frame, 1)

        # Footer with buttons
        footer_frame = QFrame()
        footer_frame.setStyleSheet(f"background-color: {ConsultEaseTheme.BG_DARK};")
        footer_frame.setMinimumHeight(80)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(50, 10, 50, 10)

        # Back button
        self.back_button = QPushButton('Back')
        self.back_button.setStyleSheet(f'''
            QPushButton {{
                background-color: {ConsultEaseTheme.TEXT_SECONDARY};
                color: {ConsultEaseTheme.TEXT_LIGHT};
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14pt;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background-color: {ConsultEaseTheme.BORDER_COLOR};
            }}
        ''')
        self.back_button.clicked.connect(self.back_to_login)

        # Login button
        self.login_button = QPushButton('Login')
        self.login_button.setStyleSheet(f'''
            QPushButton {{
                background-color: {ConsultEaseTheme.SUCCESS_COLOR};
                color: {ConsultEaseTheme.TEXT_LIGHT};
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14pt;
                font-weight: bold;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background-color: {ConsultEaseTheme.SUCCESS_COLOR_HOVER};
            }}
        ''')
        self.login_button.clicked.connect(self.login)

        footer_layout.addWidget(self.back_button)
        footer_layout.addStretch()
        footer_layout.addWidget(self.login_button)

        # Add footer to main layout
        main_layout.addWidget(footer_frame, 0)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Set up keyboard shortcuts
        self.password_input.returnPressed.connect(self.login)
        self.username_input.returnPressed.connect(self.focus_password)

        # Configure tab order for better keyboard navigation
        self.setTabOrder(self.username_input, self.password_input)
        self.setTabOrder(self.password_input, self.login_button)
        self.setTabOrder(self.login_button, self.back_button)

    def focus_password(self):
        """
        Focus on the password input field.
        """
        self.password_input.setFocus()

    def show_login_error(self, message):
        """
        Show an error message on the login form.

        Args:
            message (str): The error message to display.
        """
        self.error_label.setText(message)
        self.error_label.setVisible(True)

        # Clear the password field for security
        self.password_input.clear()

    def login(self):
        """
        Handle login button click.
        """
        # Hide any previous error message
        self.error_label.setVisible(False)

        # Get username and password
        username = self.username_input.text().strip()
        password = self.password_input.text()

        # Validate inputs
        if not username:
            self.show_login_error('Please enter a username')
            self.username_input.setFocus()
            return

        if not password:
            self.show_login_error('Please enter a password')
            self.password_input.setFocus()
            return

        # Emit the signal with the credentials as a tuple
        self.admin_authenticated.emit((username, password))

    def back_to_login(self):
        """
        Go back to the login screen.
        """
        self.change_window.emit('login', None)

    def showEvent(self, event):
        """
        Override showEvent to focus the username input.
        Keyboard appearance is now handled by the app-level FocusEventFilter.
        """
        super().showEvent(event)
        logger.info("AdminLoginWindow shown")
        self.username_input.setFocus()
        # No need to set keyboardOnFocus property anymore
        # self.username_input.setProperty("keyboardOnFocus", True)
        # self.password_input.setProperty("keyboardOnFocus", True)

    # def _force_show_keyboard_for_admin(self): # Example of a removed complex keyboard method
    #    pass 