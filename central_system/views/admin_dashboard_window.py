from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
                               QHeaderView, QFrame, QDialog, QFormLayout, QLineEdit,
                               QDialogButtonBox, QMessageBox, QComboBox, QCheckBox,
                               QGroupBox, QFileDialog, QTextEdit, QApplication, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont, QTextCursor

import os
import logging
from .base_window import BaseWindow
from ..controllers import FacultyController, ConsultationController, AdminController, StudentController
from ..models.faculty import Faculty
from ..models.student import Student
from ..models.base import get_db, close_db
from ..services import get_rfid_service
from ..utils.input_sanitizer import (
    sanitize_string, sanitize_email, sanitize_filename, sanitize_path, sanitize_boolean
)
from ..models.base import db_operation_with_retry
from ..config import get_config
from ..utils.icons import IconProvider, Icons
import datetime

# Set up logging
logger = logging.getLogger(__name__)

class AdminDashboardWindow(BaseWindow):
    """
    Admin dashboard window with tabs for managing faculty, students, and system settings.
    """
    # Signals
    faculty_updated = pyqtSignal()
    student_updated = pyqtSignal()
    change_window = pyqtSignal(str, object)  # Add explicit signal if it's missing
    admin_username_changed_signal = pyqtSignal(str) # Define the signal

    def __init__(self, admin=None, parent=None):
        self.admin = admin # Initialize self.admin first
        super().__init__(parent) # Now call super, which will call self.init_ui()
        self.config = get_config() # It's fine to get it again or ensure it's set if needed here.

        # Connect signals
        if hasattr(self.system_tab, 'actual_admin_username_changed_signal'):
             self.system_tab.actual_admin_username_changed_signal.connect(self.handle_admin_username_changed_on_dashboard)

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Set window title
        self.setWindowTitle("ConsultEase - Admin Dashboard")

        # Create a main container widget for the scroll area
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header with admin info and logout button
        header_layout = QHBoxLayout()

        # Admin welcome label
        admin_username = "Admin" # Default
        if self.admin: # self.admin is now expected to be an Admin model object
            admin_username = getattr(self.admin, 'username', 'Admin')

        self.admin_header_label = QLabel(f"Admin Dashboard - Logged in as: {admin_username}")
        self.admin_header_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(self.admin_header_label)

        # Logout button - smaller size
        logout_button = QPushButton("Logout")
        logout_button.setFixedSize(80, 30)
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        logout_button.clicked.connect(self.logout)
        header_layout.addWidget(logout_button)

        main_layout.addLayout(header_layout)

        # Tab widget for different admin functions
        self.tab_widget = QTabWidget()

        # Create tabs
        self.faculty_tab = FacultyManagementTab()
        self.faculty_tab.faculty_updated.connect(self.handle_faculty_updated)

        self.student_tab = StudentManagementTab()
        self.student_tab.student_updated.connect(self.handle_student_updated)

        self.system_tab = SystemMaintenanceTab(admin_info_context=self.admin, dashboard_window_ref=self)

        # Add tabs to tab widget
        self.tab_widget.addTab(self.faculty_tab, "Faculty Management")
        self.tab_widget.addTab(self.student_tab, "Student Management")
        self.tab_widget.addTab(self.system_tab, "System Maintenance")

        main_layout.addWidget(self.tab_widget)

        # Create a scroll area and set its properties
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # Allow the widget to resize
        scroll_area.setWidget(main_container)  # Set the main container as the scroll area's widget

        # Only show scrollbars when needed
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Style the scroll area with improved visibility and touch-friendliness
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 15px;  /* Increased width for better touch targets */
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;  /* Darker color for better visibility */
                min-height: 30px;  /* Increased minimum height for better touch targets */
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #868e96;  /* Even darker on hover */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Set the scroll area as the central widget
        self.setCentralWidget(scroll_area)

    def logout(self):
        """
        Handle logout button click.
        """
        logger.info("Admin logging out")

        # Clean up any resources
        try:
            # Clean up student tab resources
            if hasattr(self, 'student_tab') and self.student_tab:
                if hasattr(self.student_tab, 'cleanup'):
                    self.student_tab.cleanup()
                elif hasattr(self.student_tab, 'scan_dialog') and self.student_tab.scan_dialog:
                    self.student_tab.scan_dialog.close()
        except Exception as e:
            logger.error(f"Error during admin logout cleanup: {str(e)}")

        # Hide this window
        self.hide()

        # Emit signal to change to the main login window (RFID scan) instead of admin login
        logger.info("Redirecting to main login window (RFID scan) after admin logout")
        self.change_window.emit("login", None)

    def handle_faculty_updated(self):
        """
        Handle faculty updated signal.
        """
        # Refresh faculty tab data
        self.faculty_tab.refresh_data()
        # Forward signal
        self.faculty_updated.emit()

    def handle_student_updated(self):
        """
        Handle student updated signal.
        """
        # Refresh student tab data
        self.student_tab.refresh_data()
        # Forward signal
        self.student_updated.emit()

    def handle_admin_username_changed_on_dashboard(self, new_username):
        logger.info(f"AdminDashboard: Handling admin username change to: {new_username}")
        if self.admin: # self.admin is now expected to be an Admin model object
            # Assuming self.admin is the Admin object
            try:
                self.admin.username = new_username
            except AttributeError:
                logger.error(f"AdminDashboard: self.admin (type: {type(self.admin)}) does not have a username attribute or is not the expected object.")
        
        if hasattr(self, 'admin_header_label'):
            self.admin_header_label.setText(f"Admin Dashboard - Logged in as: {new_username}")
            logger.info(f"AdminDashboard: Updated header label to: {self.admin_header_label.text()}")
        else:
            logger.warning("AdminDashboard: admin_header_label not found for update.")

class FacultyManagementTab(QWidget):
    """
    Tab for managing faculty members.
    """
    # Signals
    faculty_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.faculty_controller = FacultyController.instance()
        self.init_ui()

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Create a container widget for the scroll area
        container = QWidget()

        # Main layout
        main_layout = QVBoxLayout(container)

        # Buttons for actions
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Faculty")
        self.add_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.add_button.clicked.connect(self.add_faculty)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Faculty")
        self.edit_button.clicked.connect(self.edit_faculty)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Faculty")
        self.delete_button.setStyleSheet("background-color: #F44336; color: white;")
        self.delete_button.clicked.connect(self.delete_faculty)
        button_layout.addWidget(self.delete_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # Faculty table
        self.faculty_table = QTableWidget()
        self.faculty_table.setColumnCount(6)
        self.faculty_table.setHorizontalHeaderLabels(["ID", "Name", "Department", "Email", "BLE ID", "Status"])
        self.faculty_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.faculty_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.faculty_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.faculty_table.setSelectionMode(QTableWidget.SingleSelection)

        main_layout.addWidget(self.faculty_table)

        # Add some spacing at the bottom for better appearance
        main_layout.addSpacing(10)

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)

        # Only show scrollbars when needed
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Style the scroll area with improved visibility and touch-friendliness
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 15px;  /* Increased width for better touch targets */
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;  /* Darker color for better visibility */
                min-height: 30px;  /* Increased minimum height for better touch targets */
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #868e96;  /* Even darker on hover */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Create a layout for the tab and add the scroll area
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        # Initial data load
        self.refresh_data()

    def refresh_data(self):
        """
        Refresh the faculty data in the table.
        """
        # Clear the table
        self.faculty_table.setRowCount(0)

        try:
            # Get all faculty from the controller
            faculties = self.faculty_controller.get_all_faculty()

            for faculty in faculties:
                row_position = self.faculty_table.rowCount()
                self.faculty_table.insertRow(row_position)

                # Add data to each column
                self.faculty_table.setItem(row_position, 0, QTableWidgetItem(str(faculty.id)))
                self.faculty_table.setItem(row_position, 1, QTableWidgetItem(faculty.name))
                self.faculty_table.setItem(row_position, 2, QTableWidgetItem(faculty.department))
                self.faculty_table.setItem(row_position, 3, QTableWidgetItem(faculty.email))
                self.faculty_table.setItem(row_position, 4, QTableWidgetItem(faculty.ble_id))

                status_item = QTableWidgetItem("Available" if faculty.status else "Unavailable")
                if faculty.status:
                    status_item.setBackground(Qt.green)
                else:
                    status_item.setBackground(Qt.red)
                self.faculty_table.setItem(row_position, 5, status_item)

        except Exception as e:
            logger.error(f"Error refreshing faculty data: {str(e)}")
            QMessageBox.warning(self, "Data Error", f"Failed to refresh faculty data: {str(e)}")

    def add_faculty(self):
        """
        Show dialog to add a new faculty member.
        """
        dialog = FacultyDialog(parent=self)

        # Ensure dialog appears on top
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

        if dialog.exec_() == QDialog.Accepted:
            try:
                # Sanitize inputs
                name = sanitize_string(dialog.name_input.text(), max_length=100)
                department = sanitize_string(dialog.department_input.text(), max_length=100)
                email = sanitize_email(dialog.email_input.text())
                ble_id = sanitize_string(dialog.ble_id_input.text(), max_length=50)
                image_path = dialog.image_path

                # Validate inputs
                if not name:
                    raise ValueError("Faculty name cannot be empty")

                if not department:
                    raise ValueError("Department cannot be empty")

                if not email:
                    raise ValueError("Email is required and must be valid")

                # Validate name and email using Faculty model validation
                if not Faculty.validate_name(name):
                    raise ValueError("Invalid faculty name format")

                if not Faculty.validate_email(email):
                    raise ValueError("Invalid email format")

                if ble_id and not Faculty.validate_ble_id(ble_id):
                    raise ValueError("Invalid BLE ID format")

                # Process image if provided
                if image_path:
                    # Get the filename only
                    import os
                    import shutil

                    # Create images directory if it doesn't exist
                    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    images_dir = os.path.join(base_dir, 'images', 'faculty')
                    if not os.path.exists(images_dir):
                        os.makedirs(images_dir)

                    # Sanitize and generate a unique filename
                    safe_email_prefix = sanitize_filename(email.split('@')[0])
                    safe_basename = sanitize_filename(os.path.basename(image_path))
                    filename = f"{safe_email_prefix}_{safe_basename}"

                    # Ensure the destination path is safe
                    dest_path = sanitize_path(os.path.join(images_dir, filename), base_dir)

                    # Copy the image file
                    shutil.copy2(image_path, dest_path)

                    # Store the relative path
                    image_path = filename
                else:
                    image_path = None

                # Add faculty using controller
                faculty = self.faculty_controller.add_faculty(name, department, email, ble_id, image_path)

                if faculty:
                    QMessageBox.information(self, "Add Faculty", f"Faculty '{name}' added successfully.")
                    self.refresh_data()
                    self.faculty_updated.emit()
                else:
                    QMessageBox.warning(self, "Add Faculty", "Failed to add faculty. This email or BLE ID may already be in use.")

            except ValueError as e:
                logger.error(f"Validation error adding faculty: {str(e)}")
                QMessageBox.warning(self, "Input Error", str(e))
            except Exception as e:
                logger.error(f"Error adding faculty: {str(e)}")
                QMessageBox.warning(self, "Add Faculty", f"Error adding faculty: {str(e)}")

    def edit_faculty(self):
        """
        Show dialog to edit the selected faculty member.
        """
        # Get selected row
        selected_rows = self.faculty_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Edit Faculty", "Please select a faculty member to edit.")
            return

        # Get faculty ID from the first column
        row_index = selected_rows[0].row()
        faculty_id = int(self.faculty_table.item(row_index, 0).text())

        # Get faculty from controller
        faculty = self.faculty_controller.get_faculty_by_id(faculty_id)
        if not faculty:
            QMessageBox.warning(self, "Edit Faculty", f"Faculty with ID {faculty_id} not found.")
            return

        # Create and populate dialog with this tab as parent
        dialog = FacultyDialog(faculty_id=faculty_id, parent=self)
        dialog.name_input.setText(faculty.name)
        dialog.department_input.setText(faculty.department)
        dialog.email_input.setText(faculty.email)
        dialog.ble_id_input.setText(faculty.ble_id)

        # Set image path if available
        if faculty.image_path:
            dialog.image_path_input.setText(faculty.image_path)

        # Ensure dialog appears on top
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

        if dialog.exec_() == QDialog.Accepted:
            try:
                name = dialog.name_input.text().strip()
                department = dialog.department_input.text().strip()
                email = dialog.email_input.text().strip()
                ble_id = dialog.ble_id_input.text().strip()
                image_path = dialog.image_path

                # Process image if provided and different from current
                if image_path and (not faculty.image_path or image_path != faculty.get_image_path()):
                    # Get the filename only
                    import os
                    import shutil

                    # Create images directory if it doesn't exist
                    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    images_dir = os.path.join(base_dir, 'images', 'faculty')
                    if not os.path.exists(images_dir):
                        os.makedirs(images_dir)

                    # Generate a unique filename
                    filename = f"{email.split('@')[0]}_{os.path.basename(image_path)}"
                    dest_path = os.path.join(images_dir, filename)

                    # Copy the image file
                    shutil.copy2(image_path, dest_path)

                    # Store the relative path
                    image_path = filename
                elif faculty.image_path:
                    # Keep the existing image path
                    image_path = faculty.image_path

                # Update faculty using controller
                updated_faculty = self.faculty_controller.update_faculty(
                    faculty_id, name, department, email, ble_id, image_path
                )

                if updated_faculty:
                    QMessageBox.information(self, "Edit Faculty", f"Faculty '{name}' updated successfully.")
                    self.refresh_data()
                    self.faculty_updated.emit()
                else:
                    QMessageBox.warning(self, "Edit Faculty", "Failed to update faculty. This email or BLE ID may already be in use.")

            except Exception as e:
                logger.error(f"Error updating faculty: {str(e)}")
                QMessageBox.warning(self, "Edit Faculty", f"Error updating faculty: {str(e)}")

    def delete_faculty(self):
        """
        Delete the selected faculty member.
        """
        # Get selected row
        selected_rows = self.faculty_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Delete Faculty", "Please select a faculty member to delete.")
            return

        # Get faculty ID and name from the table
        row_index = selected_rows[0].row()
        faculty_id = int(self.faculty_table.item(row_index, 0).text())
        faculty_name = self.faculty_table.item(row_index, 1).text()

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Faculty",
            f"Are you sure you want to delete faculty member '{faculty_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Delete faculty using controller
                success = self.faculty_controller.delete_faculty(faculty_id)

                if success:
                    QMessageBox.information(self, "Delete Faculty", f"Faculty '{faculty_name}' deleted successfully.")
                    self.refresh_data()
                    self.faculty_updated.emit()
                else:
                    QMessageBox.warning(self, "Delete Faculty", f"Failed to delete faculty '{faculty_name}'.")

            except Exception as e:
                logger.error(f"Error deleting faculty: {str(e)}")
                QMessageBox.warning(self, "Delete Faculty", f"Error deleting faculty: {str(e)}")

class FacultyDialog(QDialog):
    """
    Dialog for adding or editing faculty members.
    """
    def __init__(self, faculty_id=None, parent=None):
        super().__init__(parent)
        self.faculty_id = faculty_id
        self.faculty_controller = FacultyController.instance() # Get controller instance
        self.original_ble_id = None # To track changes in BLE ID for validation
        self.original_email = None # To track changes in email for validation
        self.init_ui()
        if self.faculty_id:
            self.load_faculty_data()

    def init_ui(self):
        self.setWindowTitle("Edit Faculty" if self.faculty_id else "Add Faculty")
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)
        self.department_input = QLineEdit()
        form_layout.addRow("Department:", self.department_input)
        self.email_input = QLineEdit()
        form_layout.addRow("Email:", self.email_input)
        self.ble_id_input = QLineEdit()
        form_layout.addRow("BLE ID (MAC or UUID):", self.ble_id_input) # Clarified label

        image_layout = QHBoxLayout()
        self.image_path_input = QLineEdit()
        self.image_path_input.setReadOnly(True)
        self.image_path_input.setPlaceholderText("No image selected")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_image)
        image_layout.addWidget(self.image_path_input)
        image_layout.addWidget(browse_button)
        form_layout.addRow("Profile Image:", image_layout)

        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def browse_image(self):
        """
        Open file dialog to select a faculty image.
        """
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.image_path_input.setText(selected_files[0])

    def accept(self):
        """
        Handle dialog acceptance (OK button click).
        Validates input and calls the appropriate controller method.
        """
        name = sanitize_string(self.name_input.text())
        department = sanitize_string(self.department_input.text())
        email = sanitize_email(self.email_input.text())
        ble_id = sanitize_string(self.ble_id_input.text()) # Sanitized, can be empty
        image_path = sanitize_path(self.image_path_input.text()) # Sanitized, can be empty

        if not name or not department or not email:
            QMessageBox.warning(self, "Input Error", "Name, department, and email are required.")
            return

        # More specific email validation (optional, basic one done by sanitize_email)
        if "@" not in email or "." not in email.split("@")[-1]:
            QMessageBox.warning(self, "Input Error", "Please enter a valid email address.")
            return

        try:
            if self.faculty_id:
                # Update existing faculty
                self.faculty_controller.update_faculty(
                    faculty_id=self.faculty_id,
                    name=name,
                    department=department,
                    email=email,
                    ble_id=ble_id if ble_id else None, 
                    image_path=image_path if image_path else None
                )
                QMessageBox.information(self, "Success", "Faculty updated successfully.")
            else:
                # Add new faculty
                self.faculty_controller.add_faculty(
                    name=name,
                    department=department,
                    email=email,
                    ble_id=ble_id if ble_id else None, 
                    image_path=image_path if image_path else None
                )
                QMessageBox.information(self, "Success", "Faculty added successfully.")
            
            super().accept() # Call accept only if controller operations were successful

        except ValueError as ve:
            logger.warning(f"Validation error during faculty save: {str(ve)}")
            QMessageBox.warning(self, "Error", str(ve))
            # Do not call super().accept() here, so the dialog stays open
        except Exception as e:
            logger.error(f"Error saving faculty: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            # Do not call super().accept() here, so the dialog stays open

    def reject(self):
        super().reject()

    def load_faculty_data(self):
        """
        Load existing faculty data into the dialog fields when editing.
        """
        if not self.faculty_id:
            return # Should not happen if called correctly

        faculty = self.faculty_controller.get_faculty_by_id(self.faculty_id)
        if faculty:
            self.name_input.setText(faculty.name)
            self.department_input.setText(faculty.department)
            self.email_input.setText(faculty.email)
            self.original_email = faculty.email # Store original for reference
            
            self.ble_id_input.setText(faculty.ble_id if faculty.ble_id else "")
            self.original_ble_id = faculty.ble_id # Store original for reference
            
            self.image_path_input.setText(faculty.image_path if faculty.image_path else "")
        else:
            QMessageBox.warning(self, "Error", f"Could not load data for faculty ID: {self.faculty_id}")
            self.close() # Close dialog if data cannot be loaded

class StudentManagementTab(QWidget):
    """
    Tab for managing students.
    """
    # Signals
    student_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_controller = StudentController.instance()
        self.rfid_service = get_rfid_service()
        self.scan_dialog = None
        self.init_ui()

    def __del__(self):
        self.cleanup()

    def init_ui(self):
        container = QWidget()
        main_layout = QVBoxLayout(container)
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Student")
        self.add_button.clicked.connect(self.add_student)
        button_layout.addWidget(self.add_button)
        self.edit_button = QPushButton("Edit Student")
        self.edit_button.clicked.connect(self.edit_student)
        button_layout.addWidget(self.edit_button)
        self.delete_button = QPushButton("Delete Student")
        self.delete_button.clicked.connect(self.delete_student)
        button_layout.addWidget(self.delete_button)
        self.scan_button = QPushButton("Scan RFID for Table")
        self.scan_button.clicked.connect(self.scan_rfid_for_table_selection)
        button_layout.addWidget(self.scan_button)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        self.student_table = QTableWidget()
        self.student_table.setColumnCount(4)
        self.student_table.setHorizontalHeaderLabels(["ID", "Name", "Department", "RFID UID"])
        main_layout.addWidget(self.student_table)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0,0,0,0)
        tab_layout.addWidget(scroll_area)
        self.refresh_data()

    def cleanup(self):
        logger.info("Cleaning up StudentManagementTab resources")
        if self.scan_dialog and self.scan_dialog.isVisible():
            self.scan_dialog.close()
            self.scan_dialog = None

    def refresh_data(self):
        try:
            self.student_table.setRowCount(0)
            students = self.student_controller.get_all_students()
            if students:
                for student in students:
                    row_position = self.student_table.rowCount()
                    self.student_table.insertRow(row_position)
                    self.student_table.setItem(row_position, 0, QTableWidgetItem(str(student.id)))
                    self.student_table.setItem(row_position, 1, QTableWidgetItem(student.name))
                    self.student_table.setItem(row_position, 2, QTableWidgetItem(student.department))
                    self.student_table.setItem(row_position, 3, QTableWidgetItem(student.rfid_uid))
            else:
                logger.info("No students found by controller during refresh.")
        except Exception as e:
            logger.error(f"Error refreshing student data via controller: {str(e)}")
            QMessageBox.warning(self, "Data Error", f"Failed to refresh student data: {str(e)}")

    def add_student(self):
        dialog = StudentDialog(self.student_controller, self.rfid_service, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            name = dialog.name_edit.text().strip()
            department = dialog.department_edit.text().strip()
            rfid_uid = dialog.rfid_edit.text().strip()

            if not (name and department and rfid_uid):
                QMessageBox.warning(self, "Input Error", "Name, Department, and RFID UID are required.")
                return
            
            logger.info(f"Attempting to add student via controller: {name}, Dept: {department}, RFID: {rfid_uid}")
            try:
                new_student = self.student_controller.add_student(name=name, department=department, rfid_uid=rfid_uid)
                
                if new_student:
                    QMessageBox.information(self, "Add Student", f"Student '{new_student.name}' added successfully.")
                    self.refresh_data()
                    self.student_updated.emit()
                    logger.info(f"Student '{new_student.name}' added and UI updated.")
                # No else needed, as controller raises ValueError for known issues (e.g., RFID exists)
                # or db_operation_with_retry handles other DB exceptions.
            except ValueError as ve: 
                logger.error(f"Failed to add student: {str(ve)}")
                QMessageBox.warning(self, "Add Student Error", str(ve))
            except Exception as e: 
                logger.error(f"Unexpected error adding student via controller: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Add Student Error", "An unexpected error occurred.")

    def edit_student(self):
        """
        Show dialog to edit the selected student.
        """
        selected_rows = self.student_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Edit Student", "Please select a student to edit.")
            return

        row_index = selected_rows[0].row()
        student_id_text = self.student_table.item(row_index, 0).text()
        try:
            student_id = int(student_id_text)
        except ValueError:
            logger.error(f"Invalid student ID in table: {student_id_text}")
            QMessageBox.critical(self, "Error", "Invalid student ID selected.")
            return
        
        current_student = self.student_controller.get_student_by_id(student_id)

        if not current_student:
            QMessageBox.warning(self, "Edit Student", f"Student with ID {student_id} not found.")
            return

        dialog = StudentDialog(self.student_controller, self.rfid_service, student_id=student_id, current_rfid=current_student.rfid_uid, parent=self)
        dialog.name_edit.setText(current_student.name)
        dialog.department_edit.setText(current_student.department)
        dialog.rfid_edit.setText(current_student.rfid_uid)
        dialog.rfid_uid = current_student.rfid_uid

        if dialog.exec_() == QDialog.Accepted:
            try:
                name = dialog.name_edit.text().strip()
                department = dialog.department_edit.text().strip()
                rfid_uid = dialog.rfid_edit.text().strip()

                if not (name and department and rfid_uid):
                    QMessageBox.warning(self, "Input Error", "Name, Department, and RFID UID are required.")
                    return

                logger.info(f"Attempting to update student via controller: ID={student_id}, Name={name}, Dept={department}, RFID={rfid_uid}")
                updated_student = self.student_controller.update_student(
                    student_id=student_id, name=name, department=department, rfid_uid=rfid_uid
                )
                
                if updated_student: 
                    QMessageBox.information(self, "Edit Student", f"Student '{updated_student.name}' updated successfully.")
                    self.refresh_data()
                    self.student_updated.emit()
                    logger.info(f"Student '{updated_student.name}' updated and UI refreshed.")
            except ValueError as ve: 
                logger.error(f"Validation error updating student: {str(ve)}")
                QMessageBox.warning(self, "Update Student Error", str(ve))
            except Exception as e:
                logger.error(f"Unexpected error updating student via controller: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Update Student Error", "An unexpected error occurred while updating.")

    def delete_student(self):
        selected_rows = self.student_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Delete Student", "Please select a student to delete.")
            return

        row_index = selected_rows[0].row()
        student_id_text = self.student_table.item(row_index, 0).text()
        student_name = self.student_table.item(row_index, 1).text()
        try:
            student_id = int(student_id_text)
        except ValueError:
            logger.error(f"Invalid student ID for deletion: {student_id_text}")
            QMessageBox.critical(self, "Error", "Invalid student ID selected for deletion.")
            return

        reply = QMessageBox.question(self, "Delete Student",
            f"Are you sure you want to delete student '{student_name}' (ID: {student_id})? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                logger.info(f"Attempting to delete student via controller: ID={student_id}, Name={student_name}")
                success = self.student_controller.delete_student(student_id=student_id)
                
                if success:
                    QMessageBox.information(self, "Delete Student", f"Student '{student_name}' deleted successfully.")
                    self.refresh_data()
                    self.student_updated.emit()
                    logger.info(f"Student '{student_name}' deleted and UI refreshed.")
            except ValueError as ve: 
                logger.error(f"Failed to delete student: {str(ve)}")
                QMessageBox.warning(self, "Delete Student Error", str(ve))
            except Exception as e:
                logger.error(f"Unexpected error deleting student via controller: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Delete Student Error", f"Could not delete student '{student_name}'. An unexpected error occurred.")

    def scan_rfid_for_table_selection(self):
        rfid_scan_dialog = RFIDScanDialog(self.rfid_service, parent=self)
        if rfid_scan_dialog.exec_() == QDialog.Accepted:
            rfid_uid = rfid_scan_dialog.get_rfid_uid()
            if rfid_uid:
                student = self.student_controller.get_student_by_rfid(rfid_uid)
                if student:
                    for row in range(self.student_table.rowCount()):
                        if self.student_table.item(row, 3).text() == rfid_uid:
                            self.student_table.selectRow(row)
                            QMessageBox.information(self, "Student Found", f"Student '{student.name}' selected in table.")
                            return
                    QMessageBox.information(self, "Student Found", f"Student '{student.name}' (RFID: {rfid_uid}) found but might not be visible due to table filters/paging (if any).")
                else:
                    QMessageBox.information(self, "Student Not Found", f"No student found with RFID: {rfid_uid}")
            else:
                logger.info("Admin tab RFID Scan dialog cancelled or no UID obtained.")

class StudentDialog(QDialog):
    """
    Dialog for adding or editing students.
    """
    def __init__(self, student_controller, rfid_service, student_id=None, current_rfid=None, parent=None):
        super().__init__(parent)
        self.student_controller = student_controller
        self.rfid_service = rfid_service
        self.student_id = student_id
        self.original_rfid_uid = current_rfid # Store original RFID for edit mode if needed for complex validation
        self.rfid_uid = current_rfid # This will be updated by scan_rfid or manual input
        self.scan_dialog_instance = None
        self.init_ui()

        if self.student_id:
            self.setWindowTitle("Edit Student")
            self.load_student_data()
        else:
            self.setWindowTitle("Add Student")

    def init_ui(self):
        self.setWindowTitle("Edit Student" if self.student_id else "Add Student")
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter student name")
        form_layout.addRow("Name:", self.name_edit)

        self.department_edit = QLineEdit()
        self.department_edit.setPlaceholderText("Enter department")
        form_layout.addRow("Department:", self.department_edit)

        self.rfid_edit = QLineEdit()
        self.rfid_edit.setPlaceholderText("Click 'Scan RFID' or enter manually")
        self.rfid_scan_button = QPushButton("Scan RFID")
        self.rfid_scan_button.setIcon(IconProvider.get_button_icon(Icons.RFID))
        self.rfid_scan_button.clicked.connect(self.scan_rfid)

        rfid_layout = QHBoxLayout()
        rfid_layout.addWidget(self.rfid_edit)
        rfid_layout.addWidget(self.rfid_scan_button)
        form_layout.addRow("RFID UID:", rfid_layout)

        layout.addLayout(form_layout)

        # Progress Indicator (optional, can be shown during blocking operations)
        self.progress_indicator = ProgressIndicator(self)
        self.progress_indicator.setVisible(False)
        layout.addWidget(self.progress_indicator)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.scan_dialog = None # Initialize scan_dialog attribute

        if self.student_id:
            self.load_student_data()

    def load_student_data(self):
        if not self.student_id:
            return
        try:
            # Ensure get_student_by_id does not require a db session as argument
            # or is called within a session managed by the controller if needed for lazy loading
            student = self.student_controller.get_student_by_id(self.student_id)
            if student:
                self.name_edit.setText(student.name)
                self.department_edit.setText(student.department)
                self.rfid_edit.setText(student.rfid_uid)
                self.original_rfid_uid = student.rfid_uid
            else:
                QMessageBox.warning(self, "Error", "Student not found.")
                self.reject() # or disable save
        except Exception as e:
            logger.error(f"Error loading student data: {e}")
            QMessageBox.critical(self, "Error", f"Could not load student details: {e}")
            self.reject()

    def scan_rfid(self):
        # Ensure rfid_service is passed and available
        if not hasattr(self, 'rfid_service') or not self.rfid_service:
            QMessageBox.critical(self, "Error", "RFID Service not available.")
            return

        # Pass self.rfid_service to RFIDScanDialog
        self.scan_dialog = RFIDScanDialog(self.rfid_service, parent=self)
        if self.scan_dialog.exec_() == QDialog.Accepted:
            rfid_uid = self.scan_dialog.rfid_uid
            if rfid_uid:
                self.rfid_edit.setText(rfid_uid)
        self.scan_dialog.deleteLater() # Ensure dialog is cleaned up
        self.scan_dialog = None

    def accept(self):
        name = sanitize_string(self.name_edit.text())
        department = sanitize_string(self.department_edit.text())
        rfid_uid = sanitize_string(self.rfid_edit.text())

        if not name or not department or not rfid_uid:
            QMessageBox.warning(self, "Input Error", "All fields (Name, Department, RFID UID) are required.")
            return

        self.progress_indicator.start_animation()
        self.progress_indicator.setVisible(True)
        QApplication.processEvents() # Ensure UI updates

        try:
            if self.student_id: # Update existing student
                # The controller's update_student method should handle checking if the new RFID UID
                # conflicts with another student, not the one being edited.
                self.student_controller.update_student(
                    student_id=self.student_id,
                    name=name,
                    department=department,
                    rfid_uid=rfid_uid
                )
                QMessageBox.information(self, "Success", "Student updated successfully.")
            else: # Add new student
                self.student_controller.add_student(
                    name=name,
                    department=department,
                    rfid_uid=rfid_uid
                )
                QMessageBox.information(self, "Success", "Student added successfully.")
            
            super().accept() # Call QDialog.accept() to close dialog and signal success
        except ValueError as ve:
            logger.warning(f"Validation error while saving student: {ve}")
            QMessageBox.warning(self, "Validation Error", str(ve))
        except Exception as e:
            logger.error(f"Error saving student: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
        finally:
            self.progress_indicator.stop_animation()
            self.progress_indicator.setVisible(False)

    def reject(self):
        super().reject()

class RFIDScanDialog(QDialog):
    def __init__(self, rfid_service=None, parent=None):
        super().__init__(parent)
        self.rfid_uid = ""
        self.rfid_service = rfid_service or get_rfid_service()

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setWindowModality(Qt.ApplicationModal)

        self.scan_received = False

        self.init_ui()

        self.callback_fn = self.handle_rfid_scan

        self.rfid_service.register_callback(self.callback_fn)

        self.scanning_timer = QTimer(self)
        self.scanning_timer.timeout.connect(self.update_animation)
        self.scanning_timer.start(500)

        if os.environ.get('RFID_SIMULATION_MODE', 'true').lower() == 'true':
            self.simulate_button = QPushButton("Simulate Scan")
            self.simulate_button.clicked.connect(self.simulate_scan)
            self.layout().addWidget(self.simulate_button, alignment=Qt.AlignCenter)

    def init_ui(self):
        self.setWindowTitle("RFID Scan")
        self.setFixedSize(350, 350)

        layout = QVBoxLayout()

        instruction_label = QLabel("Please scan the 13.56 MHz RFID card...")
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("font-size: 14pt;")
        layout.addWidget(instruction_label)

        self.animation_label = QLabel("🔄")
        self.animation_label.setAlignment(Qt.AlignCenter)
        self.animation_label.setStyleSheet("font-size: 48pt; color: #4a86e8;")
        layout.addWidget(self.animation_label)

        self.status_label = QLabel("Scanning...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12pt; color: #4a86e8;")
        layout.addWidget(self.status_label)

        manual_section = QGroupBox("Manual RFID Input")
        manual_layout = QVBoxLayout()

        manual_instructions = QLabel("If scanning doesn't work, enter the RFID manually:")
        manual_layout.addWidget(manual_instructions)

        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("Enter RFID UID manually")
        self.manual_input.returnPressed.connect(self.handle_manual_input)
        manual_layout.addWidget(self.manual_input)

        manual_submit = QPushButton("Submit Manual RFID")
        manual_submit.clicked.connect(self.handle_manual_input)
        manual_layout.addWidget(manual_submit)

        manual_section.setLayout(manual_layout)
        layout.addWidget(manual_section)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def handle_manual_input(self):
        uid = self.manual_input.text().strip().upper()
        if uid:
            logger.info(f"Manual RFID input: {uid}")
            self.manual_input.clear()
            self.handle_rfid_scan(None, uid)
        else:
            self.status_label.setText("Please enter a valid RFID UID")
            self.status_label.setStyleSheet("font-size: 12pt; color: #f44336;")
            QTimer.singleShot(2000, lambda: self.reset_status_label())

    def reset_status_label(self):
        if not self.scan_received:
            self.status_label.setText("Scanning...")
            self.status_label.setStyleSheet("font-size: 12pt; color: #4a86e8;")

    def update_animation(self):
        if self.scan_received:
            return

        animations = ["🔄", "🔁", "🔃", "🔂"]
        current_index = animations.index(self.animation_label.text()) if self.animation_label.text() in animations else 0
        next_index = (current_index + 1) % len(animations)
        self.animation_label.setText(animations[next_index])

    def handle_rfid_scan(self, student=None, rfid_uid=None):
        logger.info(f"RFIDScanDialog received scan: {rfid_uid}")

        if not rfid_uid or self.scan_received:
            logger.info(f"Ignoring scan - no UID or already received: {rfid_uid}")
            return

        self.scan_received = True
        self.rfid_uid = rfid_uid

        self.scanning_timer.stop()
        self.animation_label.setText("✅")
        self.animation_label.setStyleSheet("font-size: 48pt; color: #4caf50;")
        self.status_label.setText(f"Card detected: {self.rfid_uid}")
        self.status_label.setStyleSheet("font-size: 12pt; color: #4caf50;")

        if student:
            QMessageBox.warning(
                self,
                "RFID Already Registered",
                f"This RFID card is already registered to student:\n{student.name}"
            )

        QTimer.singleShot(1500, self.accept)

    def closeEvent(self, event):
        if hasattr(self, 'callback_fn') and self.callback_fn:
            try:
                self.rfid_service.unregister_callback(self.callback_fn)
                logger.info("Unregistered RFID callback in RFIDScanDialog closeEvent")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback in closeEvent: {str(e)}")
        super().closeEvent(event)

    def reject(self):
        if hasattr(self, 'callback_fn') and self.callback_fn:
            try:
                self.rfid_service.unregister_callback(self.callback_fn)
                logger.info("Unregistered RFID callback in RFIDScanDialog reject")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback in reject: {str(e)}")
        super().reject()

    def accept(self):
        if hasattr(self, 'callback_fn') and self.callback_fn:
            try:
                self.rfid_service.unregister_callback(self.callback_fn)
                logger.info("Unregistered RFID callback in RFIDScanDialog accept")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback in accept: {str(e)}")
        super().accept()

    def simulate_scan(self):
        try:
            if hasattr(self, 'simulate_button'):
                self.simulate_button.setEnabled(False)

            if not self.scan_received:
                logger.info("Simulating RFID scan from RFIDScanDialog")

                import random
                random_uid = ''.join(random.choices('0123456789ABCDEF', k=8))
                logger.info(f"Generated random RFID: {random_uid}")

                self.rfid_service.simulate_card_read(random_uid)

                logger.info(f"Simulation complete, RFID: {random_uid}")
        except Exception as e:
            logger.error(f"Error in RFID simulation: {str(e)}")
            self.status_label.setText(f"Simulation error: {str(e)}")
            if hasattr(self, 'simulate_button'):
                self.simulate_button.setEnabled(True)

    def get_rfid_uid(self):
        return self.rfid_uid

class SystemMaintenanceTab(QWidget):
    actual_admin_username_changed_signal = pyqtSignal(str)

    def __init__(self, admin_info_context=None, dashboard_window_ref=None, parent=None):
        super().__init__(parent if parent else dashboard_window_ref) 
        self.config = get_config()
        self.admin_info_context = admin_info_context
        self.dashboard_window_ref = dashboard_window_ref
        self.faculty_controller = FacultyController.instance()
        self.consultation_controller = ConsultationController.instance()
        self.admin_controller = AdminController.instance()
        self.init_ui() 
        self.load_faculty_list()

    def init_ui(self):
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10,10,10,10)
        main_layout.setSpacing(15)

        database_group = QGroupBox("Database Maintenance")
        database_layout = QVBoxLayout()
        backup_button = QPushButton("Backup Database")
        backup_button.clicked.connect(self.backup_database)
        database_layout.addWidget(backup_button)
        restore_button = QPushButton("Restore Database")
        restore_button.clicked.connect(self.restore_database)
        database_layout.addWidget(restore_button)
        database_group.setLayout(database_layout)
        main_layout.addWidget(database_group)

        admin_group = QGroupBox("Admin Account Management")
        admin_account_main_layout = QVBoxLayout()
        username_form = QFormLayout()
        self.current_password_username_input = QLineEdit()
        self.current_password_username_input.setEchoMode(QLineEdit.Password)
        username_form.addRow("Current Password (for username change):", self.current_password_username_input)
        self.new_username_input = QLineEdit()
        username_form.addRow("New Username:", self.new_username_input)
        change_username_button = QPushButton("Change Username")
        change_username_button.clicked.connect(self.change_admin_username)
        username_form.addRow("", change_username_button)
        admin_account_main_layout.addLayout(username_form)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        admin_account_main_layout.addWidget(separator)
        password_form = QFormLayout()
        self.current_password_password_input = QLineEdit()
        self.current_password_password_input.setEchoMode(QLineEdit.Password)
        password_form.addRow("Current Password (for password change):", self.current_password_password_input)
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        password_form.addRow("New Password:", self.new_password_input)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        password_form.addRow("Confirm New Password:", self.confirm_password_input)
        change_password_button = QPushButton("Change Password")
        change_password_button.clicked.connect(self.change_admin_password)
        password_form.addRow("", change_password_button)
        admin_account_main_layout.addLayout(password_form)
        admin_group.setLayout(admin_account_main_layout)
        main_layout.addWidget(admin_group)

        logs_group = QGroupBox("System Logs")
        logs_layout = QVBoxLayout()
        view_logs_button = QPushButton("View Logs")
        view_logs_button.clicked.connect(self.view_logs)
        logs_layout.addWidget(view_logs_button)
        logs_group.setLayout(logs_layout)
        main_layout.addWidget(logs_group)

        faculty_desk_group = QGroupBox("Faculty Desk Unit Test")
        faculty_desk_layout = QVBoxLayout()
        faculty_select_layout = QHBoxLayout()
        faculty_label = QLabel("Select Faculty:")
        self.faculty_combo = QComboBox()
        self.faculty_combo.setMinimumWidth(200)
        faculty_select_layout.addWidget(faculty_label)
        faculty_select_layout.addWidget(self.faculty_combo)
        faculty_desk_layout.addLayout(faculty_select_layout)
        test_connection_button = QPushButton("Test Faculty Desk Connection")
        test_connection_button.clicked.connect(self.test_faculty_desk_connection)
        faculty_desk_layout.addWidget(test_connection_button)
        faculty_desk_group.setLayout(faculty_desk_layout)
        main_layout.addWidget(faculty_desk_group)

        settings_group = QGroupBox("System Settings")
        settings_layout = QFormLayout()
        self.mqtt_host_input = QLineEdit(self.config.get('mqtt.broker_host', 'localhost'))
        settings_layout.addRow("MQTT Broker Host:", self.mqtt_host_input)
        self.mqtt_port_input = QLineEdit(str(self.config.get('mqtt.broker_port', 1883)))
        settings_layout.addRow("MQTT Broker Port:", self.mqtt_port_input)
        self.auto_start_checkbox = QCheckBox()
        self.auto_start_checkbox.setChecked(self.config.get('system.auto_start', True))
        settings_layout.addRow("Auto-start on boot:", self.auto_start_checkbox)
        save_settings_button = QPushButton("Save Settings")
        save_settings_button.clicked.connect(self.save_settings)
        settings_layout.addRow("", save_settings_button)
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        main_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)
        scroll_area.setStyleSheet(""" QScrollArea { border: none; background-color: transparent; } 
                                      QScrollBar:vertical { border: none; background: #f0f0f0; width: 15px; margin: 0px; } 
                                      QScrollBar::handle:vertical { background: #adb5bd; min-height: 30px; border-radius: 7px; } 
                                      QScrollBar::handle:vertical:hover { background: #868e96; } 
                                      QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } 
                                      QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; } """)
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0,0,0,0)
        tab_layout.addWidget(scroll_area)
    
    def backup_database(self):
        logger.warning("Database backup functionality is not fully implemented yet.")
        # Recommendation for pg_dump (security - avoid shell=True):
        # DB_USER = self.config.get('database.user')
        # DB_HOST = self.config.get('database.host')
        # DB_NAME = self.config.get('database.name')
        # file_path = 'backup.sql' # Should be a configurable path
        # env = os.environ.copy()
        # if self.config.get('database.password'):
        #     env['PGPASSWORD'] = self.config.get('database.password')
        # cmd_list = ['pg_dump', '-U', DB_USER, '-h', DB_HOST, '-d', DB_NAME, '-f', file_path]
        # try:
        #     result = subprocess.run(cmd_list, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
        #     if result.returncode == 0:
        #         QMessageBox.information(self, "Backup", f"Database backup successful to {file_path}")
        #     else:
        #         logger.error(f"Database backup failed. STDERR: {result.stderr}")
        #         QMessageBox.critical(self, "Backup Error", f"Database backup failed: {result.stderr}")
        # except FileNotFoundError:
        #     logger.error("pg_dump command not found. Ensure PostgreSQL client tools are installed and in PATH.")
        #     QMessageBox.critical(self, "Backup Error", "pg_dump command not found. Ensure PostgreSQL client tools are installed and in PATH.")
        # except Exception as e:
        #     logger.error(f"Error during database backup: {e}")
        #     QMessageBox.critical(self, "Backup Error", f"An unexpected error occurred: {e}")
        QMessageBox.information(self, "Not Implemented", "Database backup is not yet implemented.")
        # raise NotImplementedError("Database backup functionality needs to be securely implemented.")

    def restore_database(self):
        logger.warning("Database restore functionality is not fully implemented yet.")
        # Recommendation for psql (security - avoid shell=True):
        # Similar structure to backup_database, using 'psql' instead of 'pg_dump'
        # Ensure to handle potential issues like database existence, user permissions etc.
        QMessageBox.information(self, "Not Implemented", "Database restore is not yet implemented.")
        # raise NotImplementedError("Database restore functionality needs to be securely implemented.")

    def view_logs(self):
        log_dialog = LogViewerDialog(self)
        log_dialog.exec_()

    def load_faculty_list(self):
        try:
            faculties = self.faculty_controller.get_all_faculty()
            self.faculty_combo.clear()
            for faculty in faculties:
                self.faculty_combo.addItem(f"{faculty.name} (ID: {faculty.id})", faculty.id)
            logger.info(f"Loaded {len(faculties)} faculty members into SystemMaintenanceTab dropdown")
        except Exception as e:
            logger.error(f"Error loading faculty list for SystemMaintenanceTab: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load faculty list: {str(e)}")

    def test_faculty_desk_connection(self):
        try:
            if self.faculty_combo.count() == 0:
                QMessageBox.warning(self, "Test Connection", "No faculty. Add faculty first.")
                return
            faculty_id = self.faculty_combo.currentData()
            if not faculty_id:
                QMessageBox.warning(self, "Test Connection", "Please select a faculty.")
                return
            faculty_name = self.faculty_combo.currentText().split(" (ID:")[0]
            
            progress_dialog = QMessageBox(self)
            progress_dialog.setWindowTitle("Testing Connection")
            progress_dialog.setText(f"Sending test to {faculty_name}... Check desk unit.")
            progress_dialog.setStandardButtons(QMessageBox.NoButton)
            progress_dialog.show()
            QApplication.processEvents()

            success = self.consultation_controller.test_faculty_desk_connection(faculty_id)
            progress_dialog.close()

            if success:
                QMessageBox.information(self, "Test Connection", f"Test message sent to {faculty_name}.")
            else:
                QMessageBox.warning(self, "Test Connection", f"Failed to send test message to {faculty_name}. Check MQTT settings and connectivity.")
        except Exception as e:
            if 'progress_dialog' in locals() and progress_dialog.isVisible(): progress_dialog.close()
            logger.error(f"Error testing faculty desk connection: {str(e)}")
            QMessageBox.critical(self, "Test Connection Error", str(e))

    def change_admin_username(self):
        try:
            if not self.admin_info_context:
                QMessageBox.warning(self, "Admin Error", "Admin context not available.")
                return
            admin_id = self.admin_info_context.get('id') if isinstance(self.admin_info_context, dict) else self.admin_info_context.id
            
            current_password = self.current_password_username_input.text()
            new_username = self.new_username_input.text().strip()
            if not (current_password and new_username):
                QMessageBox.warning(self, "Input Error", "All fields for username change are required.")
                return

            success = self.admin_controller.change_username(admin_id, current_password, new_username)
            if success:
                self.actual_admin_username_changed_signal.emit(new_username)
                if isinstance(self.admin_info_context, dict):
                    self.admin_info_context['username'] = new_username

                QMessageBox.information(self, "Username Changed", "Username changed successfully.")
                self.current_password_username_input.clear()
                self.new_username_input.clear()
            else:
                QMessageBox.warning(self, "Username Change Failed", "Failed. Check password or new username may be taken.")
        except Exception as e:
            logger.error(f"Error changing admin username: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")

    def change_admin_password(self):
        try:
            if not self.admin_info_context:
                QMessageBox.warning(self, "Admin Error", "Admin context not available to identify current admin.")
                return
            
            admin_id = self.admin_info_context.get('id') if isinstance(self.admin_info_context, dict) else self.admin_info_context.id
            if not admin_id:
                QMessageBox.warning(self, "Admin Error", "Could not determine Admin ID from context.")
                return

            current_password = self.current_password_password_input.text()
            new_password = self.new_password_input.text()
            confirm_password = self.confirm_password_input.text()

            if not (current_password and new_password and confirm_password):
                QMessageBox.warning(self, "Input Error", "All fields are required.")
                return
            if new_password != confirm_password:
                QMessageBox.warning(self, "Input Error", "New passwords do not match.")
                return
            
            from ..models.admin import Admin as AdminModel
            is_strong, msg = AdminModel.validate_password_strength(new_password)
            if not is_strong:
                QMessageBox.warning(self, "Password Policy", msg)
                return

            success = self.admin_controller.change_password(admin_id, current_password, new_password)
            if success:
                QMessageBox.information(self, "Password Changed", "Password changed successfully.")
                self.current_password_password_input.clear()
                self.new_password_input.clear()
                self.confirm_password_input.clear()
            else:
                QMessageBox.warning(self, "Password Change Failed", "Failed. Check current password or new password policy.")
        except ValueError as ve: 
             QMessageBox.warning(self, "Password Policy/Error", str(ve))
        except Exception as e:
            logger.error(f"Error changing admin password: {str(e)}")
            QMessageBox.critical(self, "Error", str(e))

    def save_settings(self):
        try:
            mqtt_host = self.mqtt_host_input.text().strip()
            mqtt_port_str = self.mqtt_port_input.text().strip()
            auto_start = self.auto_start_checkbox.isChecked()

            if not (mqtt_host and mqtt_port_str):
                QMessageBox.warning(self, "Input Error", "MQTT Host and Port are required.")
                return
            try:
                mqtt_port = int(mqtt_port_str)
                if not (0 < mqtt_port < 65536):
                    raise ValueError("Port out of range")
            except ValueError:
                QMessageBox.warning(self, "Input Error", "MQTT Port must be a valid number (1-65535).")
                return

            logger.info(f"Saving settings: MQTT Host={mqtt_host}, Port={mqtt_port}, AutoStart={auto_start}")
            
            self.config.set('mqtt.broker_host', mqtt_host)
            self.config.set('mqtt.broker_port', mqtt_port)
            self.config.set('system.auto_start', auto_start)
            
            if self.config.save():
                QMessageBox.information(self, "Settings Saved", 
                    "Settings saved to config.json. Restart application for changes to MQTT broker or auto-start to take full effect.")
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save settings to config.json.")
            self.load_faculty_list()
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred: {str(e)}")

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.log_file_path = self.config.get('logging.file', 'consultease.log') 
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        self.setWindowTitle("System Logs")
        self.resize(800, 600)
        layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.log_text)
        controls_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_logs)
        controls_layout.addWidget(self.refresh_button)
        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self.clear_logs)
        controls_layout.addWidget(self.clear_button)
        controls_layout.addStretch()
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        controls_layout.addWidget(self.close_button)
        layout.addLayout(controls_layout)
        self.setLayout(layout)

    def load_logs(self):
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    log_content = f.read()
                self.log_text.setText(log_content)
                self.log_text.moveCursor(QTextCursor.End)
            else:
                self.log_text.setText(f"Log file not found at: {self.log_file_path}")
        except Exception as e:
            self.log_text.setText(f"Error loading logs: {str(e)}")
            logger.error(f"Error loading log file {self.log_file_path}: {e}")

    def clear_logs(self):
        try:
            reply = QMessageBox.warning(self, "Clear Logs", 
                f"Are you sure you want to clear the log file: {self.log_file_path}? This cannot be undone.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if os.path.exists(self.log_file_path):
                    with open(self.log_file_path, 'w', encoding='utf-8') as f:
                        f.write(f"[{datetime.datetime.now().isoformat()}] Log cleared by admin.\n")
                    self.log_text.setText("Log cleared by admin.\n")
                    QMessageBox.information(self, "Logs Cleared", "Log file has been cleared.")
                else:
                    QMessageBox.warning(self, "Clear Logs", f"Log file not found: {self.log_file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Clear Logs Error", f"Error clearing logs: {str(e)}")
            logger.error(f"Error clearing log file {self.log_file_path}: {e}")