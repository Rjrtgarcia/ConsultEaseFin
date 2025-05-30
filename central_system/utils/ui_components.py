"""
UI component library for ConsultEase.
Provides modern, reusable UI components for a consistent and user-friendly experience.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QLineEdit, QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QIcon, QFont, QPalette

from .icons import IconProvider, Icons

logger = logging.getLogger(__name__)


class ModernButton(QPushButton):
    """
    Modern button with consistent styling, touch-friendly size, and icons.
    """

    def __init__(self, text="", icon_name=None, primary=False, danger=False, parent=None):
        """
        Initialize a modern button.

        Args:
            text (str): Button text
            icon_name (str, optional): Icon name from Icons class
            primary (bool): Whether this is a primary button (more prominent)
            danger (bool): Whether this is a danger/destructive button
            parent: Parent widget
        """
        super(ModernButton, self).__init__(text, parent)

        # Set minimum size for touch-friendliness
        self.setMinimumSize(120, 48)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # Configure style
        if primary:
            self.setObjectName("primary_button")
        elif danger:
            self.setObjectName("danger_button")

        # Add icon if specified
        if icon_name:
            self.setIcon(IconProvider.get_button_icon(icon_name))
            self.setIconSize(QSize(24, 24))


class IconButton(QPushButton):
    """
    Icon-only button for toolbar-like functionality.
    """

    def __init__(self, icon_name, tooltip="", parent=None):
        """
        Initialize an icon button.

        Args:
            icon_name (str): Icon name from Icons class
            tooltip (str): Tooltip text
            parent: Parent widget
        """
        super(IconButton, self).__init__(parent)

        # Set fixed size for consistent layout
        self.setFixedSize(48, 48)

        # Add icon
        self.setIcon(IconProvider.get_button_icon(icon_name))
        self.setIconSize(QSize(32, 32))

        # Set tooltip
        if tooltip:
            self.setToolTip(tooltip)

        # Flat style for icon buttons
        self.setFlat(True)


class FacultyCard(QFrame):
    """
    Card widget displaying faculty information with availability status.
    """

    # Signal emitted when the card is clicked
    clicked = pyqtSignal(dict)

    def __init__(self, faculty_data, parent=None):
        """
        Initialize a faculty card.

        Args:
            faculty_data (dict): Faculty information (id, name, department, available, etc.)
            parent: Parent widget
        """
        super(FacultyCard, self).__init__(parent)

        self.faculty_data = faculty_data

        # Set appropriate object name based on availability
        if faculty_data.get("available", False):
            self.setObjectName("faculty_card_available")
        else:
            self.setObjectName("faculty_card_unavailable")

        # Set fixed size
        self.setMinimumSize(300, 180)
        self.setMaximumSize(400, 220)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        # Set up the layout
        self._setup_ui()

        # Make clickable
        self.setCursor(Qt.PointingHandCursor)

    def _setup_ui(self):
        """Set up the card UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # Faculty name (bold)
        self.name_label = QLabel(self.faculty_data.get("name", "Unknown Faculty"))
        self.name_label.setObjectName("heading")
        layout.addWidget(self.name_label)

        # Department
        dept_layout = QHBoxLayout()
        dept_icon = QLabel()
        dept_icon.setPixmap(IconProvider.get_icon(Icons.FACULTY).pixmap(QSize(16, 16)))
        dept_label = QLabel(self.faculty_data.get("department", "Department"))
        dept_layout.addWidget(dept_icon)
        dept_layout.addWidget(dept_label)
        dept_layout.addStretch()
        layout.addLayout(dept_layout)

        # Status
        status_layout = QHBoxLayout()
        status_text = "Available" if self.faculty_data.get("available", False) else "Unavailable"
        status_icon_name = Icons.AVAILABLE if self.faculty_data.get(
            "available", False) else Icons.UNAVAILABLE
        status_icon = QLabel()
        status_icon.setPixmap(IconProvider.get_icon(status_icon_name).pixmap(QSize(16, 16)))

        status_label = QLabel(status_text)
        if self.faculty_data.get("available", False):
            status_label.setObjectName("available")
        else:
            status_label.setObjectName("unavailable")

        status_layout.addWidget(status_icon)
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Add room information if available
        if "room" in self.faculty_data:
            room_layout = QHBoxLayout()
            room_label = QLabel(f"Room: {self.faculty_data['room']}")
            room_layout.addWidget(room_label)
            room_layout.addStretch()
            layout.addLayout(room_layout)

        # Add spacing
        layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Request button (only enabled if faculty is available)
        self.request_button = ModernButton(
            "Request Consultation",
            icon_name=Icons.MESSAGE,
            primary=True)
        self.request_button.setEnabled(self.faculty_data.get("available", False))
        layout.addWidget(self.request_button)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        super(FacultyCard, self).mousePressEvent(event)
        self.clicked.emit(self.faculty_data)

    def enterEvent(self, event):
        """Handle mouse enter events with subtle hover effect."""
        # Create a scale animation
        self._animate_scale(1.03)
        super(FacultyCard, self).enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave events."""
        # Create a scale animation back to normal
        self._animate_scale(1.0)
        super(FacultyCard, self).leaveEvent(event)

    def _animate_scale(self, scale_factor):
        """
        Animate the card scaling.

        Args:
            scale_factor (float): Target scale factor
        """
        # Store original size for animation
        original_size = self.size()
        target_width = int(original_size.width() * scale_factor)
        target_height = int(original_size.height() * scale_factor)

        # Create the animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        # Calculate centered position
        pos = self.pos()
        width_diff = target_width - original_size.width()
        height_diff = target_height - original_size.height()

        # Set start and end geometries
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(QRect(
            pos.x() - width_diff // 2,
            pos.y() - height_diff // 2,
            target_width,
            target_height
        ))

        # Start the animation
        self.animation.start()


class ModernSearchBox(QWidget):
    """
    Modern search input with clear button and search icon.
    """

    # Signal emitted when search text changes
    search_changed = pyqtSignal(str)

    def __init__(self, placeholder="Search...", parent=None):
        """
        Initialize a modern search box.

        Args:
            placeholder (str): Placeholder text
            parent: Parent widget
        """
        super(ModernSearchBox, self).__init__(parent)

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Search icon
        self.search_icon = QLabel()
        self.search_icon.setPixmap(IconProvider.get_icon(Icons.SEARCH).pixmap(QSize(16, 16)))
        self.search_icon.setFixedSize(36, 48)
        layout.addWidget(self.search_icon)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.setMinimumHeight(48)
        self.search_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.search_input)

        # Clear button
        self.clear_button = IconButton(Icons.CANCEL, "Clear search")
        self.clear_button.setFixedSize(36, 48)
        self.clear_button.clicked.connect(self.clear)
        self.clear_button.hide()  # Initially hidden
        layout.addWidget(self.clear_button)

    def _on_text_changed(self, text):
        """Handle text changes in the search input."""
        self.clear_button.setVisible(bool(text))
        self.search_changed.emit(text)

    def clear(self):
        """Clear the search input."""
        self.search_input.clear()

    def text(self):
        """Get the current search text."""
        return self.search_input.text()

    def setFocus(self):
        """Set focus to the search input."""
        self.search_input.setFocus()


class NotificationBanner(QFrame):
    """
    Notification banner for displaying success, error, or info messages.
    Automatically disappears after a timeout.
    """

    # Message types with corresponding styles
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    def __init__(self, parent=None):
        """
        Initialize a notification banner.

        Args:
            parent: Parent widget
        """
        super(NotificationBanner, self).__init__(parent)

        # Set up UI
        self._setup_ui()

        # Hide initially
        self.hide()

        # Animation for showing/hiding
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        # Timer for auto-hide
        self.timer = None

    def _setup_ui(self):
        """Set up the banner UI."""
        # Set minimum height
        self.setMinimumHeight(60)

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        layout.addWidget(self.icon_label)

        # Message
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)

        # Close button
        self.close_button = IconButton(Icons.CANCEL, "Dismiss")
        self.close_button.clicked.connect(self.hide_animation)
        layout.addWidget(self.close_button)

    def show_message(self, message, message_type=INFO, timeout=3000):
        """
        Show a notification message.

        Args:
            message (str): Message to display
            message_type (str): Type of message (INFO, SUCCESS, WARNING, ERROR)
            timeout (int): Time in ms before auto-hiding (0 for no auto-hide)
        """
        # Configure icon and style based on message type
        if message_type == self.SUCCESS:
            icon_name = Icons.SUCCESS
            self.setObjectName("success_banner")
        elif message_type == self.WARNING:
            icon_name = Icons.WARNING
            self.setObjectName("warning_banner")
        elif message_type == self.ERROR:
            icon_name = Icons.ERROR
            self.setObjectName("error_banner")
        else:  # INFO is default
            icon_name = Icons.INFO
            self.setObjectName("info_banner")

        # Update icon and message
        self.icon_label.setPixmap(IconProvider.get_icon(icon_name).pixmap(QSize(24, 24)))
        self.message_label.setText(message)

        # Force style update
        self.style().unpolish(self)
        self.style().polish(self)

        # Show with animation
        self.show_animation()

        # Set timer for auto-hide if timeout > 0
        if timeout > 0:
            try:
                if self.timer:
                    self.timer.stop()
                from PyQt5.QtCore import QTimer
                self.timer = QTimer()
                self.timer.setSingleShot(True)
                self.timer.timeout.connect(self.hide_animation)
                self.timer.start(timeout)
            except Exception as e:
                logger.error(f"Error setting notification timer: {e}")

    def show_animation(self):
        """Show the banner with a slide-down animation."""
        # Stop any running animations
        self.animation.stop()

        # Make sure widget is visible
        self.show()

        # Get parent dimensions
        if self.parent():
            parent_width = self.parent().width()
        else:
            parent_width = self.width()

        # Calculate start and end positions
        start_height = self.height()
        self.animation.setStartValue(QRect(0, -start_height, parent_width, start_height))
        self.animation.setEndValue(QRect(0, 0, parent_width, start_height))

        # Start animation
        self.animation.start()

    def hide_animation(self):
        """Hide the banner with a slide-up animation."""
        # Stop any running animations
        self.animation.stop()

        # Get parent dimensions
        if self.parent():
            parent_width = self.parent().width()
        else:
            parent_width = self.width()

        # Calculate start and end positions
        start_height = self.height()
        self.animation.setStartValue(QRect(0, 0, parent_width, start_height))
        self.animation.setEndValue(QRect(0, -start_height, parent_width, start_height))

        # Connect to finished signal to hide widget
        self.animation.finished.connect(self.hide)

        # Start animation
        self.animation.start()


class LoadingOverlay(QWidget):
    """
    Semi-transparent overlay with loading indicator.
    Used to block UI during longer operations.
    """

    def __init__(self, parent=None):
        """
        Initialize a loading overlay.

        Args:
            parent: Parent widget
        """
        super(LoadingOverlay, self).__init__(parent)

        # Set up UI
        self._setup_ui()

        # Hide initially
        self.hide()

        # Track parent resizes
        if parent:
            self.resize(parent.size())
            parent.resizeEvent = self._handle_parent_resize

    def _setup_ui(self):
        """Set up the overlay UI."""
        # Set background color and opacity
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 128))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # Loading indicator (just a text label for now)
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            background-color: #313244;
            color: white;
            font-size: 16pt;
            font-weight: bold;
            padding: 20px 40px;
            border-radius: 10px;
        """)
        layout.addWidget(self.loading_label)

    def _handle_parent_resize(self, event):
        """Handle parent widget resize events."""
        # Resize overlay to match parent
        self.resize(event.size())

        # Call original parent resizeEvent if it exists
        parent = self.parent()
        if parent and hasattr(parent, "_original_resize_event"):
            parent._original_resize_event(event)

    def show_loading(self, message="Loading..."):
        """
        Show the loading overlay with specified message.

        Args:
            message (str): Loading message to display
        """
        self.loading_label.setText(message)
        self.show()

        # Ensure overlay is on top
        self.raise_()

        # Force update
        from PyQt5.QtCore import QCoreApplication
        QCoreApplication.processEvents()

    def hide_loading(self):
        """Hide the loading overlay."""
        self.hide()
