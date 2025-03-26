import sys
import subprocess
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QTreeWidget, 
                           QTreeWidgetItem, QMessageBox, QTextEdit, QSplitter,
                           QStackedWidget, QLineEdit, QFrame, QGridLayout,
                           QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtChart import (QChart, QChartView, QPieSeries, QBarSeries,
                          QBarSet, QBarCategoryAxis, QValueAxis)
import sqlite3
import signal
from datetime import datetime
from collections import Counter

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
        self.dark_mode = False  # Track dark mode state
        self.setWindowTitle("Emergency Call Center Assistant")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create navigation bar
        nav_bar = QWidget()
        nav_bar.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 15px 25px;
                font-size: 14px;
                color: #6c757d;
            }
            QPushButton:hover {
                color: #007bff;
            }
            QPushButton:checked {
                color: #007bff;
                border-bottom: 2px solid #007bff;
                font-weight: bold;
            }
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        
        # Create navigation buttons
        self.active_calls_btn = QPushButton("Active Calls")
        self.active_calls_btn.setCheckable(True)
        self.call_history_btn = QPushButton("Call History")
        self.call_history_btn.setCheckable(True)
        self.analytics_btn = QPushButton("Analytics")
        self.analytics_btn.setCheckable(True)
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setCheckable(True)
        
        # Add buttons to navigation
        nav_layout.addWidget(self.active_calls_btn)
        nav_layout.addWidget(self.call_history_btn)
        nav_layout.addWidget(self.analytics_btn)
        nav_layout.addWidget(self.settings_btn)
        nav_layout.addStretch()
        
        # Create stacked widget for different pages
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        self.active_calls_page = self.create_active_calls_page()
        self.call_history_page = self.create_call_history_page()
        self.analytics_page = self.create_analytics_page()
        self.settings_page = self.create_settings_page()  # New settings page
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.active_calls_page)
        self.stacked_widget.addWidget(self.call_history_page)
        self.stacked_widget.addWidget(self.analytics_page)
        self.stacked_widget.addWidget(self.settings_page)
        
        # Connect button signals
        self.active_calls_btn.clicked.connect(lambda: self.switch_page(0))
        self.call_history_btn.clicked.connect(lambda: self.switch_page(1))
        self.analytics_btn.clicked.connect(lambda: self.switch_page(2))
        self.settings_btn.clicked.connect(lambda: self.switch_page(3))
        
        # Add widgets to main layout
        layout.addWidget(nav_bar)
        layout.addWidget(self.stacked_widget)
        
        # Initialize thread and timers
        self.conv_thread = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_transcript)
        
        self.summary_check_timer = QTimer()
        self.summary_check_timer.timeout.connect(self.check_summary_completion)
        
        # Set initial page
        self.switch_page(0)
        
        # Load conversations when the application starts
        QTimer.singleShot(100, self.update_conversation_list)  # Use QTimer to ensure UI is fully initialized
        
    def create_active_calls_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Control buttons
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
        
        button_layout.addStretch()
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
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(top_splitter)
        
        # Bottom section - Conversation History
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        
        history_label = QLabel("Conversation History")
        history_label.setFont(QFont("Arial", 12, QFont.Bold))
        history_label.setStyleSheet("color: #2196F3; margin: 10px 0px 5px 0px;")
        history_layout.addWidget(history_label)
        
        self.active_conversation_tree = QTreeWidget()
        self.active_conversation_tree.setHeaderLabels([
            "UID", "Conversation", "Timestamp", "Summary",
            "Criticality", "isSpam", "User", "Location"
        ])
        self.active_conversation_tree.setColumnCount(8)
        self.active_conversation_tree.setAlternatingRowColors(True)
        self.active_conversation_tree.setStyleSheet("""
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
        self.active_conversation_tree.setColumnWidth(0, 100)  # uid
        self.active_conversation_tree.setColumnWidth(1, 300)  # conversation
        self.active_conversation_tree.setColumnWidth(2, 150)  # timestamp
        self.active_conversation_tree.setColumnWidth(3, 300)  # summary
        self.active_conversation_tree.setColumnWidth(4, 100)  # criticality
        self.active_conversation_tree.setColumnWidth(5, 80)   # isSpam
        self.active_conversation_tree.setColumnWidth(6, 150)  # user
        self.active_conversation_tree.setColumnWidth(7, 150)  # location
        
        history_layout.addWidget(self.active_conversation_tree)
        layout.addWidget(history_widget)
        
        # Set layout proportions
        layout.setStretchFactor(top_splitter, 2)
        layout.setStretchFactor(history_widget, 1)
        
        return page
        
    def create_call_history_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Call History")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Filters section
        filters_layout = QHBoxLayout()
        
        # Date filter
        date_filter = QLineEdit()
        date_filter.setPlaceholderText("Filter by date (YYYY-MM-DD)")
        date_filter.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        """)
        filters_layout.addWidget(date_filter)
        
        # Emergency type filter
        type_filter = QLineEdit()
        type_filter.setPlaceholderText("Filter by emergency type")
        type_filter.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        """)
        filters_layout.addWidget(type_filter)
        
        # Apply filters button
        apply_filters_btn = QPushButton("Apply Filters")
        apply_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        filters_layout.addWidget(apply_filters_btn)
        
        layout.addLayout(filters_layout)
        
        # History table
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
        
        layout.addWidget(self.conversation_tree)
        
        return page
        
    def create_analytics_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("Call Analytics Dashboard")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        layout.addWidget(title, 0, 0, 1, 2)

        # Time period filter
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)

        period_label = QLabel("Time Period:")
        period_label.setFont(QFont("Arial", 10))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Last 24 Hours", "Last Week", "Last Month", "All Time"])
        self.period_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                min-width: 150px;
            }
        """)
        self.period_combo.currentIndexChanged.connect(self.update_analytics)

        filter_layout.addWidget(period_label)
        filter_layout.addWidget(self.period_combo)
        filter_layout.addStretch()
        layout.addWidget(filter_widget, 1, 0, 1, 2)

        # Statistics cards
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setSpacing(20)

        # Total Calls Card
        self.total_calls_label = self.create_stat_card("Total Calls", "0")
        stats_layout.addWidget(self.total_calls_label)

        # Average Duration Card
        self.avg_duration_label = self.create_stat_card("Avg. Duration", "0 min")
        stats_layout.addWidget(self.avg_duration_label)

        # Emergency Rate Card
        self.emergency_rate_label = self.create_stat_card("Emergency Rate", "0%")
        stats_layout.addWidget(self.emergency_rate_label)

        # Spam Rate Card
        self.spam_rate_label = self.create_stat_card("Spam Rate", "0%")
        stats_layout.addWidget(self.spam_rate_label)

        layout.addWidget(stats_widget, 2, 0, 1, 2)

        # Charts
        # Location Distribution Chart
        self.location_chart = self.create_pie_chart("Call Distribution by Location")
        layout.addWidget(self.location_chart, 3, 0)

        # Emergency Type Distribution Chart
        self.type_chart = self.create_bar_chart("Emergency Type Distribution")
        layout.addWidget(self.type_chart, 3, 1)

        # Call Volume Timeline
        self.timeline_chart = self.create_line_chart("Call Volume Timeline")
        layout.addWidget(self.timeline_chart, 4, 0, 1, 2)

        return page

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        layout.addWidget(title)

        # Settings Container
        settings_container = QWidget()
        settings_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)

        # Dark Mode Section
        dark_mode_widget = QWidget()
        dark_mode_layout = QHBoxLayout(dark_mode_widget)
        dark_mode_layout.setContentsMargins(0, 0, 0, 0)

        dark_mode_label = QLabel("Dark Mode")
        dark_mode_label.setFont(QFont("Arial", 12))
        dark_mode_layout.addWidget(dark_mode_label)

        self.dark_mode_toggle = QPushButton()
        self.dark_mode_toggle.setCheckable(True)
        self.dark_mode_toggle.setChecked(self.dark_mode)
        self.dark_mode_toggle.setFixedSize(50, 25)
        self.dark_mode_toggle.setStyleSheet("""
            QPushButton {
                border: 2px solid #999;
                border-radius: 12px;
                background-color: #fff;
            }
            QPushButton:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
            QPushButton::hover {
                border-color: #666;
            }
            QPushButton::checked:hover {
                border-color: #1976D2;
            }
        """)
        self.dark_mode_toggle.clicked.connect(self.toggle_dark_mode)
        dark_mode_layout.addWidget(self.dark_mode_toggle)
        dark_mode_layout.addStretch()

        settings_layout.addWidget(dark_mode_widget)
        settings_layout.addStretch()
        layout.addWidget(settings_container)
        layout.addStretch()

        return page

    def create_stat_card(self, title, value):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setStyleSheet("color: #666;")
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Bold))
        value_label.setStyleSheet("color: #2196F3;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card

    def create_pie_chart(self, title):
        series = QPieSeries()
        
        # Sample data - will be updated with real data
        series.append("Dubai", 30)
        series.append("Abu Dhabi", 20)
        series.append("Sharjah", 15)
        series.append("Other", 35)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignRight)
        
        chartview = QChartView(chart)
        chartview.setRenderHint(QPainter.Antialiasing)
        
        return chartview

    def create_bar_chart(self, title):
        series = QBarSeries()
        
        # Sample data - will be updated with real data
        bar_set = QBarSet("Emergency Types")
        bar_set.append([40, 30, 20, 10])  # Fire, Medical, Crime, Other
        series.append(bar_set)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        categories = ["Fire", "Medical", "Crime", "Other"]
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setRange(0, 50)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        chart.legend().setVisible(False)
        
        chartview = QChartView(chart)
        chartview.setRenderHint(QPainter.Antialiasing)
        
        return chartview

    def create_line_chart(self, title):
        chart = QChart()
        chart.setTitle(title)
        
        # This will be implemented with real data
        chartview = QChartView(chart)
        chartview.setRenderHint(QPainter.Antialiasing)
        
        return chartview

    def update_analytics(self):
        try:
            period = self.period_combo.currentText()
            
            # Fetch data based on selected time period
            conn = sqlite3.connect("conversation.db")
            c = conn.cursor()
            
            # Query based on time period
            if period == "Last 24 Hours":
                time_filter = "datetime(timestamp) >= datetime('now', '-1 day')"
            elif period == "Last Week":
                time_filter = "datetime(timestamp) >= datetime('now', '-7 days')"
            elif period == "Last Month":
                time_filter = "datetime(timestamp) >= datetime('now', '-30 days')"
            else:  # All Time
                time_filter = "1=1"
            
            # Get total calls
            c.execute(f"SELECT COUNT(*) FROM conversations WHERE {time_filter}")
            total_calls = c.fetchone()[0]
            
            # Get spam rate
            c.execute(f"SELECT COUNT(*) FROM conversations WHERE isSpam = 1 AND {time_filter}")
            spam_calls = c.fetchone()[0]
            spam_rate = (spam_calls / total_calls * 100) if total_calls > 0 else 0
            
            # Get emergency distribution
            c.execute(f"SELECT criticality FROM conversations WHERE {time_filter}")
            criticalities = [row[0] for row in c.fetchall()]
            high_priority = sum(1 for c in criticalities if c.lower() == 'high')
            emergency_rate = (high_priority / total_calls * 100) if total_calls > 0 else 0
            
            # Get location distribution
            c.execute(f"SELECT location FROM conversations WHERE {time_filter}")
            locations = [row[0] for row in c.fetchall()]
            location_counts = Counter(locations)
            
            # Update statistics cards
            self._update_stat_card(self.total_calls_label, str(total_calls))
            self._update_stat_card(self.spam_rate_label, f"{spam_rate:.1f}%")
            self._update_stat_card(self.emergency_rate_label, f"{emergency_rate:.1f}%")
            
            # Update pie chart
            self._update_location_chart(location_counts)
            
            conn.close()
            
        except Exception as e:
            print(f"Error updating analytics: {e}")

    def _update_stat_card(self, card, value):
        # Update the value label in the stat card
        value_label = card.findChild(QLabel, "", Qt.FindChildrenRecursively)
        if value_label:
            value_label.setText(value)

    def _update_location_chart(self, location_counts):
        # Update the location pie chart with new data
        series = QPieSeries()
        
        # Sort locations by count and take top 5
        top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        other_count = sum(count for loc, count in location_counts.items() 
                         if (loc, count) not in top_locations)
        
        # Add top locations to pie chart
        for location, count in top_locations:
            series.append(location, count)
        
        # Add "Other" if there are more locations
        if other_count > 0:
            series.append("Other", other_count)
        
        # Update the chart
        self.location_chart.chart().removeAllSeries()
        self.location_chart.chart().addSeries(series)
        
    def switch_page(self, index):
        # Update button states
        buttons = [self.active_calls_btn, self.call_history_btn, 
                  self.analytics_btn, self.settings_btn]
        for i, btn in enumerate(buttons):
            btn.setChecked(i == index)
        
        # Switch to selected page
        self.stacked_widget.setCurrentIndex(index)

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
            
            # Fetch all conversations ordered by timestamp
            c.execute("SELECT * FROM conversations ORDER BY timestamp DESC")
            rows = c.fetchall()
            
            # Print detailed debug information
            print(f"\nFetched {len(rows)} conversations from database")
            if len(rows) == 0:
                print("Warning: No conversations found in database")
            else:
                print("\nFirst conversation data:")
                for idx, value in enumerate(rows[0]):
                    print(f"Column {idx}: {value}")
                print(f"\nLatest conversation timestamp: {rows[0][2]}")
            
            conn.close()
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
        self.active_conversation_tree.clear()  # Clear both trees
        conversations = self.fetch_conversations()
        print(f"Fetched {len(conversations)} conversations from database")
        
        # Store the current scroll positions
        current_scroll = self.conversation_tree.verticalScrollBar().value()
        active_scroll = self.active_conversation_tree.verticalScrollBar().value()
        
        for idx, convo in enumerate(conversations):
            try:
                # Create items for both trees
                history_item = QTreeWidgetItem(self.conversation_tree)
                active_item = QTreeWidgetItem(self.active_conversation_tree)
                
                # Map database columns to tree columns
                tree_values = [
                    str(convo[0]),  # UID
                    str(convo[1])[:100] + "..." if len(str(convo[1])) > 100 else str(convo[1]),  # Truncate conversation
                    str(convo[2]),  # Timestamp
                    str(convo[3]),  # Summary
                    str(convo[4]),  # Criticality
                    "Yes" if convo[5] == 1 else "No",  # isSpam
                    str(convo[6]),  # User
                    str(convo[7])   # Location
                ]
                
                # Set values for both trees
                for col, value in enumerate(tree_values):
                    history_item.setText(col, value)
                    active_item.setText(col, value)
                
                print(f"Added conversation {idx + 1}: {tree_values[0]} - {tree_values[6]} - {tree_values[7]}")
            except Exception as e:
                print(f"Error adding conversation {idx}: {str(e)}")
        
        # Restore scroll positions
        self.conversation_tree.verticalScrollBar().setValue(current_scroll)
        self.active_conversation_tree.verticalScrollBar().setValue(active_scroll)
        
        # Ensure the latest conversation is visible in both trees
        if conversations:
            self.conversation_tree.scrollToTop()
            self.active_conversation_tree.scrollToTop()
            print(f"Successfully added {len(conversations)} conversations to both trees")
        else:
            print("No conversations found in database")
        
        # Force the trees to update their display
        self.conversation_tree.update()
        self.active_conversation_tree.update()
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

    def toggle_dark_mode(self):
        self.dark_mode = self.dark_mode_toggle.isChecked()
        self.apply_theme()

    def apply_theme(self):
        if self.dark_mode:
            # Dark theme styles
            app_style = """
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
                QTreeWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                }
                QTreeWidget::item {
                    color: #ffffff;
                }
                QTreeWidget::item:selected {
                    background-color: #3d3d3d;
                }
                QTreeWidget::item:alternate {
                    background-color: #363636;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #2196F3;
                    color: white;
                    border: 1px solid #1976D2;
                }
                QTextEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                }
                QLineEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                }
                QComboBox {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    selection-background-color: #3d3d3d;
                }
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                }
            """
            self.setStyleSheet(app_style)
            
            # Apply dark theme to conversation trees
            tree_style = """
                QTreeWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                }
                QTreeWidget::item {
                    color: #ffffff;
                }
                QTreeWidget::item:selected {
                    background-color: #3d3d3d;
                }
                QTreeWidget::item:alternate {
                    background-color: #363636;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #2196F3;
                    color: white;
                    border: 1px solid #1976D2;
                }
            """
            self.conversation_tree.setStyleSheet(tree_style)
            self.active_conversation_tree.setStyleSheet(tree_style)
            
            # Update navigation bar style for dark mode
            nav_bar = self.findChild(QWidget, "", Qt.FindDirectChildrenOnly)
            nav_bar_style = """
                QWidget {
                    background-color: #2d2d2d;
                    border-bottom: 1px solid #3d3d3d;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    padding: 15px 25px;
                    font-size: 14px;
                    color: #999999;
                }
                QPushButton:hover {
                    color: #2196F3;
                }
                QPushButton:checked {
                    color: #2196F3;
                    border-bottom: 2px solid #2196F3;
                    font-weight: bold;
                }
            """
            nav_bar.setStyleSheet(nav_bar_style)
            
            # Update transcript area
            transcript_style = """
                QTextEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    padding: 10px;
                    font-family: Arial;
                    font-size: 12px;
                }
            """
            self.transcript_area.setStyleSheet(transcript_style)
            
            # Update chart colors for analytics
            if hasattr(self, 'location_chart'):
                self.location_chart.chart().setBackgroundBrush(Qt.darkGray)
                self.location_chart.chart().setTitleBrush(Qt.white)
                self.location_chart.setStyleSheet("background-color: #2d2d2d;")
            
            if hasattr(self, 'type_chart'):
                self.type_chart.chart().setBackgroundBrush(Qt.darkGray)
                self.type_chart.chart().setTitleBrush(Qt.white)
                self.type_chart.setStyleSheet("background-color: #2d2d2d;")
            
            if hasattr(self, 'timeline_chart'):
                self.timeline_chart.chart().setBackgroundBrush(Qt.darkGray)
                self.timeline_chart.chart().setTitleBrush(Qt.white)
                self.timeline_chart.setStyleSheet("background-color: #2d2d2d;")
            
            # Update stat cards for dark mode
            stat_card_style = """
                QFrame {
                    background-color: #2d2d2d;
                    border-radius: 8px;
                    padding: 15px;
                    border: 1px solid #3d3d3d;
                }
                QLabel {
                    color: #ffffff;
                }
                QLabel[value="true"] {
                    color: #2196F3;
                }
            """
            for card in [self.total_calls_label, self.avg_duration_label, 
                        self.emergency_rate_label, self.spam_rate_label]:
                card.setStyleSheet(stat_card_style)
                # Update value label color
                value_label = card.findChild(QLabel, "", Qt.FindChildrenRecursively)
                if value_label:
                    value_label.setProperty("value", True)
                    value_label.setStyleSheet("color: #2196F3;")
                # Update title label color
                title_label = card.layout().itemAt(0).widget()
                if title_label:
                    title_label.setStyleSheet("color: #999999;")
        else:
            # Light theme styles
            self.setStyleSheet("")  # Reset to default light theme
            
            # Reset conversation trees style
            tree_style = """
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
            """
            self.conversation_tree.setStyleSheet(tree_style)
            self.active_conversation_tree.setStyleSheet(tree_style)
            
            # Reset navigation bar style
            nav_bar = self.findChild(QWidget, "", Qt.FindDirectChildrenOnly)
            nav_bar_style = """
                QWidget {
                    background-color: #f8f9fa;
                    border-bottom: 1px solid #dee2e6;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    padding: 15px 25px;
                    font-size: 14px;
                    color: #6c757d;
                }
                QPushButton:hover {
                    color: #007bff;
                }
                QPushButton:checked {
                    color: #007bff;
                    border-bottom: 2px solid #007bff;
                    font-weight: bold;
                }
            """
            nav_bar.setStyleSheet(nav_bar_style)
            
            # Reset transcript area style
            transcript_style = """
                QTextEdit {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 10px;
                    font-family: Arial;
                    font-size: 12px;
                }
            """
            self.transcript_area.setStyleSheet(transcript_style)
            
            # Reset chart colors
            if hasattr(self, 'location_chart'):
                self.location_chart.chart().setBackgroundBrush(Qt.white)
                self.location_chart.chart().setTitleBrush(Qt.black)
                self.location_chart.setStyleSheet("")
            
            if hasattr(self, 'type_chart'):
                self.type_chart.chart().setBackgroundBrush(Qt.white)
                self.type_chart.chart().setTitleBrush(Qt.black)
                self.type_chart.setStyleSheet("")
            
            if hasattr(self, 'timeline_chart'):
                self.timeline_chart.chart().setBackgroundBrush(Qt.white)
                self.timeline_chart.chart().setTitleBrush(Qt.black)
                self.timeline_chart.setStyleSheet("")
            
            # Reset stat cards to light mode
            stat_card_style = """
                QFrame {
                    background-color: white;
                    border-radius: 8px;
                    padding: 15px;
                    border: 1px solid #e0e0e0;
                }
                QLabel {
                    color: #666666;
                }
                QLabel[value="true"] {
                    color: #2196F3;
                }
            """
            for card in [self.total_calls_label, self.avg_duration_label, 
                        self.emergency_rate_label, self.spam_rate_label]:
                card.setStyleSheet(stat_card_style)
                # Update value label color
                value_label = card.findChild(QLabel, "", Qt.FindChildrenRecursively)
                if value_label:
                    value_label.setProperty("value", True)
                    value_label.setStyleSheet("color: #2196F3;")
                # Update title label color
                title_label = card.layout().itemAt(0).widget()
                if title_label:
                    title_label.setStyleSheet("color: #666666;")
        
        # Preserve specific button styles
        self.update_component_styles()

    def update_component_styles(self):
        # Update navigation bar style
        nav_bar_style = """
            QWidget {
                background-color: """ + ("#2d2d2d" if self.dark_mode else "#f8f9fa") + """;
                border-bottom: 1px solid """ + ("#3d3d3d" if self.dark_mode else "#dee2e6") + """;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 15px 25px;
                font-size: 14px;
                color: """ + ("#999" if self.dark_mode else "#6c757d") + """;
            }
            QPushButton:hover {
                color: #007bff;
            }
            QPushButton:checked {
                color: #007bff;
                border-bottom: 2px solid #007bff;
                font-weight: bold;
            }
        """
        self.findChild(QWidget, "", Qt.FindDirectChildrenOnly).setStyleSheet(nav_bar_style)

        # Update start button style
        start_button_style = """
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
        """
        self.start_button.setStyleSheet(start_button_style)

        # Update end button style
        end_button_style = """
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
        """
        self.end_button.setStyleSheet(end_button_style)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VoiceAnalysisUI()
    window.show()
    sys.exit(app.exec_())