"""
Consultation panel module.
Contains the consultation request form and consultation history panel.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QLineEdit, QTextEdit,
                             QComboBox, QMessageBox, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
                             QSizePolicy, QProgressBar, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
from PyQt5.QtGui import QColor, QIcon

import logging

# Added imports
from ..controllers import ConsultationController, FacultyController
from ..config import get_config
from ..utils.theme import ConsultEaseTheme
from ..utils.icons import IconProvider, Icons

# Set up logging
logger = logging.getLogger(__name__)


class ConsultationRequestForm(QFrame):
    """
    Form to request a consultation with a faculty member.
    """
    request_submitted = pyqtSignal(object, str, str)

    def __init__(self, faculty=None, parent=None):
        super().__init__(parent)
        self.faculty = faculty
        self.faculty_options = []
        self.init_ui()

    def init_ui(self):
        """
        Initialize the consultation request form UI.
        """
        # Using ConsultEaseTheme for consistent styling
        theme = ConsultEaseTheme

        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("consultation_request_form")
        self.setStyleSheet(f"""
            QFrame#consultation_request_form {{
                background-color: {theme.BG_SECONDARY_LIGHT};
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: {theme.BORDER_RADIUS_LARGE}px;
                padding: 20px;
            }}
            QLabel {{
                font-size: {theme.FONT_SIZE_NORMAL}pt;
                color: {theme.TEXT_PRIMARY};
                font-weight: bold; /* Make labels bold */
                margin-bottom: 3px;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: {theme.BORDER_RADIUS_NORMAL}px;
                padding: 10px;
                background-color: {theme.BG_PRIMARY};
                font-size: {theme.FONT_SIZE_NORMAL}pt;
                color: {theme.TEXT_PRIMARY};
                margin-bottom: 10px; /* Add some margin below inputs */
                min-height: {theme.TOUCH_MIN_HEIGHT}px; /* Ensure touch height */
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {theme.PRIMARY_COLOR};
                background-color: {theme.BG_PRIMARY};
            }}

            # Prepare icon path for f-string
            # arrow_down_icon_path = IconProvider.get_icon(Icons.ARROW_DOWN, QSize(16,16)).name().replace("\\\\", "/") # Removed as ARROW_DOWN is not valid and icon is not used

            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left: 1px solid {theme.BORDER_COLOR};
            }}
            QComboBox::down-arrow {{
                /* image: url(...); */ /* Default system arrow will be used */
                width: 16px;
                height: 16px;
            }}
            QComboBox QAbstractItemView {{ /* Style for the dropdown list */
                border: 1px solid {theme.PRIMARY_COLOR};
                background-color: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {theme.ACCENT_COLOR};
                selection-color: {theme.TEXT_LIGHT};
                font-size: {theme.FONT_SIZE_NORMAL}pt;
                padding: 5px;
            }}
            QPushButton#submit_button {{
                background-color: {theme.SUCCESS_COLOR};
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: {theme.BORDER_RADIUS_NORMAL}px;
                font-size: {theme.FONT_SIZE_NORMAL}pt;
            }}
            QPushButton#submit_button:hover {{
                background-color: {theme.SUCCESS_COLOR_HOVER};
            }}
            QPushButton#cancel_button {{
                background-color: {theme.ERROR_COLOR};
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: {theme.BORDER_RADIUS_NORMAL}px;
                font-size: {theme.FONT_SIZE_NORMAL}pt;
            }}
            QPushButton#cancel_button:hover {{
                background-color: {theme.ERROR_COLOR_HOVER};
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins for a tighter look
        main_layout.setSpacing(12)  # Slightly reduced spacing

        # Form title
        title_label = QLabel("Request Consultation")
        title_label.setStyleSheet(
            f"font-size: {theme.FONT_SIZE_LARGE}pt; font-weight: bold; color: {theme.PRIMARY_COLOR}; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Faculty selection
        faculty_label = QLabel("Faculty:")
        # faculty_label.setFixedWidth(120) # Remove fixed width for better flow
        self.faculty_combo = QComboBox()
        self.faculty_combo.setMinimumWidth(250)  # Ensure enough width
        # self.faculty_combo.setToolTip("Select the faculty member for consultation.") # Add tooltip
        main_layout.addWidget(faculty_label)
        main_layout.addWidget(self.faculty_combo)

        # Course code input
        course_label = QLabel("Course Code (Optional):")
        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("e.g., CS101")
        # self.course_input.setToolTip("Enter the relevant course code, if any.")
        main_layout.addWidget(course_label)
        main_layout.addWidget(self.course_input)

        # Message input
        message_label = QLabel("Consultation Details:")
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Describe what you'd like to discuss...")
        self.message_input.setMinimumHeight(120)  # Adjusted height
        # self.message_input.setToolTip("Provide details about your consultation request.")
        main_layout.addWidget(message_label)
        main_layout.addWidget(self.message_input)

        # Character count with visual indicator (Simplified)
        char_count_layout = QHBoxLayout()
        self.char_count_label = QLabel("0/500")
        self.char_count_label.setAlignment(Qt.AlignRight)
        self.char_count_label.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: {theme.FONT_SIZE_SMALL}pt;")

        self.char_count_progress = QProgressBar()
        self.char_count_progress.setRange(0, 500)
        self.char_count_progress.setValue(0)
        self.char_count_progress.setTextVisible(False)
        self.char_count_progress.setFixedHeight(8)  # Slimmer progress bar
        self.char_count_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.BORDER_COLOR_LIGHT};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {theme.PRIMARY_COLOR};
                border-radius: 4px;
            }}
        """)
        char_count_layout.addWidget(self.char_count_progress)  # Progress bar first
        char_count_layout.addWidget(self.char_count_label)  # Label next to it
        main_layout.addLayout(char_count_layout)

        self.message_input.textChanged.connect(self.update_char_count)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.clicked.connect(self.cancel_request)
        # self.cancel_button.setIcon(IconProvider.get_icon(Icons.CANCEL, QSize(18,18)))

        self.submit_button = QPushButton("Submit Request")
        self.submit_button.setObjectName("submit_button")
        self.submit_button.clicked.connect(self.submit_request)
        # self.submit_button.setIcon(IconProvider.get_icon(Icons.SEND,
        # QSize(18,18))) # Assuming Icons.SEND exists

        button_layout.addStretch()  # Push buttons to the right
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.submit_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)  # Add stretch at the end to push form elements up

    def update_char_count(self):
        """
        Update the character count label and progress bar.
        """
        theme = ConsultEaseTheme
        count = len(self.message_input.toPlainText())
        self.char_count_label.setText(f"{count}/500")

        progress_color = theme.PRIMARY_COLOR
        text_color = theme.TEXT_SECONDARY

        if count > 500:
            progress_color = theme.ERROR_COLOR
            text_color = theme.ERROR_COLOR
            self.char_count_label.setText(f"<font color='{theme.ERROR_COLOR}'>{count}/500</font>")
        elif count > 450:  # Warning state
            progress_color = theme.WARNING_COLOR
            text_color = theme.WARNING_COLOR

        self.char_count_label.setStyleSheet(
            f"color: {text_color}; font-size: {theme.FONT_SIZE_SMALL}pt;")
        self.char_count_progress.setValue(min(count, 500))  # Cap progress at max
        self.char_count_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.BORDER_COLOR_LIGHT};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {progress_color};
                border-radius: 4px;
            }}
        """)

    def set_faculty(self, faculty):
        """
        Set the faculty for the consultation request.
        """
        self.faculty = faculty

        # Update the combo box
        if self.faculty and self.faculty_combo.count() > 0:
            for i in range(self.faculty_combo.count()):
                faculty_id = self.faculty_combo.itemData(i)
                if faculty_id == self.faculty.id:
                    self.faculty_combo.setCurrentIndex(i)
                    break

    def set_faculty_options(self, faculty_list):
        """
        Set the available faculty options in the dropdown.
        """
        self.faculty_options = faculty_list
        self.faculty_combo.clear()

        for faculty in faculty_list:
            self.faculty_combo.addItem(f"{faculty.name} ({faculty.department})", faculty.id)

        # If we have a selected faculty, select it in the dropdown
        if self.faculty:
            for i in range(self.faculty_combo.count()):
                faculty_id = self.faculty_combo.itemData(i)
                if faculty_id == self.faculty.id:
                    self.faculty_combo.setCurrentIndex(i)
                    break

    def get_selected_faculty(self):
        """
        Get the selected faculty from the dropdown.
        """
        if self.faculty_combo.count() == 0:
            return self.faculty

        faculty_id = self.faculty_combo.currentData()

        for faculty in self.faculty_options:
            if faculty.id == faculty_id:
                return faculty

        return None

    def submit_request(self):
        """
        Handle the submission of the consultation request.
        """
        faculty = self.get_selected_faculty()
        if not faculty:
            self.show_validation_error("Consultation Request", "Please select a faculty member.")
            return

        # Check if faculty is available
        if hasattr(faculty, 'status') and not faculty.status:
            self.show_validation_error("Consultation Request",
                                       f"Faculty {faculty.name} is currently unavailable. "
                                       "Please select an available faculty member.")
            return

        message = self.message_input.toPlainText().strip()
        if not message:
            self.show_validation_error("Consultation Request", "Please enter consultation details.")
            return

        if len(message) > 500:
            self.show_validation_error("Consultation Request",
                                       "Consultation details cannot exceed 500 characters.")
            return

        course_code = self.course_input.text().strip()
        # Optional: Validate course_code if is_valid_course_code is implemented and deemed necessary
        # if course_code and not self.is_valid_course_code(course_code):
        #     self.show_validation_error("Consultation Request", "Invalid course code format.")
        #     return

        # Emit signal with the request details
        self.request_submitted.emit(faculty, message, course_code)

    def show_validation_error(self, title, message):
        """
        Show a validation error message using the standardized notification system.

        Args:
            title (str): Error title
            message (str): Error message
        """
        try:
            # Try to use the notification manager
            from ..utils.notification import NotificationManager
            NotificationManager.show_message(
                self,
                title,
                message,
                NotificationManager.WARNING
            )
        except ImportError:
            # Fallback to basic implementation
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Validation Error")
            error_dialog.setIcon(QMessageBox.Warning)
            error_dialog.setText(f"<b>{title}</b>")
            error_dialog.setInformativeText(message)
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.setDefaultButton(QMessageBox.Ok)
            error_dialog.setStyleSheet("""
                QMessageBox {
                    background-color: #f8f9fa;
                }
                QLabel {
                    color: #212529;
                    font-size: 12pt;
                }
                QPushButton {
                    background-color: #0d3b66;
                    color: white;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #0a2f52;
                }
            """)
            error_dialog.exec_()

    def is_valid_course_code(self, course_code):
        """
        Validate course code format.

        Args:
            course_code (str): Course code to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Basic validation: 2-4 letters followed by 3-4 numbers, optionally followed by a letter
        import re
        pattern = r'^[A-Za-z]{2,4}\d{3,4}[A-Za-z]?$'

        # Allow common formats like CS101, MATH202, ENG101A
        return bool(re.match(pattern, course_code))

    def cancel_request(self):
        """
        Cancel the consultation request.
        """
        self.message_input.clear()
        self.course_input.clear()
        self.setVisible(False)


class ConsultationHistoryPanel(QFrame):
    """
    Panel to display consultation history.
    """
    consultation_selected = pyqtSignal(object)
    consultation_cancelled = pyqtSignal(int)

    def __init__(self, student=None, parent=None):
        super().__init__(parent)
        self.student = student
        self.consultation_controller = ConsultationController.instance()
        self.consultations_data = []
        self.table_update_timer = QTimer(self)
        self.table_update_timer.setSingleShot(True)
        self.table_update_timer.timeout.connect(self.update_consultation_table)
        self.init_ui()

    def init_ui(self):
        """
        Initialize the consultation history panel UI.
        """
        # Import theme system
        from ..utils.theme import ConsultEaseTheme

        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("consultation_history_panel")

        # Apply theme-based stylesheet with further improved readability
        self.setStyleSheet('''
            QFrame#consultation_history_panel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 20px;
            }
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 5px;
                background-color: white;
                alternate-background-color: #f1f3f5;
                gridline-color: #dee2e6;
                font-size: 16pt;
                color: #212529;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #e9ecef;
            }
            QHeaderView::section {
                background-color: #228be6;
                color: white;
                padding: 15px;
                border: none;
                font-size: 16pt;
                font-weight: bold;
            }
            QHeaderView::section:first {
                border-top-left-radius: 5px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 5px;
            }
            /* Improve scrollbar visibility */
            QScrollBar:vertical {
                background: #f1f3f5;
                width: 15px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #868e96;
            }
            QPushButton {
                border-radius: 5px;
                padding: 12px 20px;
                font-size: 15pt;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        ''')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("My Consultation History")
        title_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title_label)

        # Consultation table
        self.consultation_table = QTableWidget()
        self.consultation_table.setColumnCount(5)
        self.consultation_table.setHorizontalHeaderLabels(
            ["Faculty", "Course", "Status", "Date", "Actions"])

        header = self.consultation_table.horizontalHeader()
        header.setMinimumSectionSize(120)  # Set a minimum width for all columns
        header.setStretchLastSection(False)  # Don't automatically stretch the last section

        header.setSectionResizeMode(0, QHeaderView.Interactive)  # Faculty column
        self.consultation_table.setColumnWidth(0, 200)           # Faculty: Set initial width
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # Course
        self.consultation_table.setColumnWidth(1, 120)           # Course: Set initial width
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status - to fit the badge
        header.setSectionResizeMode(3, QHeaderView.Interactive)  # Date
        # Date: Set initial width for "YYYY-MM-DD HH:MM"
        self.consultation_table.setColumnWidth(3, 180)
        header.setSectionResizeMode(4, QHeaderView.Interactive)  # Actions column - Interactive
        # Actions: Set fixed width to accommodate buttons
        self.consultation_table.setColumnWidth(4, 220)

        self.consultation_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.consultation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.consultation_table.setSelectionMode(QTableWidget.SingleSelection)
        self.consultation_table.setAlternatingRowColors(True)

        main_layout.addWidget(self.consultation_table)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet('''
            QPushButton {
                background-color: #3498db;
                min-width: 120px;
            }
        ''')
        refresh_button.clicked.connect(self.refresh_consultations)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(refresh_button)

        main_layout.addLayout(button_layout)

    def set_student(self, student):
        """
        Set the student for the consultation history.
        """
        self.student = student
        self.refresh_consultations()

    def refresh_consultations(self):
        """
        Refresh the consultation history from the database with loading indicator.
        """
        if not self.student:
            return

        try:
            # Import notification utilities
            from ..utils.notification import LoadingDialog, NotificationManager

            # Define the operation to run with progress updates
            def load_consultations(progress_callback):
                # Update progress
                progress_callback(10, "Connecting to database...")

                # Get consultations for this student
                consultations = self.consultation_controller.get_consultations(
                    student_id=self.student.id)

                # Update progress
                progress_callback(80, "Processing results...")

                # Simulate a short delay for better UX
                import time
                time.sleep(0.5)

                # Update progress
                progress_callback(100, "Complete!")

                return consultations

            # Show loading dialog while fetching consultations
            self.consultations = LoadingDialog.show_loading(
                self,
                load_consultations,
                title="Refreshing Consultations",
                message="Loading your consultation history...",
                cancelable=True
            )

            # Update the table with the results
            self.update_consultation_table()

        except Exception as e:
            logger.error(f"Error refreshing consultations: {str(e)}")

            try:
                # Use notification manager if available
                from ..utils.notification import NotificationManager
                NotificationManager.show_message(
                    self,
                    "Error",
                    f"Failed to refresh consultation history: {str(e)}",
                    NotificationManager.ERROR
                )
            except ImportError:
                # Fallback to basic message box
                QMessageBox.warning(
                    self, "Error", f"Failed to refresh consultation history: {str(e)}")

    def update_consultation_table(self):
        """
        Update the consultation table with the current consultations.
        """
        # Clear the table
        self.consultation_table.setRowCount(0)

        # Add consultations to the table
        for consultation in self.consultations:
            row_position = self.consultation_table.rowCount()
            self.consultation_table.insertRow(row_position)

            # Faculty name
            faculty_item = QTableWidgetItem(consultation.faculty.name)
            self.consultation_table.setItem(row_position, 0, faculty_item)

            # Course code
            course_item = QTableWidgetItem(
                consultation.course_code if consultation.course_code else "N/A")
            self.consultation_table.setItem(row_position, 1, course_item)

            # Status with enhanced color coding using QLabel for better styling
            status_label_widget = QLabel(consultation.status.value.capitalize())
            status_label_widget.setAlignment(Qt.AlignCenter)  # Center the text

            status_value = consultation.status.value
            style_parts = [
                "font-weight: bold",
                f"font-size: {self.font().pointSize() + 1}pt",  # Match existing font sizing intent
                "padding: 5px 8px",  # Add some padding
                "border-radius: 4px"  # Add border radius
            ]

            # Define status colors with better contrast and accessibility
            # These are the same colors as before
            status_colors = {
                # Amber, Black text
                "pending": {"bg": "#ffc107", "fg": "#000000", "border": "#f08c00"},
                # Green, White text
                "accepted": {"bg": "#28a745", "fg": "#ffffff", "border": "#2b8a3e"},
                # Blue, White text
                "completed": {"bg": "#007bff", "fg": "#ffffff", "border": "#1864ab"},
                # Red, White text
                "cancelled": {"bg": "#dc3545", "fg": "#ffffff", "border": "#a61e4d"}
            }

            if status_value in status_colors:
                colors = status_colors[status_value]
                style_parts.append(f"background-color: {colors['bg']}")
                style_parts.append(f"color: {colors['fg']}")
                # Use 1px border for a less chunky look
                style_parts.append(f"border: 1px solid {colors['border']}")
            else:  # Default fallback style if status not in map
                style_parts.append("background-color: #e9ecef")  # Light gray
                style_parts.append("color: #495057")  # Dark gray text
                style_parts.append("border: 1px solid #ced4da")

            status_label_widget.setStyleSheet("; ".join(style_parts) + ";")
            self.consultation_table.setCellWidget(row_position, 2, status_label_widget)

            # Date
            date_str = consultation.requested_at.strftime("%Y-%m-%d %H:%M")
            date_item = QTableWidgetItem(date_str)
            self.consultation_table.setItem(row_position, 3, date_item)

            # Actions
            actions_cell = QWidget()
            actions_layout = QHBoxLayout(actions_cell)
            actions_layout.setContentsMargins(2, 2, 2, 2)

            # View details button
            view_button = QPushButton("View")
            view_button.setStyleSheet("background-color: #3498db; color: white;")
            # Use a better lambda that ignores the checked parameter
            view_button.clicked.connect(lambda _, c=consultation: self.view_consultation_details(c))
            actions_layout.addWidget(view_button)

            # Cancel button (only for pending consultations)
            if consultation.status.value == "pending":
                cancel_button = QPushButton("Cancel")
                cancel_button.setStyleSheet("background-color: #e74c3c; color: white;")
                # Use a better lambda that ignores the checked parameter
                cancel_button.clicked.connect(lambda _, c=consultation: self.cancel_consultation(c))
                actions_layout.addWidget(cancel_button)

            self.consultation_table.setCellWidget(row_position, 4, actions_cell)

    def view_consultation_details(self, consultation):
        """
        Show consultation details in a dialog.
        """
        dialog = ConsultationDetailsDialog(consultation, self)
        dialog.exec_()

    def cancel_consultation(self, consultation):
        """
        Cancel a pending consultation with improved confirmation dialog.
        """
        try:
            # Try to use the notification manager for confirmation
            from ..utils.notification import NotificationManager

            # Show confirmation dialog
            if NotificationManager.show_confirmation(
                self,
                "Cancel Consultation",
                f"Are you sure you want to cancel your consultation request with {consultation.faculty.name}?",
                "Yes, Cancel",
                "No, Keep It"
            ):
                # Emit signal to cancel the consultation
                self.consultation_cancelled.emit(consultation.id)

        except ImportError:
            # Fallback to basic confirmation dialog
            reply = QMessageBox.question(
                self,
                "Cancel Consultation",
                f"Are you sure you want to cancel your consultation request with {consultation.faculty.name}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Emit signal to cancel the consultation
                self.consultation_cancelled.emit(consultation.id)


class ConsultationDetailsDialog(QDialog):
    """
    Dialog to display consultation details.
    """

    def __init__(self, consultation, parent=None):
        super().__init__(parent)
        self.consultation = consultation
        self.init_ui()

    def init_ui(self):
        """
        Initialize the dialog UI.
        """
        # Import theme system
        from ..utils.theme import ConsultEaseTheme

        self.setWindowTitle("Consultation Details")
        self.setMinimumWidth(650)
        self.setMinimumHeight(550)
        self.setObjectName("consultation_details_dialog")

        # Apply theme-based stylesheet with improved readability
        self.setStyleSheet('''
            QDialog#consultation_details_dialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 15pt;
                color: #212529;
            }
            QLabel[heading="true"] {
                font-size: 20pt;
                font-weight: bold;
                color: #228be6;
                margin-bottom: 10px;
            }
            QFrame {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: white;
                padding: 20px;
                margin: 5px 0;
            }
            QPushButton {
                border-radius: 5px;
                padding: 12px 20px;
                font-size: 15pt;
                font-weight: bold;
                color: white;
                background-color: #228be6;
            }
            QPushButton:hover {
                background-color: #1971c2;
            }
        ''')

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Consultation Details")
        title_label.setProperty("heading", "true")
        layout.addWidget(title_label)

        # Details frame
        details_frame = QFrame()
        details_layout = QFormLayout(details_frame)
        details_layout.setSpacing(10)

        # Faculty
        faculty_label = QLabel("Faculty:")
        faculty_value = QLabel(self.consultation.faculty.name)
        faculty_value.setStyleSheet("font-weight: bold;")
        details_layout.addRow(faculty_label, faculty_value)

        # Department
        dept_label = QLabel("Department:")
        dept_value = QLabel(self.consultation.faculty.department)
        details_layout.addRow(dept_label, dept_value)

        # Course
        course_label = QLabel("Course:")
        course_value = QLabel(
            self.consultation.course_code if self.consultation.course_code else "N/A")
        details_layout.addRow(course_label, course_value)

        # Status with enhanced visual styling
        status_label = QLabel("Status:")
        status_value = QLabel(self.consultation.status.value.capitalize())

        # Define status colors with better contrast and accessibility
        status_styles = {
            "pending": {
                "color": "#000000",                # Black text
                "background": "#ffd43b",           # Bright yellow background
                "border": "2px solid #f08c00",     # Orange border
                "padding": "8px 12px",
                "border-radius": "6px"
            },
            "accepted": {
                "color": "#ffffff",                # White text
                "background": "#40c057",           # Bright green background
                "border": "2px solid #2b8a3e",     # Dark green border
                "padding": "8px 12px",
                "border-radius": "6px"
            },
            "completed": {
                "color": "#ffffff",                # White text
                "background": "#339af0",           # Bright blue background
                "border": "2px solid #1864ab",     # Dark blue border
                "padding": "8px 12px",
                "border-radius": "6px"
            },
            "cancelled": {
                "color": "#ffffff",                # White text
                "background": "#fa5252",           # Bright red background
                "border": "2px solid #c92a2a",     # Dark red border
                "padding": "8px 12px",
                "border-radius": "6px"
            }
        }

        # Apply the appropriate style
        status_value.setStyleSheet(f"""
            font-weight: bold;
            font-size: 16pt;
            color: {status_styles.get(self.consultation.status.value, {}).get("color", "#212529")};
            background-color: {status_styles.get(self.consultation.status.value, {}).get("background", "#e9ecef")};
            border: {status_styles.get(self.consultation.status.value, {}).get("border", "2px solid #adb5bd")};
            padding: {status_styles.get(self.consultation.status.value, {}).get("padding", "8px 12px")};
            border-radius: {status_styles.get(self.consultation.status.value, {}).get("border-radius", "6px")};
        """)
        details_layout.addRow(status_label, status_value)

        # Requested date
        requested_label = QLabel("Requested:")
        requested_value = QLabel(self.consultation.requested_at.strftime("%Y-%m-%d %H:%M"))
        details_layout.addRow(requested_label, requested_value)

        # Accepted date (if applicable)
        if self.consultation.accepted_at:
            accepted_label = QLabel("Accepted:")
            accepted_value = QLabel(self.consultation.accepted_at.strftime("%Y-%m-%d %H:%M"))
            details_layout.addRow(accepted_label, accepted_value)

        # Completed date (if applicable)
        if self.consultation.completed_at:
            completed_label = QLabel("Completed:")
            completed_value = QLabel(self.consultation.completed_at.strftime("%Y-%m-%d %H:%M"))
            details_layout.addRow(completed_label, completed_value)

        layout.addWidget(details_frame)

        # Message
        message_label = QLabel("Consultation Details:")
        message_label.setProperty("heading", "true")
        layout.addWidget(message_label)

        message_frame = QFrame()
        message_layout = QVBoxLayout(message_frame)

        message_text = QLabel(self.consultation.request_message)
        message_text.setWordWrap(True)
        message_layout.addWidget(message_text)

        layout.addWidget(message_frame)

        # Close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)


class ConsultationPanel(QTabWidget):
    """
    Main consultation panel with request form and history tabs.
    Improved with better transitions and user feedback.
    """
    consultation_requested = pyqtSignal(object, str, str)
    consultation_cancelled = pyqtSignal(int)

    def __init__(self, student=None, parent=None):
        super().__init__(parent)
        self.student = student
        self.consultation_controller = ConsultationController.instance()
        self.faculty_controller = FacultyController.instance()
        self.config = get_config()
        self.init_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_refresh_history)
        # Increased refresh interval for history, less frequent updates
        self.refresh_timer.start(
            self.config.get(
                'ui.history_refresh_interval_ms',
                120000))  # Default 2 mins

        self.currentChanged.connect(self.on_tab_changed)

    def init_ui(self):
        """
        Initialize the consultation panel UI with improved styling and responsiveness.
        """
        theme = ConsultEaseTheme
        self.setObjectName("consultation_panel_main")  # For specific styling if needed

        # Tab Bar styling for a more modern look
        self.setStyleSheet(f"""
            QTabWidget#consultation_panel_main::pane {{
                border: 1px solid {theme.BORDER_COLOR};
                border-top: none; /* Pane border only on sides/bottom */
                background-color: {theme.BG_SECONDARY_LIGHT};
                border-bottom-left-radius: {theme.BORDER_RADIUS_LARGE}px;
                border-bottom-right-radius: {theme.BORDER_RADIUS_LARGE}px;
                padding: 10px;
            }}
            QTabBar::tab {{
                background-color: {theme.BG_PRIMARY_MUTED};
                color: {theme.TEXT_SECONDARY};
                border: 1px solid {theme.BORDER_COLOR};
                border-bottom: none; /* No bottom border for inactive tabs */
                border-top-left-radius: {theme.BORDER_RADIUS_NORMAL}px;
                border-top-right-radius: {theme.BORDER_RADIUS_NORMAL}px;
                padding: 10px 25px; /* Increased padding */
                margin-right: 2px;
                font-size: {theme.FONT_SIZE_NORMAL}pt;
                font-weight: bold;
                min-width: 180px; /* Ensure tabs have enough width */
            }}
            QTabBar::tab:selected {{
                background-color: {theme.BG_SECONDARY_LIGHT}; /* Match pane background */
                color: {theme.PRIMARY_COLOR};
                border-bottom: 2px solid {theme.BG_SECONDARY_LIGHT}; /* Creates illusion of tab merging with pane */
                margin-bottom: -1px; /* Overlap with pane top border */
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {theme.BG_PRIMARY_MUTED};
                color: {theme.PRIMARY_COLOR};
            }}
            QTabWidget::tab-bar {{
                alignment: left; /* Align tabs to the left */
                left: 5px; /* Small offset from edge */
            }}
        """)

        self.request_form = ConsultationRequestForm()
        self.request_form.request_submitted.connect(self.handle_consultation_request)
        self.addTab(self.request_form, "New Request")  # Shorter tab title
        # Set tab icon (ensure Icons.EDIT or a suitable icon exists)
        self.setTabIcon(0, IconProvider.get_icon(Icons.EDIT, QSize(20, 20)))

        self.history_panel = ConsultationHistoryPanel(self.student)
        self.history_panel.consultation_cancelled.connect(self.handle_consultation_cancel)
        self.addTab(self.history_panel, "History")  # Shorter tab title
        # Set tab icon (ensure Icons.HISTORY or a suitable icon exists)
        self.setTabIcon(1, IconProvider.get_icon(Icons.REPORTS, QSize(20, 20)))

        # min_width = min(900, max(500, int(QApplication.desktop().screenGeometry().width() * 0.4)))
        # min_height = min(700, max(400, int(QApplication.desktop().screenGeometry().height() * 0.6)))
        # self.setMinimumSize(min_width, min_height) # Handled by splitter sizes mostly
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_student(self, student):
        """
        Set the student for the consultation panel.
        """
        self.student = student
        self.history_panel.set_student(student)

        # Update window title with student name
        if student and hasattr(self.parent(), 'setWindowTitle'):
            self.parent().setWindowTitle(f"ConsultEase - {student.name}")

    def set_faculty(self, faculty):
        """
        Set the faculty for the consultation request.
        """
        self.request_form.set_faculty(faculty)

        # Animate transition to request form tab
        self.animate_tab_change(0)

    def set_faculty_options(self, faculty_list):
        """
        Set the available faculty options in the dropdown.
        """
        self.request_form.set_faculty_options(faculty_list)

        # Update status message if no faculty available
        if not faculty_list:
            QMessageBox.information(
                self,
                "No Faculty Available",
                "There are no faculty members available at this time. Please try again later."
            )

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request submission with improved feedback.
        """
        try:
            # Try to import notification manager
            try:
                from ..utils.notification import NotificationManager, LoadingDialog
                use_notification_manager = True
            except ImportError:
                use_notification_manager = False

            # Get ConsultationController instance
            consultation_controller = ConsultationController.instance()

            # Define the operation to run with progress updates
            def submit_request(progress_callback=None):
                if progress_callback:
                    progress_callback(20, "Submitting request...")

                # Directly call the controller to create the consultation
                created_consultation = consultation_controller.create_consultation(
                    student_id=self.student.id,
                    faculty_id=faculty.id,
                    request_message=message,
                    course_code=course_code
                )

                if not created_consultation:
                    # The controller already logs errors. We might want to raise an exception here
                    # to be caught by the outer try/except for consistent error messaging.
                    raise Exception("Failed to create consultation. Controller returned None.")

                if progress_callback:
                    progress_callback(60, "Processing submission...")

                # Clear form fields
                self.request_form.message_input.clear()
                self.request_form.course_input.clear()

                if progress_callback:
                    progress_callback(80, "Refreshing history...")

                # Refresh history
                self.history_panel.refresh_consultations()

                if progress_callback:
                    progress_callback(100, "Complete!")

                # Emit the original signal for DashboardWindow or other listeners,
                # now with the successfully created consultation object.
                # This signal becomes more of a "consultation_successfully_created_and_submitted"
                self.consultation_requested.emit(created_consultation, message, course_code)

                return True  # Indicate success for LoadingDialog

            # Use loading dialog if available
            if use_notification_manager:
                # Show loading dialog while submitting
                LoadingDialog.show_loading(
                    self,
                    submit_request,
                    title="Submitting Request",
                    message="Submitting your consultation request...",
                    cancelable=False  # Should not be cancelable once submission starts
                )

                # Show success message (this might be redundant if DashboardWindow also shows one)
                # Consider if NotificationManager should be used by the primary handler (panel)
                # or the secondary listener (dashboard). For now, keeping it here.
                NotificationManager.show_message(
                    self,
                    "Request Submitted",
                    f"Your consultation request with {faculty.name} has been submitted successfully.",
                    NotificationManager.SUCCESS
                )
            else:
                # Fallback to basic implementation (without loading dialog)
                submit_request()  # This will raise Exception on failure

                # Show success message
                QMessageBox.information(
                    self,
                    "Consultation Request Submitted",
                    f"Your consultation request with {faculty.name} has been submitted successfully."
                )

            # Animate transition to history tab
            self.animate_tab_change(1)

        except Exception as e:
            logger.error(f"Error submitting consultation request in ConsultationPanel: {str(e)}")

            # Show error message
            error_message_detail = str(e)
            if "Failed to create consultation" in error_message_detail:
                error_message_detail = "The system could not create your consultation request. Please try again."

            try:
                from ..utils.notification import NotificationManager
                NotificationManager.show_message(
                    self,
                    "Submission Error",
                    f"Failed to submit consultation request: {error_message_detail}",
                    NotificationManager.ERROR
                )
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to submit consultation request: {error_message_detail}"
                )

    def handle_consultation_cancel(self, consultation_id):
        """
        Handle consultation cancellation with improved feedback.
        """
        try:
            # Try to import notification manager
            try:
                from ..utils.notification import NotificationManager, LoadingDialog
                use_notification_manager = True
            except ImportError:
                use_notification_manager = False

            # Get ConsultationController instance
            consultation_controller = ConsultationController.instance()

            # Define the operation to run with progress updates
            def perform_cancel_consultation(progress_callback=None):
                if progress_callback:
                    progress_callback(30, "Cancelling request...")

                # Directly call the controller to cancel the consultation
                cancelled_consultation = consultation_controller.cancel_consultation(
                    consultation_id)

                if not cancelled_consultation:
                    raise Exception(
                        "Failed to cancel consultation. Controller returned None or error.")

                if progress_callback:
                    progress_callback(70, "Updating records...")

                # Refresh history
                self.history_panel.refresh_consultations()

                if progress_callback:
                    progress_callback(100, "Complete!")

                # Emit the original signal, now with the (cancelled) consultation object
                # if needed by other listeners, though DashboardWindow might not need it anymore
                # for its primary function of calling the controller.
                # Or emit `cancelled_consultation` if more useful
                self.consultation_cancelled.emit(consultation_id)

                return True  # Indicate success for LoadingDialog

            # Use loading dialog if available
            if use_notification_manager:
                # Show confirmation dialog first
                if NotificationManager.show_confirmation(
                    self,
                    "Cancel Consultation",
                    "Are you sure you want to cancel this consultation request?",
                    "Yes, Cancel",
                    "No, Keep It"
                ):
                    # Show loading dialog while cancelling
                    LoadingDialog.show_loading(
                        self,
                        perform_cancel_consultation,
                        title="Cancelling Request",
                        message="Cancelling your consultation request...",
                        cancelable=False  # Cancellation process itself should not be cancelable midway
                    )

                    # Show success message
                    NotificationManager.show_message(
                        self,
                        "Request Cancelled",
                        "Your consultation request has been cancelled successfully.",
                        NotificationManager.SUCCESS
                    )
            else:
                # Fallback to basic implementation
                reply = QMessageBox.question(
                    self,
                    "Cancel Consultation",
                    "Are you sure you want to cancel this consultation request?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # Cancel the consultation (this will raise Exception on failure)
                    perform_cancel_consultation()

                    # Show success message
                    QMessageBox.information(
                        self,
                        "Consultation Cancelled",
                        "Your consultation request has been cancelled successfully."
                    )

        except Exception as e:
            logger.error(f"Error cancelling consultation in ConsultationPanel: {str(e)}")

            # Show error message
            error_message_detail = str(e)
            if "Failed to cancel consultation" in error_message_detail:
                error_message_detail = "The system could not cancel your consultation request. Please try again."

            try:
                from ..utils.notification import NotificationManager
                NotificationManager.show_message(
                    self,
                    "Cancellation Error",
                    f"Failed to cancel consultation: {error_message_detail}",
                    NotificationManager.ERROR
                )
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to cancel consultation: {error_message_detail}"
                )

    def animate_tab_change(self, tab_index):
        """
        Animate the transition to a different tab with enhanced visual effects.

        Args:
            tab_index (int): The index of the tab to switch to
        """
        # Import animation classes if available
        try:
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup

            # Create a property animation for the tab widget
            pos_animation = QPropertyAnimation(self, b"pos")
            pos_animation.setDuration(300)  # 300ms animation
            pos_animation.setStartValue(self.pos() + QPoint(10, 0))  # Slight offset
            pos_animation.setEndValue(self.pos())  # Original position
            pos_animation.setEasingCurve(QEasingCurve.OutCubic)  # Smooth curve

            # Create a parallel animation group
            animation_group = QParallelAnimationGroup()
            animation_group.addAnimation(pos_animation)

            # Start the animation
            animation_group.start()

            # Set the current tab
            self.setCurrentIndex(tab_index)

        except ImportError:
            # If animation classes are not available, use simpler animation
            # Set the current tab
            self.setCurrentIndex(tab_index)

            # Flash the tab briefly to draw attention
            try:
                current_style = self.tabBar().tabTextColor(tab_index)

                # Create a timer to reset the color after a brief flash
                def reset_color():
                    self.tabBar().setTabTextColor(tab_index, current_style)

                # Set highlight color
                self.tabBar().setTabTextColor(tab_index, QColor("#228be6"))

                # Reset after a short delay
                QTimer.singleShot(500, reset_color)
            except BaseException:
                # If even this fails, just change the tab without animation
                pass

    def on_tab_changed(self, index):
        """
        Handle tab change events.

        Args:
            index (int): The index of the newly selected tab
        """
        # Refresh history when switching to history tab
        if index == 1:  # History tab
            self.history_panel.refresh_consultations()

    def auto_refresh_history(self):
        """
        Automatically refresh the history panel periodically.
        """
        # Only refresh if the history tab is visible
        if self.currentIndex() == 1:
            self.history_panel.refresh_consultations()

    def refresh_history(self):
        """
        Refresh the consultation history.
        """
        self.history_panel.refresh_consultations()
