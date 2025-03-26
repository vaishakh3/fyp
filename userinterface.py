import sys
import subprocess
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QTreeWidget, 
                           QTreeWidgetItem, QMessageBox, QTextEdit, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
import sqlite3
import signal
from datetime import datetime

class ConversationThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.process = None
        self.termination_requested = False
        self.max_wait_time = 30  # Maximum time to wait for summary completion in seconds
        self.wait_start_time = None

    def run(self):
        try:
            if os.path.exists("summary_complete.txt"):
                os.remove("summary_complete.txt")
            if os.path.exists("end_call.txt"):
                os.remove("end_call.txt")
                
            self.process = subprocess.Popen([sys.executable, 'main.py'], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)
            
            # Read output in real-time
            while True:
                if self.process.poll() is not None:
                    break
                    
                output = self.process.stdout.readline()
                if output:
                    print(output.strip())
                    
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode != 0 and not self.process.returncode == -signal.SIGTERM:
                print(f"Process error output: {stderr}")
                self.error.emit(f"Error in main.py: {stderr}")
            else:
                print("Process completed successfully")
                self.finished.emit()
        except Exception as e:
            print(f"Thread error: {str(e)}")
            self.error.emit(str(e))

    def stop_conversation(self):
        if self.process:
            print("Stopping conversation...")
            # Create end call signal first
            with open("end_call.txt", "w") as f:
                f.write("1")
            print("Created end_call.txt signal")
            
            # Process the conversation immediately
            try:
                print("Processing conversation immediately...")
                with open("conversations.txt", "r") as f:
                    conversations = f.read()
                    print("Final conversation length:", len(conversations))
                
                if conversations.strip():
                    # Import and call get_conversation directly
                    from main import get_conversation
                    get_conversation()
                    print("Successfully processed conversation")
                else:
                    print("Warning: Empty conversation, skipping processing")
            except Exception as e:
                print(f"Error processing conversation: {e}")
            
            # Force stop the process after processing
            QTimer.singleShot(1000, self.force_stop_if_needed)
            
    def force_stop_if_needed(self):
        if self.process and self.process.poll() is None:
            print("Process still running, forcing termination...")
            try:
                self.process.terminate()
                # Give it a moment to terminate gracefully
                QTimer.singleShot(1000, self.kill_if_needed)
            except Exception as e:
                print(f"Error terminating process: {e}")
                self.kill_if_needed()
    
    def kill_if_needed(self):
        if self.process and self.process.poll() is None:
            print("Process still running after terminate, killing...")
            try:
                self.process.kill()
            except Exception as e:
                print(f"Error killing process: {e}")
            finally:
                self.finished.emit()

class VoiceAnalysisUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emergency Call Center Assistant for Disaster Response")
        self.setGeometry(100, 100, 1400, 900)  # Made window larger for better layout
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("Emergency Call Center Assistant")
        header_label.setFont(QFont("Arial", 20, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Conversation")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_button.clicked.connect(self.start_conversation_thread)
        button_layout.addWidget(self.start_button)
        
        self.end_button = QPushButton("End Call")
        self.end_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.end_button.clicked.connect(self.end_conversation)
        self.end_button.setEnabled(False)
        button_layout.addWidget(self.end_button)
        
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)
        
        layout.addLayout(button_layout)
        
        # Create top section splitter (Transcript and Map)
        top_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Transcript
        transcript_widget = QWidget()
        transcript_layout = QVBoxLayout(transcript_widget)
        
        transcript_label = QLabel("Live Transcript")
        transcript_label.setFont(QFont("Arial", 12, QFont.Bold))
        transcript_label.setStyleSheet("color: #2196F3; margin-bottom: 5px;")
        transcript_layout.addWidget(transcript_label)
        
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setMinimumHeight(300)
        self.transcript_area.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                font-family: Arial;
                font-size: 12px;
            }
        """)
        transcript_layout.addWidget(self.transcript_area)
        
        # Right side - Map
        map_widget = QWidget()
        map_layout = QVBoxLayout(map_widget)
        
        map_label = QLabel("Location Map")
        map_label.setFont(QFont("Arial", 12, QFont.Bold))
        map_label.setStyleSheet("color: #2196F3; margin-bottom: 5px;")
        map_layout.addWidget(map_label)
        
        self.map_view = QWebEngineView()
        self.map_view.setMinimumWidth(500)
        self.map_view.setMinimumHeight(300)
        self.map_view.setUrl(QUrl('https://www.openstreetmap.org'))
        map_layout.addWidget(self.map_view)
        
        # Add transcript and map to top splitter
        top_splitter.addWidget(transcript_widget)
        top_splitter.addWidget(map_widget)
        top_splitter.setStretchFactor(0, 1)  # Give transcript more space
        top_splitter.setStretchFactor(1, 1)  # Give map equal space
        
        # Add top splitter to main layout
        layout.addWidget(top_splitter)
        
        # Bottom section - Conversation History
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        
        history_label = QLabel("Conversation History")
        history_label.setFont(QFont("Arial", 12, QFont.Bold))
        history_label.setStyleSheet("color: #2196F3; margin: 10px 0px 5px 0px;")
        history_layout.addWidget(history_label)
        
        self.conversation_tree = QTreeWidget()
        self.conversation_tree.setHeaderLabels([
            "UID", "Conversation", "Timestamp", "Summary",
            "Criticality", "isSpam", "User", "Location"
        ])
        self.conversation_tree.setColumnCount(8)
        self.conversation_tree.setAlternatingRowColors(True)
        self.conversation_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTreeWidget::item:alternate {
                background-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 5px;
                border: 1px solid #1976D2;
            }
        """)
        
        # Set column widths
        self.conversation_tree.setColumnWidth(0, 100)  # uid
        self.conversation_tree.setColumnWidth(1, 300)  # conversation
        self.conversation_tree.setColumnWidth(2, 150)  # timestamp
        self.conversation_tree.setColumnWidth(3, 300)  # summary
        self.conversation_tree.setColumnWidth(4, 100)  # criticality
        self.conversation_tree.setColumnWidth(5, 80)   # isSpam
        self.conversation_tree.setColumnWidth(6, 150)  # user
        self.conversation_tree.setColumnWidth(7, 150)  # location
        
        history_layout.addWidget(self.conversation_tree)
        layout.addWidget(history_widget)
        
        # Set layout proportions
        layout.setStretchFactor(top_splitter, 2)  # Give top section more space
        layout.setStretchFactor(history_widget, 1)  # Give history less space
        
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
            print("\nAttempting to fetch conversations from database...")
            conn = sqlite3.connect("conversation.db")
            c = conn.cursor()
            
            # First check if table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            if not c.fetchone():
                print("Table 'conversations' does not exist!")
                return []
            
            # Check table structure
            c.execute("PRAGMA table_info(conversations)")
            columns = c.fetchall()
            print("Table structure:", columns)
            
            # Get the count of records before fetching
            c.execute("SELECT COUNT(*) FROM conversations")
            count = c.fetchone()[0]
            print(f"Total records in database: {count}")
            
            c.execute("SELECT * FROM conversations ORDER BY timestamp DESC")
            rows = c.fetchall()
            conn.close()
            
            print(f"Fetched {len(rows)} conversations from database")
            if len(rows) == 0:
                print("Warning: No conversations found in database")
            else:
                print("First conversation data:", rows[0])  # Print first row as example
                print("Latest conversation timestamp:", rows[0][2])  # Print timestamp of latest conversation
            return rows
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            return []
        except Exception as e:
            print(f"Error fetching conversations: {e}")
            return []

    def update_conversation_list(self):
        print("\nUpdating conversation list...")
        self.conversation_tree.clear()
        conversations = self.fetch_conversations()
        print(f"Updating conversation list with {len(conversations)} conversations")
        
        # Store the current scroll position
        current_scroll = self.conversation_tree.verticalScrollBar().value()
        
        for convo in conversations:
            item = QTreeWidgetItem(self.conversation_tree)
            for i, value in enumerate(convo):
                # Convert SQLite INTEGER to boolean string for isSpam column
                if i == 5:  # isSpam column
                    value = "Yes" if value == 1 else "No"
                item.setText(i, str(value))
            print(f"Added conversation: {convo[0][:8]}... (UID)")  # Print first 8 chars of UID
        
        # Restore scroll position
        self.conversation_tree.verticalScrollBar().setValue(current_scroll)
        
        # Ensure the latest conversation is visible
        if conversations:
            self.conversation_tree.scrollToTop()
            print("Scrolled to top to show latest conversation")
        print("Conversation list update complete")

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

    def update_map_location(self, location):
        if location and location.lower() != "unknown":
            formatted_location = location.replace(' ', '+')
            self.map_view.setUrl(
                QUrl(f'https://www.openstreetmap.org/search?query={formatted_location}')
            )
            print(f"Updated map to show location: {location}")
        else:
            # Reset to default view if location is unknown
            self.map_view.setUrl(QUrl('https://www.openstreetmap.org'))
            print("Reset map to default view (location unknown)")

    def check_summary_completion(self):
        if os.path.exists("summary_complete.txt"):
            print("Summary completion detected, reading conversation ID...")
            try:
                with open("summary_complete.txt", "r") as f:
                    conversation_id = f.read().strip()
                print(f"Found conversation ID: {conversation_id}")
                
                # Verify the conversation exists in the database
                conn = sqlite3.connect("conversation.db")
                c = conn.cursor()
                c.execute("SELECT * FROM conversations WHERE uid = ?", (conversation_id,))
                result = c.fetchone()
                conn.close()
                
                if result:
                    print(f"Verified conversation {conversation_id} exists in database")
                    # Update map with location from the conversation
                    location = result[7]  # Location is the 8th column (index 7)
                    self.update_map_location(location)
                else:
                    print(f"Warning: Conversation {conversation_id} not found in database")
                
                os.remove("summary_complete.txt")
                print("Removed summary_complete.txt")
                
                # Update the conversation list immediately
                print("Updating conversation list...")
                self.update_conversation_list()
                
                # Scroll to the top to show the latest conversation
                self.conversation_tree.scrollToTop()
                print("Scrolled to top")
                
                # Stop the summary check timer
                self.summary_check_timer.stop()
                print("Stopped summary check timer")
                
                # Enable the start button and disable the end button
                self.start_button.setEnabled(True)
                self.end_button.setEnabled(False)
                print("Updated button states")
                
                # Stop the transcript update timer
                self.update_timer.stop()
                print("Stopped transcript update timer")
                
                print("Conversation processing complete")
                QMessageBox.information(self, "Success", "Conversation has been processed and added to history.")
                
            except Exception as e:
                print(f"Error checking summary completion: {e}")
                QMessageBox.warning(self, "Warning", f"Error updating conversation list: {str(e)}")

    def on_conversation_finished(self):
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(False)
        self.update_timer.stop()
        self.summary_check_timer.stop()
        print("Conversation finished, performing final update...")
        # Update the conversation list one final time to ensure we have the latest data
        self.update_conversation_list()
        QMessageBox.information(self, "Info", "Conversation has ended and summary has been generated.")

    def on_conversation_error(self, error_msg):
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(False)
        self.update_timer.stop()
        self.summary_check_timer.stop()
        QMessageBox.critical(self, "Error", error_msg)

    def end_conversation(self):
        if self.conv_thread and self.conv_thread.isRunning():
            print("Ending conversation...")
            # Stop the conversation thread
            self.conv_thread.stop_conversation()
            self.end_button.setEnabled(False)
            QMessageBox.information(self, "Info", "Ending conversation and generating summary...\nPlease wait while the conversation is processed.")
            
            # Start checking for summary completion with a shorter interval
            self.summary_check_timer.start(500)  # Check every 500ms instead of 1000ms

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VoiceAnalysisUI()
    window.show()
    sys.exit(app.exec_())