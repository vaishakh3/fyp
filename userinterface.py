import sys
import subprocess
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QTreeWidget, 
                           QTreeWidgetItem, QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import sqlite3
import signal

class ConversationThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.process = None

    def run(self):
        try:
            if os.path.exists("summary_complete.txt"):
                os.remove("summary_complete.txt")
                
            self.process = subprocess.Popen([sys.executable, 'main.py'], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode != 0 and not self.process.returncode == -signal.SIGTERM:
                self.error.emit(f"Error in main.py: {stderr.decode()}")
            else:
                self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def stop_conversation(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            
class VoiceAnalysisUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Call Analysis UI")
        self.setGeometry(100, 100, 1000, 800)
        
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
        
        self.end_button = QPushButton("End Call")
        self.end_button.setStyleSheet("background-color: orange; color: white;")
        self.end_button.clicked.connect(self.end_conversation)
        self.end_button.setEnabled(False)
        button_layout.addWidget(self.end_button)
        
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("background-color: red; color: white;")
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)
        
        layout.addLayout(button_layout)
        
        # Live Transcript Area
        transcript_label = QLabel("Live Transcript")
        transcript_label.setFont(QFont("Arial", 12))
        layout.addWidget(transcript_label)
        
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setMinimumHeight(200)
        self.transcript_area.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 5px;
                font-family: Arial;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.transcript_area)
        
        # History Label
        history_label = QLabel("Conversation History")
        history_label.setFont(QFont("Arial", 12))
        layout.addWidget(history_label)
        
        # Conversation TreeWidget
        self.conversation_tree = QTreeWidget()
        self.conversation_tree.setHeaderLabels([
            "UID", "Conversation", "Timestamp", "Summary",
            "Criticality", "isSpam", "User", "Location"
        ])
        self.conversation_tree.setColumnCount(8)
        
        # Set column widths
        self.conversation_tree.setColumnWidth(0, 100)  # uid
        self.conversation_tree.setColumnWidth(1, 200)  # conversation
        self.conversation_tree.setColumnWidth(2, 100)  # timestamp
        self.conversation_tree.setColumnWidth(3, 200)  # summary
        self.conversation_tree.setColumnWidth(4, 80)   # criticality
        self.conversation_tree.setColumnWidth(5, 60)   # isSpam
        self.conversation_tree.setColumnWidth(6, 100)  # user
        self.conversation_tree.setColumnWidth(7, 100)  # location
        
        layout.addWidget(self.conversation_tree)
        
        # Initialize thread and timers
        self.conv_thread = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_transcript)
        
        self.summary_check_timer = QTimer()
        self.summary_check_timer.timeout.connect(self.check_summary_completion)
        
        # Initial load
        self.update_conversation_list()

    def fetch_conversations(self):
        try:
            conn = sqlite3.connect("conversation.db")
            c = conn.cursor()
            c.execute("SELECT * FROM conversations ORDER BY timestamp DESC")
            rows = c.fetchall()
            conn.close()
            print(f"Fetched {len(rows)} conversations from database")
            return rows
        except Exception as e:
            print(f"Error fetching conversations: {e}")
            return []

    def update_conversation_list(self):
        self.conversation_tree.clear()
        conversations = self.fetch_conversations()
        for convo in conversations:
            item = QTreeWidgetItem(self.conversation_tree)
            for i, value in enumerate(convo):
                # Convert SQLite INTEGER to boolean string for isSpam column
                if i == 5:  # isSpam column
                    value = "Yes" if value == 1 else "No"
                item.setText(i, str(value))

    def update_transcript(self):
        try:
            with open("conversations.txt", "r") as f:
                transcript = f.read()
                self.transcript_area.setText(transcript)
                self.transcript_area.moveCursor(self.transcript_area.textCursor().End)
        except FileNotFoundError:
            pass

    def start_conversation_thread(self):
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(True)
        self.transcript_area.clear()
        self.conv_thread = ConversationThread()
        self.conv_thread.finished.connect(self.on_conversation_finished)
        self.conv_thread.error.connect(self.on_conversation_error)
        self.conv_thread.start()
        
        self.update_timer.start(1000)

    def end_conversation(self):
        if self.conv_thread and self.conv_thread.isRunning():
            self.conv_thread.stop_conversation()
            self.end_button.setEnabled(False)
            QMessageBox.information(self, "Info", "Ending conversation and generating summary...")
            self.summary_check_timer.start(1000)

    def check_summary_completion(self):
        if os.path.exists("summary_complete.txt"):
            self.summary_check_timer.stop()
            try:
                with open("summary_complete.txt", "r") as f:
                    conversation_id = f.read().strip()
                os.remove("summary_complete.txt")
                self.update_conversation_list()
                self.on_conversation_finished()
            except Exception as e:
                print(f"Error checking summary completion: {e}")

    def on_conversation_finished(self):
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(False)
        self.update_timer.stop()
        self.summary_check_timer.stop()
        QMessageBox.information(self, "Info", "Conversation has ended and summary has been generated.")

    def on_conversation_error(self, error_msg):
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(False)
        self.update_timer.stop()
        self.summary_check_timer.stop()
        QMessageBox.critical(self, "Error", error_msg)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VoiceAnalysisUI()
    window.show()
    sys.exit(app.exec_())