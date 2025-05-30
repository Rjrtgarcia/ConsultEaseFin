import os
import datetime
import logging

logger = logging.getLogger(__name__)

class QDialog:
    def __init__(self, parent=None):
        pass

class QMessageBox:
    Yes = 1
    No = 2
    
    @staticmethod
    def warning(parent, title, message, buttons1=None, buttons2=None):
        return 1
    
    @staticmethod
    def information(parent, title, message):
        pass
    
    @staticmethod
    def critical(parent, title, message):
        pass

class QTextCursor:
    End = 1

class QFont:
    def __init__(self, family, size):
        pass

class QPushButton:
    def __init__(self, text):
        pass
    
    def connect(self, func):
        pass

class QTextEdit:
    def __init__(self):
        pass
    
    def setReadOnly(self, readonly):
        pass
    
    def setFont(self, font):
        pass
    
    def setText(self, text):
        pass
    
    def moveCursor(self, cursor):
        pass

class QVBoxLayout:
    def __init__(self):
        pass
    
    def addWidget(self, widget):
        pass
    
    def addLayout(self, layout):
        pass

class QHBoxLayout:
    def __init__(self):
        pass
    
    def addWidget(self, widget):
        pass
    
    def addStretch(self):
        pass

def get_config():
    return {'logging.file': 'test.log'}

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

    def setWindowTitle(self, title):
        pass
        
    def resize(self, w, h):
        pass
        
    def setLayout(self, layout):
        pass
        
    def accept(self):
        pass

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
                    QMessageBox.warning(
                        self, "Clear Logs", f"Log file not found: {self.log_file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Clear Logs Error", f"Error clearing logs: {str(e)}")
            logger.error(f"Error clearing log file {self.log_file_path}: {e}")

# Test if this file has any syntax errors
if __name__ == "__main__":
    print("No syntax errors found") 