from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QGridLayout, QScrollArea, QFrame,
                               QLineEdit, QTextEdit, QComboBox, QMessageBox,
                               QSplitter, QApplication, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QPixmap

import os
import logging
import time # Moved import time here
from .base_window import BaseWindow
from .consultation_panel import ConsultationPanel
from ..controllers import FacultyController, ConsultationController
from ..utils.icons import IconProvider, Icons
from ..models.student import Student
from ..models.consultation import Consultation
from ..config import get_config
from ..services import get_rfid_service, get_mqtt_service

# Set up logging
logger = logging.getLogger(__name__)

class FacultyCard(QFrame):
    """
    Widget to display faculty information and status.
    """
    consultation_requested = pyqtSignal(object)

    def __init__(self, faculty, parent=None):
        super().__init__(parent)
        self.faculty = faculty
        self.init_ui()

    def init_ui(self):
        """
        Initialize the faculty card UI.
        """
        self.setFrameShape(QFrame.StyledPanel)

        # Set fixed width and minimum height for consistent card size
        # Reduced width as per user preference
        self.setFixedWidth(240)
        self.setMinimumHeight(160)

        # Set size policy to prevent stretching
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        # Add drop shadow effect for card-like appearance
        self.setGraphicsEffect(self._create_shadow_effect())

        # Set styling based on faculty status
        self.update_style()

        # Main layout with improved margins for card-like appearance
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins
        main_layout.setSpacing(6)  # Reduced spacing
        main_layout.setAlignment(Qt.AlignCenter)

        # Faculty info layout (image + text)
        info_layout = QHBoxLayout()
        info_layout.setAlignment(Qt.AlignCenter)

        # Faculty image - further reduced size with improved styling
        self.image_label = QLabel()
        self.image_label.setFixedSize(50, 50)  # Smaller image
        self.image_label.setStyleSheet("""
            border: 1px solid #ddd;
            border-radius: 25px;  # Adjusted radius to match size
            background-color: white;
            padding: 2px;
        """)
        self.image_label.setScaledContents(True)
        self._load_faculty_image() # Helper method to load image

        info_layout.addWidget(self.image_label)

        # Faculty text info
        text_layout = QVBoxLayout()
        text_layout.setAlignment(Qt.AlignLeft)
        text_layout.setSpacing(4)  # Increased spacing between name and department
        text_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to maximize text space

        # Faculty name - improved styling for better readability with no border
        self.name_label = QLabel(self.faculty.name)
        self.name_label.setStyleSheet("""
            font-size: 15pt;
            font-weight: bold;
            padding: 0;
            margin: 0;
            border: none;
        """)
        self.name_label.setAlignment(Qt.AlignLeft)
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumWidth(180)  # Ensure enough width for text
        self.name_label.setMaximumWidth(200)  # Limit maximum width
        text_layout.addWidget(self.name_label)

        # Department - improved styling with no border
        self.dept_label = QLabel(self.faculty.department)
        self.dept_label.setStyleSheet("""
            font-size: 11pt;
            color: #666;
            padding: 0;
            margin: 0;
            border: none;
        """)
        self.dept_label.setAlignment(Qt.AlignLeft)
        self.dept_label.setWordWrap(True)
        self.dept_label.setMinimumWidth(180)  # Ensure enough width for text
        self.dept_label.setMaximumWidth(200)  # Limit maximum width
        text_layout.addWidget(self.dept_label)

        info_layout.addLayout(text_layout)
        main_layout.addLayout(info_layout)

        # Add a horizontal line separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #ddd; max-height: 1px;")
        main_layout.addWidget(separator)

        # Status indicator - improved layout and styling
        status_layout = QHBoxLayout()
        status_layout.setAlignment(Qt.AlignLeft)
        status_layout.setSpacing(4)

        self.status_icon_label = QLabel("●")
        self.status_text_label = QLabel() # Initialize status_text_label here
        self._update_status_widgets() # Helper method

        status_layout.addWidget(self.status_icon_label)
        status_layout.addWidget(self.status_text_label)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)

        # Request consultation button - more compact with improved styling
        self.request_button = QPushButton("Request Consultation")
        self.request_button.setEnabled(self.faculty.status)
        self.request_button.setStyleSheet("""
            QPushButton {
                font-size: 10pt;
                padding: 6px;
                border-radius: 4px;
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #B0BEC5;
                color: #ECEFF1;
            }
        """)
        self.request_button.clicked.connect(self.request_consultation)
        main_layout.addWidget(self.request_button)

    def _create_shadow_effect(self):
        """
        Create a shadow effect for the card.
        """
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        from PyQt5.QtGui import QColor

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 2)
        return shadow

    def update_style(self):
        """
        Update the card styling based on faculty status.
        """
        if self.faculty.status:
            self.setStyleSheet('''
                QFrame {
                    background-color: #e8f5e9;
                    border: 1px solid #4caf50;
                    border-radius: 8px;
                    margin: 5px;  /* Added margin for better visual separation */
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);  /* Subtle shadow */
                }
            ''')
        else:
            self.setStyleSheet('''
                QFrame {
                    background-color: #ffebee;
                    border: 1px solid #f44336;
                    border-radius: 8px;
                    margin: 5px;  /* Added margin for better visual separation */
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);  /* Subtle shadow */
                }
            ''')

    def _load_faculty_image(self):
        pixmap_loaded = False
        if hasattr(self.faculty, 'get_image_path') and self.faculty.image_path:
            try:
                image_path = self.faculty.get_image_path()
                if image_path and os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        self.image_label.setPixmap(pixmap)
                        pixmap_loaded = True
                    else:
                        logger.warning(f"Could not load image for faculty {self.faculty.name}: {image_path} (pixmap isNull)")
                else:
                    logger.warning(f"Image path not found or is invalid for faculty {self.faculty.name}: {image_path}")
            except Exception as e:
                logger.error(f"Error loading faculty image for {self.faculty.name} from {getattr(self.faculty, 'image_path', 'N/A')}: {str(e)}")
        
        if not pixmap_loaded:
            # Attempt to load a default user icon
            try:
                # Assuming IconProvider and Icons are imported, and Icons.USER exists
                default_icon = IconProvider.get_icon(Icons.USER, QSize(50, 50))
                if default_icon and not default_icon.isNull():
                    self.image_label.setPixmap(default_icon.pixmap(QSize(50,50)))
                else:
                    # Fallback if IconProvider fails or returns null icon
                    logger.warning(f"Default user icon (Icons.USER) could not be loaded. Using basic placeholder for {self.faculty.name}.")
                    fallback_pixmap = QPixmap(QSize(50, 50))
                    fallback_pixmap.fill(QColor("#e0e0e0")) # Light gray background
                    self.image_label.setPixmap(fallback_pixmap)
            except Exception as e:
                logger.error(f"Exception while trying to load default user icon for {self.faculty.name}: {str(e)}")
                # Last resort basic placeholder
                fallback_pixmap = QPixmap(QSize(50, 50))
                fallback_pixmap.fill(QColor("#e0e0e0")) # Light gray background
                self.image_label.setPixmap(fallback_pixmap)

    def _update_status_widgets(self):
        if self.faculty.status:
            self.status_icon_label.setStyleSheet("font-size: 12pt; color: #4caf50; border: none;")
            self.status_text_label.setText("Available") # Update existing label
            self.status_text_label.setStyleSheet("font-size: 11pt; color: #4caf50; border: none;")
            self.request_button.setEnabled(self.faculty.status)
        else:
            self.status_icon_label.setStyleSheet("font-size: 12pt; color: #f44336; border: none;")
            self.status_text_label.setText("Unavailable") # Update existing label
            self.status_text_label.setStyleSheet("font-size: 11pt; color: #f44336; border: none;")
            self.request_button.setEnabled(self.faculty.status)

    def update_faculty(self, faculty):
        """
        Update the faculty information efficiently.
        """
        self.faculty = faculty
        self.update_style() # Updates card background/border

        # Update specific widgets
        self.name_label.setText(self.faculty.name)
        self.dept_label.setText(self.faculty.department)
        self._load_faculty_image() # Reload image if it changed
        self._update_status_widgets() # Updates status icon, text, and button state

    def request_consultation(self):
        """
        Emit signal to request a consultation with this faculty.
        """
        self.consultation_requested.emit(self.faculty)

class DashboardWindow(BaseWindow):
    """
    Main dashboard window with faculty availability display and consultation request functionality.
    """
    # Signal to handle consultation request
    consultation_requested = pyqtSignal(object, str, str)

    def __init__(self, student=None, parent=None):
        super().__init__(parent)
        self.student = student

        # Get controller instances (now singletons)
        self.faculty_controller = FacultyController.instance()
        self.consultation_controller = ConsultationController.instance()

        # UI elements for faculty grid feedback
        self.loading_label = QLabel("Loading faculty data...")
        self.loading_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; padding: 20px; background-color: transparent;")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setVisible(False)

        self.no_results_label = QLabel("No faculty members found matching your criteria.")
        self.no_results_label.setStyleSheet("font-size: 14pt; color: #7f8c8d; padding: 20px; background-color: #f5f5f5; border-radius: 10px;")
        self.no_results_label.setAlignment(Qt.AlignCenter)
        self.no_results_label.setVisible(False)
        
        # Store faculty cards to manage them directly
        self._faculty_cards_widgets = []

        # Initialize UI components
        self.init_ui()

        # Set up auto-refresh timer for faculty status with further reduced frequency
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_faculty_status)
        self.refresh_timer.start(120000)  # Refresh every 120 seconds (2 minutes) to reduce loading indicators

        # Track consecutive no-change refreshes to further reduce refresh frequency when idle
        self._consecutive_no_changes = 0
        self._max_refresh_interval = 300000  # 5 minutes maximum interval

        # Log student info for debugging
        if student:
            logger.info(f"Dashboard initialized with student: ID={student.id}, Name={student.name}, RFID={student.rfid_uid}")
        else:
            logger.warning("Dashboard initialized without student information")

    def init_ui(self):
        """
        Initialize the dashboard UI.
        """
        # Main layout
        main_layout = QVBoxLayout(self)

        # Header (Logo and Title)
        header_layout = QHBoxLayout()
        self.logo_label = QLabel()
        # Correct way to get icon path or use a fallback
        icon_candidate = IconProvider.get_icon("logo") # Try to get 'logo.png', 'logo.svg', etc.
        icon_path = icon_candidate.name() # .name() can give a path for QPixmap

        if icon_path and os.path.exists(icon_path): # Check if path is valid and file exists
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self.logo_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logger.warning("Failed to load logo from path: {icon_path}, using fallback.")
                self._set_fallback_logo()
        else:
            logger.warning(f"Logo icon 'logo' not found by IconProvider or path '{icon_path}' is invalid. Using fallback.")
            self._set_fallback_logo()
            
        header_layout.addWidget(self.logo_label)

        title_label = QLabel("ConsultEase - Faculty Dashboard")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #0d3b66;")
        header_layout.addWidget(title_label, 1) # Add stretch factor to push logo to left

        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Search and Filter
        search_filter_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search faculty by name or department...")
        self.search_bar.textChanged.connect(self.filter_faculty)
        search_filter_layout.addWidget(self.search_bar)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All")
        self.filter_combo.addItem("Available")
        self.filter_combo.addItem("Busy")
        self.filter_combo.addItem("Unavailable")
        self.filter_combo.currentTextChanged.connect(self.filter_faculty)
        search_filter_layout.addWidget(self.filter_combo)
        main_layout.addLayout(search_filter_layout)

        # Faculty Cards Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")

        self.faculty_cards_widget = QWidget()
        self.faculty_grid_layout = QGridLayout(self.faculty_cards_widget)
        # Spacing between cards
        self.faculty_grid_layout.setSpacing(20)
        # Align cards to top-left
        self.faculty_grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.faculty_cards_widget)
        main_layout.addWidget(self.scroll_area)

        # Manual RFID Entry (Moved to bottom for better layout) - Temporarily commented out
        # manual_entry_layout = QHBoxLayout()
        # self.manual_rfid_input = QLineEdit()
        # self.manual_rfid_input.setPlaceholderText("Enter Student RFID/ID Manually")
        # self.manual_rfid_button = QPushButton("Submit ID")
        # self.manual_rfid_button.setIcon(IconProvider.get_icon("input"))
        # self.manual_rfid_button.setStyleSheet(
        #     "QPushButton { background-color: #0d3b66; color: white; padding: 10px; border-radius: 5px; }"
        #     "QPushButton:hover { background-color: #1a5f99; }"
        # )
        # self.manual_rfid_button.clicked.connect(self._handle_manual_rfid_input) # This line caused the AttributeError
        # manual_entry_layout.addWidget(self.manual_rfid_input)
        # manual_entry_layout.addWidget(self.manual_rfid_button)
        # main_layout.addLayout(manual_entry_layout)

        # Logout Button
        self.logout_button = QPushButton("Logout")
        self.logout_button.setIcon(IconProvider.get_button_icon(Icons.LOGOUT))
        self.logout_button.setStyleSheet(
            "QPushButton { background-color: #e63946; color: white; padding: 10px; border-radius: 5px; font-size: 16px; }"
            "QPushButton:hover { background-color: #c9303f; }"
        )

        # Consultation panel with request form and history
        self.consultation_panel = ConsultationPanel(self.student)
        self.consultation_panel.consultation_requested.connect(self.handle_consultation_request)
        self.consultation_panel.consultation_cancelled.connect(self.handle_consultation_cancel)

        # Add widgets to splitter
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.addWidget(self.scroll_area)
        content_splitter.addWidget(self.consultation_panel)

        # Set splitter sizes proportionally to screen width
        screen_size = QApplication.desktop().screenGeometry()
        screen_width = screen_size.width()
        content_splitter.setSizes([int(screen_width * 0.6), int(screen_width * 0.4)])

        # Save splitter state when it changes
        content_splitter.splitterMoved.connect(self.save_splitter_state)

        # Store the splitter for later reference
        self.content_splitter = content_splitter

        # Try to restore previous splitter state
        self.restore_splitter_state()

        # Add the splitter to the main layout
        main_layout.addWidget(content_splitter)

        # Schedule a scroll to top after the UI is fully loaded
        QTimer.singleShot(100, self._scroll_faculty_to_top)

        # Set the main layout to a widget and make it the central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def populate_faculty_grid(self, faculties):
        """
        Populate the faculty grid with faculty cards.
        Optimized for performance with batch processing and reduced UI updates.

        Args:
            faculties (list): List of faculty objects
        """
        # Temporarily disable updates to reduce flickering and improve performance
        self.setUpdatesEnabled(False)

        try:
            # Clear existing faculty cards from the grid and delete them
            for card_widget in self._faculty_cards_widgets:
                self.faculty_grid_layout.removeWidget(card_widget)
                card_widget.deleteLater()
            self._faculty_cards_widgets.clear()

            # Remove feedback labels if they are present
            # Check if widgets are part of the layout before removing
            if self.loading_label.parent() is self.faculty_grid_layout.parentWidget(): # Or check layout directly
                 self.faculty_grid_layout.removeWidget(self.loading_label)
            self.loading_label.setVisible(False)

            if self.no_results_label.parent() is self.faculty_grid_layout.parentWidget():
                 self.faculty_grid_layout.removeWidget(self.no_results_label)
            self.no_results_label.setVisible(False)

            # Calculate optimal number of columns based on screen width
            screen_width = QApplication.desktop().screenGeometry().width()
            card_width = 240
            spacing = 15
            grid_container_width = self.faculty_grid_layout.parentWidget().width()
            if grid_container_width <= 0:
                grid_container_width = int(screen_width * 0.6)
            grid_container_width -= 30
            max_cols = max(1, int(grid_container_width / (card_width + spacing)))
            if screen_width < 800:
                max_cols = 1

            if not faculties:
                # If no faculty found, show the no_results_label
                if self.no_results_label.parentWidget() is None:
                    self.faculty_grid_layout.addWidget(self.no_results_label, 0, 0, 1, max_cols)
                self.no_results_label.setVisible(True)
            else:
                # Add faculty cards to grid
                row, col = 0, 0
                for faculty in faculties:
                    container = QWidget()
                    container.setStyleSheet("background-color: transparent;")
                    container_layout = QHBoxLayout(container)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                    container_layout.setAlignment(Qt.AlignCenter)
                    card = FacultyCard(faculty)
                    card.consultation_requested.connect(self.show_consultation_form)
                    container_layout.addWidget(card)
                    self.faculty_grid_layout.addWidget(container, row, col)
                    self._faculty_cards_widgets.append(container) # Store the container
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
        finally:
            self.setUpdatesEnabled(True)

    def filter_faculty(self):
        """
        Filter faculty grid based on search text and filter selection.
        Uses a debounce mechanism to prevent excessive updates.
        """
        # Cancel any pending filter operation
        if hasattr(self, '_filter_timer') and self._filter_timer.isActive():
            self._filter_timer.stop()

        # Create a new timer for debouncing
        if not hasattr(self, '_filter_timer'):
            self._filter_timer = QTimer(self)
            self._filter_timer.setSingleShot(True)
            self._filter_timer.timeout.connect(self._perform_filter)

        # Start the timer - will trigger _perform_filter after 300ms
        self._filter_timer.start(300)

    def _perform_filter(self):
        """
        Actually perform the faculty filtering after debounce delay.
        """
        try:
            # Get search text and filter value
            search_text = self.search_bar.text().strip()
            filter_available = self.filter_combo.currentData()

            # Get filtered faculty list
            faculties = self.faculty_controller.get_all_faculty(
                filter_available=filter_available,
                search_term=search_text
            )

            # Update the grid
            self.populate_faculty_grid(faculties)

            # Ensure scroll area starts at the top
            if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
                self.faculty_scroll.verticalScrollBar().setValue(0)

            # Update current faculty data for future comparisons
            self._current_faculty_data = self._extract_faculty_data(faculties)

        except Exception as e:
            logger.error(f"Error filtering faculty: {str(e)}")
            self.show_notification("Error filtering faculty list", "error")

    def refresh_faculty_status(self):
        """
        Refresh the faculty status from the server with optimizations to reduce loading indicators.
        Implements adaptive refresh rate based on activity.
        """
        try:
            # Store current scroll position to restore it later
            current_scroll_position = 0
            if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
                current_scroll_position = self.faculty_scroll.verticalScrollBar().value()

            # Get current filter settings
            search_text = self.search_bar.text().strip()
            filter_available = self.filter_combo.currentData()

            # Get updated faculty list with current filters
            faculties = self.faculty_controller.get_all_faculty(
                filter_available=filter_available,
                search_term=search_text
            )

            # Check if we have current faculty data to compare
            if hasattr(self, '_current_faculty_data'):
                # Compare with previous data to see if anything changed
                if self._compare_faculty_data(self._current_faculty_data, faculties):
                    # No changes detected, increment consecutive no-change counter
                    self._consecutive_no_changes += 1
                    logger.debug(f"No faculty status changes detected ({self._consecutive_no_changes} consecutive), skipping UI update")

                    # Adjust refresh rate based on consecutive no-changes
                    if self._consecutive_no_changes >= 3:
                        # After 3 consecutive no-changes, slow down the refresh rate
                        current_interval = self.refresh_timer.interval()
                        if current_interval < self._max_refresh_interval:
                            # Increase interval by 60 seconds, up to the maximum
                            new_interval = min(current_interval + 60000, self._max_refresh_interval)
                            self.refresh_timer.setInterval(new_interval)
                            logger.debug(f"Reduced refresh frequency to {new_interval/1000} seconds due to inactivity")

                    return
                else:
                    # Changes detected, reset consecutive no-change counter and restore normal refresh rate
                    self._consecutive_no_changes = 0
                    if self.refresh_timer.interval() > 120000:  # If we're at a slower rate
                        self.refresh_timer.setInterval(120000)  # Reset to base rate of 2 minutes
                        logger.debug("Restored normal refresh rate due to detected changes")

            # Store the new faculty data for future comparisons
            self._current_faculty_data = self._extract_faculty_data(faculties)

            # Update the grid only if there are changes or this is the first load
            self.populate_faculty_grid(faculties)

            # Restore previous scroll position instead of always scrolling to top
            if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
                self.faculty_scroll.verticalScrollBar().setValue(current_scroll_position)

            # Also refresh consultation history if student is logged in, but less frequently
            # import time # Moved to top of file

            # Initialize last refresh time if not set
            if self.student and not hasattr(self, '_last_history_refresh'):
                self._last_history_refresh = time.time()

            current_time = time.time()
            # Only refresh history every 3 minutes (180 seconds) - increased from 2 minutes
            if self.student and (current_time - getattr(self, '_last_history_refresh', 0) > 180):
                self.consultation_panel.refresh_history()
                self._last_history_refresh = current_time

        except Exception as e:
            logger.error(f"Error refreshing faculty status: {str(e)}")
            # Only show notification for serious errors, not for every refresh issue
            if "Connection refused" in str(e) or "Database error" in str(e):
                self.show_notification("Error refreshing faculty status", "error")

            # Reset consecutive no-change counter on errors to ensure we don't slow down too much
            self._consecutive_no_changes = 0

    def _extract_faculty_data(self, faculties):
        """
        Extract relevant data from faculty objects for comparison.

        Args:
            faculties (list): List of faculty objects

        Returns:
            list: List of tuples with faculty ID, name, and status
        """
        return [(f.id, f.name, f.status) for f in faculties]

    def _compare_faculty_data(self, old_data, new_faculties):
        """
        Compare old and new faculty data to detect changes.

        Args:
            old_data (list): Previous faculty data
            new_faculties (list): New faculty objects

        Returns:
            bool: True if data is the same, False if there are changes
        """
        # Extract data from new faculty objects
        new_data = self._extract_faculty_data(new_faculties)

        # Quick length check
        if len(old_data) != len(new_data):
            return False

        # Convert to sets for comparison (ignoring order)
        return set(old_data) == set(new_data)

    def show_consultation_form(self, faculty):
        """
        Show the consultation request form for a specific faculty.

        Args:
            faculty (object): Faculty object to request consultation with
        """
        # Check if faculty is available
        if not faculty.status:
            self.show_notification(
                f"Faculty {faculty.name} is currently unavailable for consultation.",
                "error"
            )
            return

        # Also populate the dropdown with all available faculty
        try:
            available_faculty = self.faculty_controller.get_all_faculty(filter_available=True)

            # Set the faculty and faculty options in the consultation panel
            self.consultation_panel.set_faculty(faculty)
            self.consultation_panel.set_faculty_options(available_faculty)
        except Exception as e:
            logger.error(f"Error loading available faculty for consultation form: {str(e)}")

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request submission.
        This method is now primarily for showing user feedback after the ConsultationPanel 
        has handled the actual creation logic.

        Args:
            faculty (object): Faculty object
            message (str): Consultation request message
            course_code (str): Optional course code
        """
        # The actual consultation creation is handled by ConsultationPanel emitting this signal
        # after it has successfully created the consultation via its controller.
        # This handler in DashboardWindow is now primarily for user feedback.

        try:
            # Show confirmation message
            QMessageBox.information(
                self,
                "Consultation Request",
                f"Your consultation request with {faculty.name} has been submitted."
            )

            # Ensure the consultation panel (which contains the history) is refreshed
            # This might be redundant if ConsultationPanel already refreshes its history tab
            # after successful submission, but ensures consistency.
            self.consultation_panel.refresh_history()
            
        except Exception as e:
            # This exception handling might be for cases where faculty object is malformed for the message string,
            # or if refresh_history itself fails, though create_consultation errors are handled in ConsultationPanel.
            logger.error(f"Error in DashboardWindow.handle_consultation_request (post-submission feedback): {str(e)}")
            QMessageBox.warning(
                self,
                "Consultation Request",
                f"An error occurred while finalizing the consultation request display: {str(e)}"
            )

    def handle_consultation_cancel(self, consultation_id):
        """
        Handle consultation cancellation.

        Args:
            consultation_id (int): ID of the consultation to cancel
        """
        try:
            # Cancel consultation
            consultation = self.consultation_controller.cancel_consultation(consultation_id)

            if consultation:
                # Show confirmation
                QMessageBox.information(
                    self,
                    "Consultation Cancelled",
                    f"Your consultation request has been cancelled."
                )

                # Refresh the consultation history
                self.consultation_panel.refresh_history()
            else:
                QMessageBox.warning(
                    self,
                    "Consultation Cancellation",
                    f"Failed to cancel consultation request. Please try again."
                )
        except Exception as e:
            logger.error(f"Error cancelling consultation: {str(e)}")
            QMessageBox.warning(
                self,
                "Consultation Cancellation",
                f"An error occurred while cancelling your consultation request: {str(e)}"
            )

    def save_splitter_state(self):
        """
        Save the current splitter state to settings.
        """
        try:
            # Create settings object
            settings = QSettings("ConsultEase", "Dashboard")

            # Save splitter state
            settings.setValue("splitter_state", self.content_splitter.saveState())
            settings.setValue("splitter_sizes", self.content_splitter.sizes())

            logger.debug("Saved splitter state")
        except Exception as e:
            logger.error(f"Error saving splitter state: {e}")

    def restore_splitter_state(self):
        """
        Restore the splitter state from settings.
        """
        try:
            # Create settings object
            settings = QSettings("ConsultEase", "Dashboard")

            # Restore splitter state if available
            if settings.contains("splitter_state"):
                state = settings.value("splitter_state")
                if state:
                    self.content_splitter.restoreState(state)
                    logger.debug("Restored splitter state")

            # Fallback to sizes if state restoration fails
            elif settings.contains("splitter_sizes"):
                sizes = settings.value("splitter_sizes")
                if sizes:
                    self.content_splitter.setSizes(sizes)
                    logger.debug("Restored splitter sizes")
        except Exception as e:
            logger.error(f"Error restoring splitter state: {e}")
            # Use default sizes as fallback
            screen_width = QApplication.desktop().screenGeometry().width()
            self.content_splitter.setSizes([int(screen_width * 0.6), int(screen_width * 0.4)])

    def logout(self):
        """
        Handle logout button click.
        """
        # Save splitter state before logout
        self.save_splitter_state()

        self.change_window.emit("login", None)

    def show_notification(self, message, message_type="info"):
        """
        Show a notification message to the user using the standardized notification system.

        Args:
            message (str): Message to display
            message_type (str): Type of message ('success', 'error', 'warning', or 'info')
        """
        try:
            # Get standardized message type
            std_type = NotificationManager.get_standardized_type(message_type)

            # Show notification using the manager
            title = message_type.capitalize()
            if message_type == "error":
                title = "Error"
            elif message_type == "success":
                title = "Success"
            elif message_type == "warning":
                title = "Warning"
            else:
                title = "Information"

            NotificationManager.show_message(self, title, message, std_type)

        except ImportError:
            # Fallback to basic message boxes if notification manager is not available
            logger.warning("NotificationManager not available, using basic message boxes")
            if message_type == "success":
                QMessageBox.information(self, "Success", message)
            elif message_type == "error":
                QMessageBox.warning(self, "Error", message)
            elif message_type == "warning":
                QMessageBox.warning(self, "Warning", message)
            else:
                QMessageBox.information(self, "Information", message)

    def _scroll_faculty_to_top(self):
        """
        Scroll the faculty grid to the top.
        This is called after the UI is fully loaded to ensure faculty cards are visible.
        """
        if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
            self.faculty_scroll.verticalScrollBar().setValue(0)
            logger.debug("Scrolled faculty grid to top")

    def simulate_consultation_request(self):
        """
        Simulate a consultation request for testing purposes.
        This method finds an available faculty and shows the consultation form.
        """
        try:
            # Get available faculty
            available_faculty = self.faculty_controller.get_all_faculty(filter_available=True)

            if available_faculty:
                # Use the first available faculty
                faculty = available_faculty[0]
                logger.info(f"Simulating consultation request with faculty: {faculty.name}")

                # Show the consultation form
                self.show_consultation_form(faculty)
            else:
                logger.warning("No available faculty found for simulation")
                self.show_notification("No available faculty found. Please try again later.", "error")
        except Exception as e:
            logger.error(f"Error simulating consultation request: {str(e)}")
            self.show_notification("Error simulating consultation request", "error")

    def _set_fallback_logo(self):
        # Helper to set a fallback if the logo isn't found
        fallback_pixmap = QPixmap(64, 64)
        fallback_pixmap.fill(Qt.transparent) # Or some other placeholder
        self.logo_label.setPixmap(fallback_pixmap)

    def _setup_rfid_listener(self):
        logger.debug(f"DashboardWindow for {self.student.name}: Setting up RFID listener.")