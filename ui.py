import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *


class EmergencyDashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Emergency Dashboard")
        self.setGeometry(100, 100, 2400, 1200)

        main_layout = QVBoxLayout()

        top_bar = QHBoxLayout()
        dashboard_btn = self.create_top_button("Dashboard")
        call_history_btn = self.create_top_button("Call History")
        analytics_btn = self.create_top_button("Analytics")
        dispatch_btn = self.create_top_button("Dispatch")

        top_bar.addWidget(dashboard_btn)
        top_bar.addWidget(call_history_btn)
        top_bar.addWidget(analytics_btn)
        top_bar.addWidget(dispatch_btn)

        main_layout.addLayout(top_bar)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        content_splitter = QSplitter(Qt.Horizontal)

        left_frame = QFrame(self)
        left_layout = QVBoxLayout()

        # Current Calls 

        current_calls_layout = QVBoxLayout()
        current_calls_label = QLabel("Current Calls")
        current_calls_label.setFont(QFont('Arial', 16, QFont.Bold))

        current_calls_layout.addWidget(current_calls_label)

        calls = [("Heart attack on Maple Drive", "Critical"),
                 ("Multiple people injured on 27th Street", "Critical"),
                 ("Apartment fire on Main Street", "Moderate")]

        for call in calls:
            call_frame = self.create_call_item(call)
            current_calls_layout.addWidget(call_frame)

        dispatch_layout = QVBoxLayout()
        dispatch_label = QLabel("Dispatch first responders:")
        dispatch_layout.addWidget(dispatch_label)

        police_btn = self.create_dispatch_button("Police", "blue")
        firefighters_btn = self.create_dispatch_button("Firefighters", "red")
        paramedics_btn = self.create_dispatch_button("Paramedics", "green")

        dispatch_layout.addWidget(police_btn)
        dispatch_layout.addWidget(firefighters_btn)
        dispatch_layout.addWidget(paramedics_btn)

        left_layout.addLayout(current_calls_layout)
        left_layout.addLayout(dispatch_layout)
        left_frame.setLayout(left_layout)

        map_frame = QFrame(self)
        map_layout = QVBoxLayout()

        self.url = QUrl('https://www.openstreetmap.org/')
        self.web_view = QWebEngineView(self)
        self.web_view.setUrl(self.url)

        map_layout.addWidget(self.web_view)
        map_frame.setLayout(map_layout)

        right_frame = QFrame(self)
        right_layout = QVBoxLayout()

        transcription_label = QLabel("Live Transcription")
        transcription_label.setFont(QFont('Arial', 14, QFont.Bold))
        right_layout.addWidget(transcription_label)

        transcript_box = QTextEdit(self)
        transcript_box.setReadOnly(True)
        transcript_box.setText("Live transcript messages will appear here...")
        transcript_box.setStyleSheet("background-color: white; border: 1px solid gray; padding: 10px;")
        right_layout.addWidget(transcript_box)

        right_frame.setLayout(right_layout)

        content_splitter.addWidget(left_frame)
        content_splitter.addWidget(map_frame)
        content_splitter.addWidget(right_frame)

        # Call Controls
        call_controls_layout = QHBoxLayout()
        hold_btn = self.create_callcontrol_button("Hold", color="#FFFFFF")
        mute_btn = self.create_callcontrol_button("Mute", color="#FFFFFF")
        message_btn = self.create_callcontrol_button("Message", color="#FFFFFF")
        transcribe_btn = self.create_callcontrol_button("Transcribe",color="#FFFFFF")
        setting_btn = self.create_callcontrol_button("Settings", color="#FFFFFF")
        endcall_btn = self.create_callcontrol_button("End", color="#A2191F", text_color="white")

        call_controls_layout.addWidget(hold_btn)
        call_controls_layout.addWidget(mute_btn)
        call_controls_layout.addWidget(message_btn)
        call_controls_layout.addWidget(transcribe_btn)
        call_controls_layout.addWidget(setting_btn)
        call_controls_layout.addWidget(endcall_btn)

        

        main_layout.addWidget(content_splitter)


        call_detail_layout = QHBoxLayout()

        
        left_layout = QVBoxLayout()
        
        phone_label = QLabel("+91 91882 70912")
        phone_label.setFont(QFont("Arial", 12))
        
        record_button = self.create_callcontrol_button("REC", color="#A2191F", text_color="white")
        
        
        # Horizontal layout for phone and REC button
        phone_layout = QHBoxLayout()
        phone_layout.addWidget(phone_label)
        phone_layout.addWidget(record_button)
        
        # User Name
        name_label = QLabel("Bradley Cooper")
        name_label.setFont(QFont("Arial", 16))
        
        # Location Info
        location_label = QLabel("Location:\n21A, First Floor, LKC Road,\nTX, USA - 43782")
        location_label.setFont(QFont("Arial", 12))
        
        # Add components to left layout
        left_layout.addLayout(phone_layout)
        left_layout.addWidget(name_label)
        left_layout.addWidget(location_label)
        left_layout.addStretch()
        
        right_layout = QVBoxLayout()
        
        transcription_label = QLabel("Transcription")
        transcription_label.setFont(QFont("Arial", 14))
        
        transcription_box = QTextEdit()
        transcription_box.setPlaceholderText("Transcription text here...")
        transcription_box.setStyleSheet("background-color: #F0F0F0;")
        
        echo_label = QLabel("EchoAnalysis")
        echo_label.setFont(QFont("Arial", 14))
        
        heart_attack_label = QLabel("Heart attack")
        heart_attack_label.setFont(QFont("Arial", 12))
        
        severity_button = self.create_dispatch_button("Critical", "#A2191F")
        
        suggestion_label = QLabel("Suggested: Ambulance")
        suggestion_label.setFont(QFont("Arial", 12))
        
        dispatch_button = self.create_dispatch_button("Dispatch", "#0E6027")
        
        echo_layout = QVBoxLayout()
        echo_layout.addWidget(heart_attack_label)
        echo_layout.addWidget(severity_button)
        echo_layout.addWidget(suggestion_label)
        echo_layout.addWidget(dispatch_button)
        
        right_layout.addWidget(transcription_label)
        right_layout.addWidget(transcription_box)
        right_layout.addWidget(echo_label)
        right_layout.addLayout(echo_layout)
        
        # Add left and right layouts to main layout
        call_detail_layout.addLayout(left_layout)
        call_detail_layout.addLayout(right_layout)


        main_layout.addLayout(call_detail_layout)

        main_layout.addLayout(call_controls_layout)




        self.setLayout(main_layout)

    def create_call_item(self, call_data):
        call_frame = QFrame(self)
        call_frame.setStyleSheet("background-color: white; border: 1px solid lightgray; border-radius: 10px;")
            
        call_label = QLabel(call_data[0])
        call_label.setFont(QFont('Arial', 12))
            
        badge_label = QLabel(call_data[1])
        badge_label.setFont(QFont('Arial', 12, QFont.Bold))
        badge_label.setAlignment(Qt.AlignCenter)
        badge_label.setStyleSheet(f"background-color: {'#A2191F' if call_data[1] == 'Critical' else '#F1C21B'}; color: white; border-radius: 10px; padding: 5px;")

        call_layout = QHBoxLayout()  
        call_layout.addWidget(call_label)
        call_layout.addWidget(badge_label)
        call_frame.setLayout(call_layout)

        return call_frame



    

    def create_top_button(self, name):
        btn = QPushButton(name)
        btn.setStyleSheet("""
            QPushButton{
                background-color: lightgray; border-radius: 10px;
            }
            QPushButton:hover{
            }
        """)
        btn.setFixedHeight(80)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def create_dispatch_button(self, name, color):
        btn = QPushButton(name)
        btn.setFixedSize(150, 40)
        btn.setStyleSheet(f"background-color: {color}; color: white; border-radius: 5px;")
        btn.setIcon(QIcon(f'{name.lower()}.png'))  
        btn.setFixedHeight(80)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn
    
    def create_callcontrol_button(self, name, color, text_color="black"):
        btn = QPushButton("  " + name)
        btn.setStyleSheet(f"background-color: {color}; color: {text_color}; border-radius: 5px;border: 1px solid #E2E8F0;")
        btn.setIcon(QIcon(f'icons/{name.lower()}.png'))    
        btn.setFixedHeight(80)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = EmergencyDashboard()
    window.show()

    sys.exit(app.exec_())
