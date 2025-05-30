from PyQt5.QtWidgets import QMessageBox
import logging

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    A simple notification manager for displaying messages to the user.
    """

    @staticmethod
    def get_standardized_type(message_type: str) -> str:
        """
        Standardize message type strings.
        """
        msg_type_lower = message_type.lower()
        if msg_type_lower in ["success", "ok", "done"]:
            return "success"
        elif msg_type_lower in ["error", "fail", "problem"]:
            return "error"
        elif msg_type_lower in ["warning", "warn", "caution"]:
            return "warning"
        else:  # "info", "information", "note", or any other
            return "info"

    @staticmethod
    def show_message(parent, title: str, message: str, message_type: str = "info"):
        """
        Show a notification message.

        Args:
            parent: The parent widget for the message box.
            title (str): The title of the message box.
            message (str): The message content.
            message_type (str): Type of message ('success', 'error', 'warning', 'info').
        """
        std_type = NotificationManager.get_standardized_type(message_type)
        logger.debug(
            f"Showing notification: Title='{title}', Type='{std_type}', Message='{message}'")

        if std_type == "success":
            QMessageBox.information(parent, title, message)
        elif std_type == "error":
            QMessageBox.critical(parent, title, message)  # Use critical for errors
        elif std_type == "warning":
            QMessageBox.warning(parent, title, message)
        else:  # info
            QMessageBox.information(parent, title, message)


# Example usage (can be removed or kept for testing)
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
    import sys

    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Notification Test")
    button = QPushButton("Show Info Notification", window)
    button.clicked.connect(
        lambda: NotificationManager.show_message(
            window,
            "Info",
            "This is an info message.",
            "info"))

    button_err = QPushButton("Show Error Notification", window)
    button_err.move(0, 50)
    button_err.clicked.connect(
        lambda: NotificationManager.show_message(
            window,
            "Error!",
            "This is an error message.",
            "error"))

    window.setGeometry(100, 100, 300, 200)
    window.show()
    sys.exit(app.exec_())
