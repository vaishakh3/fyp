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
        self.setGeometry(100, 100, 1000, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("Call Details")
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