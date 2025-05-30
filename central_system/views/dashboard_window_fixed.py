import logging
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import QSize

from central_system.utils.icon_provider import IconProvider, Icons

logger = logging.getLogger(__name__)


class FacultyProfileWidget:
    """Widget to display faculty profile information with image and status."""

    def __init__(self, faculty, theme):
        """
        Initialize the widget with faculty data.

        Args:
            faculty: The faculty model instance
            theme: The application theme
        """
        self.faculty = faculty
        self.theme = theme
        self.image_label = QLabel()
        self.image_label.setFixedSize(60, 60)
        self._load_faculty_image()

    def _load_faculty_image(self):
        pixmap_loaded = False
        # Assume self.faculty.get_image_path() returns an absolute, verified
        # path or None
        image_path = self.faculty.get_image_path() if hasattr(
            self.faculty, 'get_image_path') else None

        if image_path:  # If model provides a valid path
            try:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap)
                    pixmap_loaded = True
                else:
                    logger.warning(
                        f"Could not load image for faculty {self.faculty.name} "
                        f"from provided path: {image_path} (pixmap isNull)"
                    )
            except Exception as e:
                logger.error(
                    f"Error loading faculty image for {self.faculty.name} "
                    f"from {image_path}: {str(e)}"
                )

        if not pixmap_loaded:
            # Fallback to default icon
            try:
                # Assuming IconProvider.get_icon returns a QIcon object
                default_qicon = IconProvider.get_icon(Icons.USER)
                if default_qicon and not default_qicon.isNull():
                    # Specify size for pixmap
                    self.image_label.setPixmap(default_qicon.pixmap(QSize(60, 60)))
                else:
                    logger.warning(
                        f"Default user icon (Icons.USER) could not be loaded or is null. "
                        f"Using theme placeholder for {self.faculty.name}."
                    )
                    fallback_pixmap = QPixmap(QSize(60, 60))
                    fallback_pixmap.fill(QColor(self.theme.BG_SECONDARY))
                    self.image_label.setPixmap(fallback_pixmap)
            except Exception as e:
                logger.error(
                    f"Exception while trying to load default user icon for "
                    f"{self.faculty.name}: {str(e)}"
                )
                fallback_pixmap = QPixmap(QSize(60, 60))
                fallback_pixmap.fill(QColor(self.theme.BG_SECONDARY))
                self.image_label.setPixmap(fallback_pixmap)

    def get_image_label(self):
        """
        Get the QLabel containing the faculty image.

        Returns:
            QLabel: The label with the faculty image
        """
        return self.image_label

    def update_faculty(self, faculty):
        """
        Update the widget with new faculty data.

        Args:
            faculty: The new faculty model instance
        """
        self.faculty = faculty
        self._load_faculty_image()
