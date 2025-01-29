import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QTreeWidget, 
                           QTreeWidgetItem, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import sqlite3
import asyncio

class ConversationThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            asyncio.run(self.main())
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    async def main(self):
        # Placeholder for your async main function
        await asyncio.sleep(1)  # Simulate some async work

class VoiceAnalysisUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Call Analysis UI")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("Voice Call Analysis System")
        header_label.setFont(QFont("Arial", 20))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Conversation")
        self.start_button.setStyleSheet("background-color: green; color: white;")
        self.start_button.clicked.connect(self.start_conversation_thread)
        button_layout.addWidget(self.start_button)
        
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("background-color: red; color: white;")
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)
        
        layout.addLayout(button_layout)
        
        # Conversation TreeWidget
        self.conversation_tree = QTreeWidget()
        columns = ["uid", "conversation", "timestamp", "summary", 
                  "criticality", "isSpam", "user", "location"]
        self.conversation_tree.setHeaderLabels(columns)
        self.conversation_tree.setColumnCount(len(columns))
        
        # Set equal column widths
        for i in range(len(columns)):
            self.conversation_tree.setColumnWidth(i, 100)
        
        layout.addWidget(self.conversation_tree)
        
        # Initialize thread
        self.conv_thread = None
        
        # Initial load
        self.update_conversation_list()

    def fetch_conversations(self):
        conn = sqlite3.connect("conversation.db")
        c = conn.cursor()
        c.execute("SELECT * FROM conversations")
        rows = c.fetchall()
        conn.close()
        return rows

    def update_conversation_list(self):
        self.conversation_tree.clear()
        conversations = self.fetch_conversations()
        for convo in conversations:
            item = QTreeWidgetItem(self.conversation_tree)
            for i, value in enumerate(convo):
                item.setText(i, str(value))

    def start_conversation_thread(self):
        self.start_button.setEnabled(False)
        self.conv_thread = ConversationThread()
        self.conv_thread.finished.connect(self.on_conversation_finished)
        self.conv_thread.error.connect(self.on_conversation_error)
        self.conv_thread.start()

    def on_conversation_finished(self):
        self.start_button.setEnabled(True)
        self.update_conversation_list()
        QMessageBox.information(self, "Info", "Conversation has ended.")

    def on_conversation_error(self, error_msg):
        self.start_button.setEnabled(True)
        QMessageBox.critical(self, "Error", error_msg)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VoiceAnalysisUI()
    window.show()
    sys.exit(app.exec_())