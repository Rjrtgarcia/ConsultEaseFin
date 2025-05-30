"""
Centralized theme system for ConsultEase.
This module provides consistent styling across the application.
"""
import logging
import os

logger = logging.getLogger(__name__)


class ConsultEaseTheme:
    """
    Centralized theme class for ConsultEase.
    Provides consistent colors, fonts, and styling across the application.
    """

    # Color palette
    PRIMARY_COLOR = "#0d3b66"       # Dark blue
    PRIMARY_COLOR_HOVER = "#1a5f99"  # Slightly lighter dark blue for hover
    SECONDARY_COLOR = "#3498db"     # Light blue
    ACCENT_COLOR = "#f4d35e"        # Gold
    SUCCESS_COLOR = "#2ecc71"       # Green
    SUCCESS_COLOR_HOVER = "#27ae60"  # Darker Green for hover
    WARNING_COLOR = "#f39c12"       # Orange
    WARNING_COLOR_HOVER = "#e67e22"  # Darker Orange for hover
    ERROR_COLOR = "#e74c3c"         # Red
    ERROR_COLOR_HOVER = "#c0392b"   # Darker Red for hover
    INFO_COLOR = "#3498db"          # Blue

    # Status colors with improved contrast
    STATUS_PENDING = "#f39c12"      # Darker amber for better contrast
    STATUS_ACCEPTED = "#27ae60"     # Darker green
    STATUS_COMPLETED = "#2980b9"    # Darker blue
    STATUS_CANCELLED = "#c0392b"    # Darker red

    # Background colors
    BG_PRIMARY = "#ffffff"          # White
    BG_PRIMARY_MUTED = "#e9ecef"    # Very light gray, for tab backgrounds
    BG_SECONDARY = "#f5f5f5"        # Light gray
    BG_SECONDARY_LIGHT = "#f8f9fa"  # Even lighter gray / off-white for specific panels
    BG_DARK = "#2c3e50"             # Dark blue-gray

    # Text colors
    TEXT_PRIMARY = "#2c3e50"        # Dark blue-gray
    TEXT_SECONDARY = "#7f8c8d"      # Medium gray
    TEXT_LIGHT = "#ecf0f1"          # Off-white

    # Border Colors
    BORDER_COLOR = "#dee2e6"        # Standard border color, light gray
    BORDER_COLOR_LIGHT = "#e0e0e0"  # Lighter border for subtle lines

    # Font sizes (in pt)
    FONT_SIZE_SMALL = 10
    FONT_SIZE_NORMAL = 14
    FONT_SIZE_LARGE = 16
    FONT_SIZE_XLARGE = 18
    FONT_SIZE_XXLARGE = 24

    # Border radius
    BORDER_RADIUS_SMALL = 3
    BORDER_RADIUS_NORMAL = 5
    BORDER_RADIUS_LARGE = 8

    # Padding
    PADDING_SMALL = 5
    PADDING_NORMAL = 10
    PADDING_LARGE = 15

    # Touch-friendly sizing
    TOUCH_MIN_WIDTH = 44
    TOUCH_MIN_HEIGHT = 44

    # Component sizing
    CONSULTATION_PANEL_MIN_WIDTH = 600
    CONSULTATION_PANEL_MIN_HEIGHT = 400

    @classmethod
    def get_base_stylesheet(cls):
        """
        Get the base stylesheet for the application.
        """
        return f"""
            /* Base styles */
            QWidget {{
                font-size: {cls.FONT_SIZE_NORMAL}pt;
                color: {cls.TEXT_PRIMARY};
            }}

            /* Button styles */
            QPushButton {{
                background-color: {cls.PRIMARY_COLOR};
                color: {cls.TEXT_LIGHT};
                border-radius: {cls.BORDER_RADIUS_NORMAL}px;
                padding: {cls.PADDING_NORMAL}px {cls.PADDING_LARGE}px;
                font-weight: bold;
                min-height: {cls.TOUCH_MIN_HEIGHT}px;
            }}

            QPushButton:hover {{
                background-color: #1a4b7c;
            }}

            QPushButton:pressed {{
                background-color: #0a2d4d;
            }}

            QPushButton:disabled {{
                background-color: #95a5a6;
                color: #ecf0f1;
            }}

            /* Input field styles */
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
                border: 1px solid #bdc3c7;
                border-radius: {cls.BORDER_RADIUS_NORMAL}px;
                padding: {cls.PADDING_NORMAL}px;
                background-color: {cls.BG_PRIMARY};
                selection-background-color: {cls.PRIMARY_COLOR};
                selection-color: {cls.TEXT_LIGHT};
                min-height: {cls.TOUCH_MIN_HEIGHT}px;
            }}

            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
                border: 2px solid {cls.PRIMARY_COLOR};
            }}

            /* Dropdown styles */
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 20px;
                border-left: 1px solid #bdc3c7;
            }}

            /* Label styles */
            QLabel {{
                color: {cls.TEXT_PRIMARY};
            }}

            QLabel[heading="true"] {{
                font-size: {cls.FONT_SIZE_XLARGE}pt;
                font-weight: bold;
                color: {cls.PRIMARY_COLOR};
            }}

            /* Frame styles */
            QFrame[frameShape="4"] {{  /* StyledPanel */
                border: 1px solid #bdc3c7;
                border-radius: {cls.BORDER_RADIUS_LARGE}px;
                background-color: {cls.BG_SECONDARY};
            }}

            /* Tab widget styles */
            QTabWidget::pane {{
                border: 1px solid #bdc3c7;
                border-radius: {cls.BORDER_RADIUS_NORMAL}px;
                background-color: {cls.BG_SECONDARY};
                top: -1px;
            }}

            QTabBar::tab {{
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-bottom: none;
                border-top-left-radius: {cls.BORDER_RADIUS_NORMAL}px;
                border-top-right-radius: {cls.BORDER_RADIUS_NORMAL}px;
                padding: {cls.PADDING_NORMAL}px {cls.PADDING_LARGE}px;
                margin-right: 2px;
                font-size: {cls.FONT_SIZE_NORMAL}pt;
            }}

            QTabBar::tab:selected {{
                background-color: {cls.PRIMARY_COLOR};
                color: {cls.TEXT_LIGHT};
                font-weight: bold;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: #d0d0d0;
            }}

            /* Table styles */
            QTableWidget {{
                border: 1px solid #bdc3c7;
                border-radius: {cls.BORDER_RADIUS_NORMAL}px;
                background-color: {cls.BG_PRIMARY};
                alternate-background-color: {cls.BG_SECONDARY};
                gridline-color: #bdc3c7;
            }}

            QTableWidget::item {{
                padding: {cls.PADDING_NORMAL}px;
            }}

            QHeaderView::section {{
                background-color: {cls.PRIMARY_COLOR};
                color: {cls.TEXT_LIGHT};
                padding: {cls.PADDING_NORMAL}px;
                border: none;
                font-weight: bold;
            }}

            /* Scrollbar styles */
            QScrollBar:vertical {{
                border: none;
                background: {cls.BG_SECONDARY};
                width: 12px;
                margin: 0px;
            }}

            QScrollBar::handle:vertical {{
                background: #95a5a6;
                min-height: 20px;
                border-radius: 6px;
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar:horizontal {{
                border: none;
                background: {cls.BG_SECONDARY};
                height: 12px;
                margin: 0px;
            }}

            QScrollBar::handle:horizontal {{
                background: #95a5a6;
                min-width: 20px;
                border-radius: 6px;
            }}

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """

    @classmethod
    def get_login_stylesheet(cls):
        """
        Get the stylesheet for the login window.
        """
        return f"""
            QWidget#loginWindow {{
                background-color: {cls.BG_PRIMARY};
            }}

            QLabel#titleLabel {{
                font-size: {cls.FONT_SIZE_XXLARGE}pt;
                font-weight: bold;
                color: {cls.PRIMARY_COLOR};
            }}

            QPushButton#loginButton {{
                background-color: {cls.SUCCESS_COLOR};
                font-size: {cls.FONT_SIZE_LARGE}pt;
                min-width: 150px;
            }}

            QLineEdit {{
                font-size: {cls.FONT_SIZE_LARGE}pt;
                padding: {cls.PADDING_LARGE}px;
            }}
        """

    @classmethod
    def get_dashboard_stylesheet(cls):
        """
        Get the stylesheet for the dashboard window.
        """
        return f"""
            QWidget#dashboardWindow {{
                background-color: {cls.BG_PRIMARY};
            }}

            QLabel#welcomeLabel {{
                font-size: {cls.FONT_SIZE_XXLARGE}pt;
                font-weight: bold;
                color: {cls.PRIMARY_COLOR};
            }}

            QPushButton#logoutButton {{
                background-color: {cls.ERROR_COLOR};
                font-size: {cls.FONT_SIZE_SMALL}pt;
                padding: {cls.PADDING_SMALL}px;
            }}

            QFrame.facultyCard {{
                border-radius: {cls.BORDER_RADIUS_LARGE}px;
                padding: {cls.PADDING_NORMAL}px;
            }}

            QFrame.facultyCard[available="true"] {{
                background-color: #e8f5e9;
                border: 2px solid {cls.SUCCESS_COLOR};
            }}

            QFrame.facultyCard[available="false"] {{
                background-color: #ffebee;
                border: 2px solid {cls.ERROR_COLOR};
            }}
        """

    @classmethod
    def get_consultation_stylesheet(cls):
        """
        Get the stylesheet for the consultation panel.
        """
        return f"""
            /* Main consultation panel */
            QTabWidget#consultation_panel {{
                min-width: {cls.CONSULTATION_PANEL_MIN_WIDTH}px;
                min-height: {cls.CONSULTATION_PANEL_MIN_HEIGHT}px;
            }}

            QTabWidget::pane {{
                border: 1px solid #bdc3c7;
                border-radius: {cls.BORDER_RADIUS_LARGE}px;
                background-color: {cls.BG_SECONDARY};
                padding: {cls.PADDING_NORMAL}px;
            }}

            QTabBar::tab {{
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-bottom: none;
                border-top-left-radius: {cls.BORDER_RADIUS_NORMAL}px;
                border-top-right-radius: {cls.BORDER_RADIUS_NORMAL}px;
                padding: {cls.PADDING_LARGE}px {cls.PADDING_LARGE}px;
                margin-right: 3px;
                font-size: {cls.FONT_SIZE_LARGE}pt;
            }}

            QTabBar::tab:selected {{
                background-color: {cls.PRIMARY_COLOR};
                color: {cls.TEXT_LIGHT};
                font-weight: bold;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: #d0d0d0;
            }}

            /* Consultation form elements */
            QLabel[heading="true"] {{
                font-size: {cls.FONT_SIZE_XLARGE}pt;
                font-weight: bold;
                color: {cls.PRIMARY_COLOR};
            }}

            QLineEdit, QTextEdit, QComboBox {{
                border: 2px solid {cls.SECONDARY_COLOR};
                border-radius: {cls.BORDER_RADIUS_NORMAL}px;
                padding: {cls.PADDING_NORMAL}px;
                background-color: white;
                font-size: {cls.FONT_SIZE_NORMAL}pt;
                min-height: {cls.TOUCH_MIN_HEIGHT}px;
            }}

            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {cls.PRIMARY_COLOR};
            }}

            /* Buttons */
            QPushButton#submitButton {{
                background-color: {cls.SUCCESS_COLOR};
                min-width: 120px;
                min-height: {cls.TOUCH_MIN_HEIGHT}px;
                font-weight: bold;
                color: white;
            }}

            QPushButton#cancelButton {{
                background-color: {cls.ERROR_COLOR};
                min-width: 120px;
                min-height: {cls.TOUCH_MIN_HEIGHT}px;
                font-weight: bold;
                color: white;
            }}

            /* Progress indicators */
            QProgressBar {{
                border: 1px solid #bdc3c7;
                border-radius: {cls.BORDER_RADIUS_SMALL}px;
                background-color: #f0f0f0;
                text-align: center;
            }}

            QProgressBar::chunk {{
                background-color: {cls.SECONDARY_COLOR};
                border-radius: {cls.BORDER_RADIUS_SMALL}px;
            }}

            /* Table styling */
            QTableWidget {{
                border: 1px solid #bdc3c7;
                border-radius: {cls.BORDER_RADIUS_NORMAL}px;
                alternate-background-color: #f9f9f9;
                gridline-color: #ddd;
            }}

            QTableWidget::item {{
                padding: {cls.PADDING_NORMAL}px;
            }}

            QHeaderView::section {{
                background-color: {cls.PRIMARY_COLOR};
                color: {cls.TEXT_LIGHT};
                padding: {cls.PADDING_NORMAL}px;
                border: none;
                font-weight: bold;
            }}
        """
