from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QGridLayout, QScrollArea, QFrame,
                               QLineEdit, QTextEdit, QComboBox, QMessageBox,
                               QSplitter, QApplication, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QSettings
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
from ..utils.notification_manager import NotificationManager
from ..utils.theme import ConsultEaseTheme # Added Theme import

# Set up logging
logger = logging.getLogger(__name__)

class FacultyCard(QFrame):
    """
    Widget to display faculty information and status with an overhauled UI.
    """
    consultation_requested = pyqtSignal(object)

    def __init__(self, faculty, parent=None):
        super().__init__(parent)
        self.faculty = faculty
        self.theme = ConsultEaseTheme() # Store theme instance
        self.init_ui()

    def init_ui(self):
        """
        Initialize the faculty card UI.
        """
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("facultyCard") # For specific card styling

        # Card dimensions and policy
        self.setFixedWidth(260) # Slightly wider for more content space
        self.setMinimumHeight(180) # Adjusted height
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Main layout for the card
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Top part: Image and Name/Department
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        self.image_label = QLabel()
        self.image_label.setFixedSize(60, 60)
        self.image_label.setScaledContents(True)
        self.image_label.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {self.theme.BORDER_COLOR};
                border-radius: 30px; /* Circular image */
                background-color: {self.theme.BG_PRIMARY};
                padding: 2px;
            }}
        """)
        self._load_faculty_image()
        top_layout.addWidget(self.image_label)

        name_dept_layout = QVBoxLayout()
        name_dept_layout.setSpacing(3)
        self.name_label = QLabel(self.faculty.name)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.theme.FONT_SIZE_LARGE}pt;
                font-weight: bold;
                color: {self.theme.TEXT_PRIMARY};
            }}
        """)
        name_dept_layout.addWidget(self.name_label)

        self.dept_label = QLabel(self.faculty.department)
        self.dept_label.setWordWrap(True)
        self.dept_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.theme.FONT_SIZE_NORMAL}pt;
                color: {self.theme.TEXT_SECONDARY};
            }}
        """)
        name_dept_layout.addWidget(self.dept_label)
        top_layout.addLayout(name_dept_layout)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Separator Line - more subtle
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {self.theme.BORDER_COLOR_LIGHT};")
        main_layout.addWidget(separator)

        # Middle part: Status
        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        self.status_icon_label = QLabel("●") # Unicode circle
        self.status_text_label = QLabel()
        status_layout.addWidget(self.status_icon_label)
        status_layout.addWidget(self.status_text_label)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)

        main_layout.addStretch(1) # Pushes button to bottom if space allows

        # Bottom part: Request Button
        self.request_button = QPushButton("Request Consultation")
        self.request_button.setObjectName("requestButton")
        self.request_button.setIcon(IconProvider.get_icon(Icons.CALENDAR_ADD if hasattr(Icons, 'CALENDAR_ADD') else Icons.ADD, QSize(18,18)))
        self.request_button.setStyleSheet(f"""
            QPushButton#requestButton {{
                font-size: {self.theme.FONT_SIZE_NORMAL}pt;
                padding: 10px;
                border-radius: {self.theme.BORDER_RADIUS_NORMAL}px;
                background-color: {self.theme.PRIMARY_COLOR};
                color: {self.theme.TEXT_LIGHT};
                font-weight: bold;
            }}
            QPushButton#requestButton:hover {{
                background-color: {self.theme.PRIMARY_COLOR_HOVER};
            }}
            QPushButton#requestButton:disabled {{
                background-color: {self.theme.TEXT_SECONDARY};
                color: {self.theme.BG_PRIMARY_MUTED};
            }}
        """)
        self.request_button.clicked.connect(self.request_consultation)
        main_layout.addWidget(self.request_button)

        self.update_style_and_status() # Initial style and status update

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

    def update_style_and_status(self):
        """
        Updates card style based on faculty status and text labels.
        """
        if self.faculty.status:
            border_color = self.theme.SUCCESS_COLOR
            status_text = "Available"
            status_icon_color = self.theme.SUCCESS_COLOR
            self.request_button.setEnabled(True)
            card_bg = self.theme.BG_PRIMARY # White background for available
        else:
            border_color = self.theme.ERROR_COLOR
            status_text = "Unavailable"
            status_icon_color = self.theme.ERROR_COLOR
            self.request_button.setEnabled(False)
            card_bg = "#fff0f0" # Very light red for unavailable, distinct but not harsh

        self.setStyleSheet(f"""
            QFrame#facultyCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: {self.theme.BORDER_RADIUS_LARGE}px;
                /* margin is handled by grid layout spacing */
            }}
            /* Other specific styles for elements inside this card if needed */
        """)

        self.status_icon_label.setStyleSheet(f"font-size: 18pt; color: {status_icon_color}; border: none;")
        self.status_text_label.setText(status_text)
        self.status_text_label.setStyleSheet(f"font-size: {self.theme.FONT_SIZE_NORMAL}pt; color: {status_icon_color}; font-weight: bold; border: none;")

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
            try:
                default_icon = IconProvider.get_icon(Icons.USER, QSize(60, 60))
                if default_icon and not default_icon.isNull():
                    self.image_label.setPixmap(default_icon.pixmap(QSize(60,60)))
                else:
                    logger.warning(f"Default user icon (Icons.USER) could not be loaded. Using theme placeholder for {self.faculty.name}.")
                    fallback_pixmap = QPixmap(QSize(60, 60))
                    fallback_pixmap.fill(QColor(self.theme.BG_SECONDARY)) # Theme color for placeholder bg
                    self.image_label.setPixmap(fallback_pixmap)
            except Exception as e:
                logger.error(f"Exception while trying to load default user icon for {self.faculty.name}: {str(e)}")
                fallback_pixmap = QPixmap(QSize(60, 60))
                fallback_pixmap.fill(QColor(self.theme.BG_SECONDARY))
                self.image_label.setPixmap(fallback_pixmap)

    def update_faculty(self, faculty):
        """
        Update the faculty information efficiently.
        """
        self.faculty = faculty
        self.name_label.setText(self.faculty.name)
        self.dept_label.setText(self.faculty.department)
        self._load_faculty_image()
        self.update_style_and_status()

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
        self.student = student # Set self.student BEFORE calling super().__init__
        self.theme = ConsultEaseTheme() # Add theme instance
        super().__init__(parent) # Now BaseWindow.__init__ can call init_ui, which can access self.student
        # self.student = student # No longer needed here

        # Get controller instances (now singletons)
        self.faculty_controller = FacultyController.instance()
        self.consultation_controller = ConsultationController.instance()

        # UI elements for faculty grid feedback
        self.loading_label = QLabel("Loading faculty data...")
        self.loading_label.setStyleSheet(f"font-size: {self.theme.FONT_SIZE_LARGE}pt; color: {self.theme.TEXT_SECONDARY}; padding: 30px;")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setVisible(False)

        self.no_results_label = QLabel("No faculty members found matching your criteria.")
        self.no_results_label.setStyleSheet(f"font-size: {self.theme.FONT_SIZE_LARGE}pt; color: {self.theme.TEXT_SECONDARY}; padding: 30px; background-color: {self.theme.BG_SECONDARY}; border-radius: {self.theme.BORDER_RADIUS_LARGE}px;")
        self.no_results_label.setAlignment(Qt.AlignCenter)
        self.no_results_label.setVisible(False)
        
        # Store faculty cards to manage them directly
        self._faculty_cards_widgets = []

        # Initialize UI components - REMOVED as super().__init__ calls init_ui polymorphicly
        # self.init_ui()

        # Set up auto-refresh timer for faculty status with further reduced frequency
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_faculty_status)
        self.refresh_timer.start(get_config().get('ui.dashboard_refresh_ms', 120000))

        # Track consecutive no-change refreshes to further reduce refresh frequency when idle
        self._consecutive_no_changes = 0
        self._max_refresh_interval = get_config().get('ui.dashboard_max_refresh_ms', 300000)

        # Log student info for debugging
        if student:
            logger.info(f"Dashboard initialized for student: ID={student.id}, Name={student.name}")
        else:
            logger.warning("Dashboard initialized without student information")
        
        # Initial population of faculty grid
        self.refresh_faculty_status()

    def init_ui(self):
        """
        Initialize the dashboard UI.
        """
        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20) # Overall padding
        main_layout.setSpacing(15)

        # --- Header Area ---
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        # header_frame.setFixedHeight(80) # Fixed height for header
        header_frame.setStyleSheet(f"""
            QFrame#headerFrame {{
                background-color: {self.theme.PRIMARY_COLOR};
                border-radius: {self.theme.BORDER_RADIUS_LARGE}px;
                padding: 10px 20px;
            }}
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0,0,0,0)

        self.logo_label = QLabel()
        # Assuming IconProvider.get_icon("logo_light") for a logo suitable for dark background
        logo_icon = IconProvider.get_icon(Icons.LOGO_LIGHT if hasattr(Icons, 'LOGO_LIGHT') else Icons.APP_ICON, QSize(50,50))
        if logo_icon and not logo_icon.isNull():
             self.logo_label.setPixmap(logo_icon.pixmap(QSize(50,50)))
        else:
            self._set_fallback_logo(QSize(50,50), self.theme.TEXT_LIGHT) # Light fallback for dark bg
        header_layout.addWidget(self.logo_label)

        title_label = QLabel("ConsultEase Dashboard")
        title_label.setStyleSheet(f"font-size: {self.theme.FONT_SIZE_XXLARGE}pt; font-weight: bold; color: {self.theme.TEXT_LIGHT};")
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        # Logout Button in Header
        self.logout_button = QPushButton("Logout")
        self.logout_button.setIcon(IconProvider.get_icon(Icons.LOGOUT, QSize(20,20)))
        self.logout_button.setFixedWidth(120)
        self.logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.ACCENT_COLOR};
                color: {self.theme.TEXT_PRIMARY};
                padding: 8px;
                border-radius: {self.theme.BORDER_RADIUS_NORMAL}px;
                font-size: {self.theme.FONT_SIZE_NORMAL}pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #f7dc80; /* Lighter Accent */
            }}
        """)
        self.logout_button.clicked.connect(self.logout)
        header_layout.addWidget(self.logout_button)
        main_layout.addWidget(header_frame)

        # --- Search and Filter Area ---
        search_filter_frame = QFrame()
        search_filter_frame.setObjectName("searchFilterFrame")
        search_filter_layout = QHBoxLayout(search_filter_frame)
        search_filter_layout.setContentsMargins(0, 10, 0, 5) # Top/bottom margin for this section
        search_filter_layout.setSpacing(10)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search faculty by name or department...")
        self.search_bar.setFixedHeight(self.theme.TOUCH_MIN_HEIGHT + 5) # Slightly taller
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {self.theme.BORDER_COLOR};
                border-radius: {self.theme.BORDER_RADIUS_NORMAL}px;
                padding: 0px 10px;
                background-color: {self.theme.BG_PRIMARY};
                font-size: {self.theme.FONT_SIZE_NORMAL}pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.theme.PRIMARY_COLOR};
            }}
        """)
        self.search_bar.textChanged.connect(self.filter_faculty)
        search_filter_layout.addWidget(self.search_bar, 2) # Search bar takes more space

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Faculty", "Available Only", "Unavailable Only"])
        # Use currentData for logic, text for display
        self.filter_combo.setItemData(0, "all")
        self.filter_combo.setItemData(1, "available")
        self.filter_combo.setItemData(2, "unavailable")
        self.filter_combo.setFixedHeight(self.theme.TOUCH_MIN_HEIGHT + 5)

        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {self.theme.BORDER_COLOR};
                border-radius: {self.theme.BORDER_RADIUS_NORMAL}px;
                padding: 0px 10px;
                background-color: {self.theme.BG_PRIMARY};
                font-size: {self.theme.FONT_SIZE_NORMAL}pt;
                min-width: 180px; /* Ensure readable width */
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left: 1px solid {self.theme.BORDER_COLOR};
            }}
            QComboBox::down-arrow {{
                /* image: url(...); */ /* Default system arrow will be used */
                width: 16px;
                height: 16px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {self.theme.PRIMARY_COLOR};
                background-color: {self.theme.BG_PRIMARY};
                color: {self.theme.TEXT_PRIMARY};
                selection-background-color: {self.theme.ACCENT_COLOR};
                selection-color: {self.theme.TEXT_PRIMARY};
                padding: 5px;
            }}
        """)
        self.filter_combo.currentIndexChanged.connect(self.filter_faculty) # Use currentIndexChanged for QComboBox
        search_filter_layout.addWidget(self.filter_combo, 1)
        main_layout.addWidget(search_filter_frame)

        # --- Main Content Area (Splitter) ---
        self.content_splitter = QSplitter(Qt.Horizontal)
        self.content_splitter.setObjectName("dashboardSplitter")
        self.content_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #d0d0d0; /* Light gray handle */
                width: 3px; /* Slimmer handle */
            }
            QSplitter::handle:hover {
                background-color: #b0b0b0; /* Darker on hover */
            }
        """)

        # Left side: Faculty Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"background-color: {self.theme.BG_SECONDARY}; border-radius: {self.theme.BORDER_RADIUS_NORMAL}px; border: 1px solid {self.theme.BORDER_COLOR_LIGHT};")

        self.faculty_cards_widget = QWidget()
        self.faculty_grid_layout = QGridLayout(self.faculty_cards_widget)
        self.faculty_grid_layout.setSpacing(20) # Spacing between cards
        self.faculty_grid_layout.setContentsMargins(15,15,15,15) # Padding within the scroll area content
        self.faculty_grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_area.setWidget(self.faculty_cards_widget)
        self.content_splitter.addWidget(self.scroll_area)

        # Right side: Consultation Panel
        self.consultation_panel = ConsultationPanel(self.student) # Already styled in its own class
        self.consultation_panel.consultation_requested.connect(self.handle_consultation_request_feedback)
        self.consultation_panel.consultation_cancelled.connect(self.handle_consultation_cancel_feedback)
        self.content_splitter.addWidget(self.consultation_panel)
        
        main_layout.addWidget(self.content_splitter, 1) # Splitter takes remaining space

        # Restore splitter state or set defaults
        screen_width = QApplication.primaryScreen().geometry().width() if QApplication.primaryScreen() else 1280
        default_left_width = int(screen_width * 0.62)
        default_right_width = int(screen_width * 0.38)
        self.restore_splitter_state(default_sizes=[default_left_width, default_right_width])
        self.content_splitter.splitterMoved.connect(self.save_splitter_state)

        # Temporary manual RFID entry - consider moving to a more appropriate place or dialog
        # ... (manual RFID input commented out as per previous state, can be restyled if re-added)

        QTimer.singleShot(100, self._scroll_faculty_to_top)

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
            for i in reversed(range(self.faculty_grid_layout.count())):
                widget_to_remove = self.faculty_grid_layout.itemAt(i).widget()
                if widget_to_remove:
                    self.faculty_grid_layout.removeWidget(widget_to_remove)
                    widget_to_remove.deleteLater()
            self._faculty_cards_widgets.clear()
            self.loading_label.setVisible(False)
            self.no_results_label.setVisible(False)

            # Grid layout logic
            # Card width + spacing defined in FacultyCard and grid layout
            # Calculate max_cols based on scroll_area width
            scroll_area_width = self.scroll_area.viewport().width() if self.scroll_area.viewport() else 600
            card_plus_spacing = 260 + self.faculty_grid_layout.spacing() # FacultyCard width + grid spacing
            max_cols = max(1, int(scroll_area_width / card_plus_spacing))

            if not faculties:
                # Add no_results_label to grid layout directly (spanning columns)
                self.faculty_grid_layout.addWidget(self.no_results_label, 0, 0, 1, max_cols, Qt.AlignCenter)
                self.no_results_label.setVisible(True)
            else:
                row, col = 0, 0
                for faculty in faculties:
                    # No need for extra container if FacultyCard handles its own margins/shadows well
                    card = FacultyCard(faculty)
                    card.consultation_requested.connect(self.show_consultation_form_for_faculty)
                    self.faculty_grid_layout.addWidget(card, row, col)
                    self._faculty_cards_widgets.append(card) # Store the card itself
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
                # Add stretch to fill remaining space if cards don't fill last row
                if faculties:
                    self.faculty_grid_layout.setRowStretch(row + 1, 1)
                    self.faculty_grid_layout.setColumnStretch(col +1, 1)

        finally:
            self.setUpdatesEnabled(True)
            self.faculty_cards_widget.adjustSize() # Crucial for grid to recalculate size
            QApplication.processEvents() # Ensure UI updates are processed

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
            search_text = self.search_bar.text().strip().lower()
            filter_value = self.filter_combo.currentData() # Using currentData set earlier

            # Determine availability filter based on combo box selection
            filter_available_bool = None
            if filter_value == "available": filter_available_bool = True
            elif filter_value == "unavailable": filter_available_bool = False
            
            faculties = self.faculty_controller.get_all_faculty(
                filter_available=filter_available_bool,
                search_term=search_text
            )
            self.populate_faculty_grid(faculties)
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
            # Show loading label if it's the first load or a significant delay is expected
            # For now, relying on fast updates, but could add self.loading_label.setVisible(True) here

            search_text = self.search_bar.text().strip().lower()
            filter_value = self.filter_combo.currentData()
            filter_available_bool = None
            if filter_value == "available": filter_available_bool = True
            elif filter_value == "unavailable": filter_available_bool = False

            faculties = self.faculty_controller.get_all_faculty(
                filter_available=filter_available_bool,
                search_term=search_text
            )

            current_data_snapshot = self._extract_faculty_data(faculties)
            if hasattr(self, '_current_faculty_data') and set(self._current_faculty_data) == set(current_data_snapshot):
                self._consecutive_no_changes += 1
                logger.debug(f"No faculty status changes detected ({self._consecutive_no_changes} consecutive).")
                if self._consecutive_no_changes >= 3 and self.refresh_timer.interval() < self._max_refresh_interval:
                    new_interval = min(self.refresh_timer.interval() + 60000, self._max_refresh_interval)
                    self.refresh_timer.setInterval(new_interval)
                    logger.debug(f"Reduced refresh frequency to {new_interval/1000}s.")
                # self.loading_label.setVisible(False) # Hide loading if it was shown
                return
            
            self._consecutive_no_changes = 0
            if self.refresh_timer.interval() > get_config().get('ui.dashboard_refresh_ms', 120000):
                self.refresh_timer.setInterval(get_config().get('ui.dashboard_refresh_ms', 120000))
                logger.debug("Restored normal refresh rate.")

            self._current_faculty_data = current_data_snapshot
            self.populate_faculty_grid(faculties)
            # self.loading_label.setVisible(False)

            # Less frequent history refresh, handled by ConsultationPanel itself now
        except Exception as e:
            logger.error(f"Error refreshing faculty status: {str(e)}")
            # self.loading_label.setVisible(False)
            if "Connection refused" in str(e) or "Database error" in str(e):
                 self.show_notification("Error refreshing faculty status. Check connection.", "error")
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

    def show_consultation_form_for_faculty(self, faculty):
        """
        Show the consultation request form for a specific faculty.

        Args:
            faculty (object): Faculty object to request consultation with
        """
        # Check if faculty is available
        if not faculty.status:
            self.show_notification(
                f"Faculty {faculty.name} is currently unavailable for consultation.",
                "warning"
            )
            return

        # Also populate the dropdown with all available faculty
        try:
            logger.info(f"Showing consultation form for faculty: {faculty.name}")
            
            # Load available faculty for the dropdown
            available_faculty = self.faculty_controller.get_all_faculty(filter_available=True) # Or get all faculty if selection should be wider
            if not available_faculty:
                logger.warning("No faculty available for consultation form dropdown.")
                # Keep a list of all faculty as a fallback, even if unavailable, they can be selected
                # but the form itself should prevent submission if they are not truly available.
                all_faculty = self.faculty_controller.get_all_faculty()
                if not all_faculty: # Should not happen if DB has faculty
                    NotificationManager.show_message(self, "Error", "No faculty found in the system.", NotificationManager.ERROR)
                    return
                available_faculty = all_faculty # Use all as fallback, form will handle availability check.

            # Pass the specific faculty and the list of available faculty to the panel
            self.consultation_panel.set_faculty_options(available_faculty)
            self.consultation_panel.set_faculty(faculty)
            self.consultation_panel.animate_tab_change(0) # Switch to the request form tab
            
            # Ensure the consultation panel is visible and focused
            self.consultation_panel.setVisible(True)
        except Exception as e:
            logger.error(f"Error loading available faculty for consultation form: {str(e)}")
            self.show_notification("Error preparing consultation form.", "error")

    def handle_consultation_request_feedback(self, faculty, message, course_code):
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

    def handle_consultation_cancel_feedback(self, success_flag, message):
        """
        Handle consultation cancellation.

        Args:
            success_flag (bool): Success flag from ConsultationPanel
            message (str): Message from ConsultationPanel
        """
        if success_flag:
            QMessageBox.information(self, "Consultation Cancelled", message)
        else:
            QMessageBox.warning(self, "Cancellation Failed", message)

    def save_splitter_state(self):
        """
        Save the current splitter state to settings.
        """
        settings = QSettings("ConsultEase", "DashboardWindow")
        settings.setValue("splitterSizes", self.content_splitter.sizes())
        logger.debug(f"Saved splitter sizes: {self.content_splitter.sizes()}")

    def restore_splitter_state(self, default_sizes=None):
        """
        Restore the splitter state from settings.
        """
        if default_sizes is None: default_sizes = [600, 400]
        settings = QSettings("ConsultEase", "DashboardWindow")
        sizes = settings.value("splitterSizes", default_sizes, type=list)
        # Ensure sizes are integers
        try:
            sizes = [int(s) for s in sizes]
            if len(sizes) == 2 and all(isinstance(s, int) for s in sizes) and sum(sizes) > 100: # Basic sanity check
                 self.content_splitter.setSizes(sizes)
                 logger.debug(f"Restored splitter sizes: {sizes}")
            else:
                logger.warning(f"Invalid splitter sizes from settings: {sizes}. Using defaults: {default_sizes}")
                self.content_splitter.setSizes(default_sizes)
        except Exception as e:
            logger.error(f"Error restoring splitter state (sizes: {sizes}): {e}. Using defaults: {default_sizes}")
            self.content_splitter.setSizes(default_sizes)

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
        if self.scroll_area and self.scroll_area.verticalScrollBar():
            self.scroll_area.verticalScrollBar().setValue(0)
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
                self.show_consultation_form_for_faculty(faculty)
            else:
                logger.warning("No available faculty found for simulation")
                self.show_notification("No available faculty found. Please try again later.", "error")
        except Exception as e:
            logger.error(f"Error simulating consultation request: {str(e)}")
            self.show_notification("Error simulating consultation request", "error")

    def _set_fallback_logo(self, size=QSize(64,64), color=None):
        if color is None: color = QColor(self.theme.PRIMARY_COLOR)
        fallback_pixmap = QPixmap(size)
        fallback_pixmap.fill(color)
        # Potentially draw initials or a generic icon on the pixmap here
        self.logo_label.setPixmap(fallback_pixmap)