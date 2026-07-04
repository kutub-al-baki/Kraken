"""
UIU MARINER - Professional ROV Control System
Main application with camera feeds, object detection, sensor telemetry, and vehicle control
"""

import sys
import os
import json
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QWidget
from PyQt6.QtCore import QTimer, Qt, pyqtSlot
from PyQt6.QtGui import QPixmap, QFont
from PyQt6 import uic

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.services.mavlinkConnection import PixhawkConnection
from src.joystickController import JoystickController
from src.views.workers.cameraWorker import CameraWorker, DualCameraManager
from src.views.workers.sensorWorker import SensorTelemetryWorker, MockSensorWorker
from src.views.workers.mediaManager import MediaManager
from src.computer_vision.camera_detector import CameraDetector


class MarinerROVControl(QMainWindow):
    """
    Main application window for UIU MARINER ROV Control System.
    Integrates camera feeds, object detection, sensor telemetry, and vehicle control.
    """

    def __init__(self):
        super().__init__()

        # Load configuration
        self.config = self.load_config()

        # Initialize UI from .ui file
        self.init_ui()

        # Initialize components
        self.pixhawk = None
        self.joystick = None
        self.camera_manager = None
        self.sensor_worker = None
        self.media_manager = None

        # State variables
        self.armed = False
        self.current_mode = "MANUAL"
        self.thruster_values = [1500] * 8
        self.camera_detection_enabled = True
        self.active_camera = 0
        self.recording_timer = None

        # Setup connections and start threads
        self.setup_connections()

        # Start components asynchronously for non-blocking startup
        print("[MARINER]  Starting components asynchronously...")

        # Start camera feeds (non-blocking)
        QTimer.singleShot(100, self.start_camera_feeds)

        # Start sensor telemetry (non-blocking with auto-fallback)
        QTimer.singleShot(200, self.start_sensor_telemetry)

        # Connect to Pixhawk (may take time)
        QTimer.singleShot(300, self.connect_pixhawk)

        # Initialize joystick
        QTimer.singleShot(400, self.init_joystick)

        # Initialize media manager
        self.media_manager = MediaManager()

        # Start control loop
        self.control_timer = QTimer(self)
        self.control_timer.timeout.connect(self.control_loop)
        self.control_timer.start(500)

        # UI update timer
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.update_ui)
        self.ui_update_timer.start(2000)

        # Attitude update timer (faster updates for smooth compass)
        self.attitude_update_timer = QTimer(self)
        self.attitude_update_timer.timeout.connect(self.update_attitude_from_pixhawk)
        self.attitude_update_timer.start(100)  # Update every 100ms for smooth compass

        print(
            "[MARINER] [OK] Application initialized - components starting in background"
        )

    def load_config(self):
        """Load configuration from JSON file."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
        default_config = {
            "mavlink_connection": "tcp:raspberrypi.local:7000",
            "joystick_target": None,
            "camera": {
                "stream_url0": "http://raspberrypi.local:8080/video_feed",
                "stream_url1": "http://raspberrypi.local:8081/video_feed",
            },
            "sensors": {
                "host": "raspberrypi.local",
                "port": 5000,
                "protocol": "tcp",
                "mock_mode": False,
                "auto_connect": True,
            },
            "network": {
                "auto_detect": True,
                "pi_hostname": "raspberrypi.local",
                "fallback_ip": "192.168.0.100",
            },
            "thrusters": {
                "total_count": 8,
            },
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    loaded = json.load(f)
                    # Merge loaded config with defaults
                    merged = {**default_config, **loaded}
                    # Ensure nested dicts are also merged
                    for key in ["camera", "sensors", "network", "thrusters"]:
                        if key in loaded and key in default_config:
                            merged[key] = {**default_config[key], **loaded[key]}
                    return merged
        except Exception as e:
            print(f"[CONFIG] Error loading: {e}, using defaults")

        return default_config

    def init_ui(self):
        """Initialize UI from the new_ui_ui.py file."""
        print("[UI] Loading new UI design...")

        # Define color palette for status indicators (used in some methods)
        self.colors = {
            "bg_dark": "#0D1117",
            "bg_secondary": "#161B22",
            "bg_tertiary": "#21262D",
            "accent": "#FF8800",
            "accent_hover": "#FFA040",
            "success": "#00D084",
            "danger": "#FF4D4D",
            "warning": "#FFB800",
            "text_primary": "#E6EDF3",
            "text_secondary": "#8B949E",
            "border": "#30363D",
            "border_accent": "#FF8800",
        }

        # Import and setup the new UI
        from src.views.new_ui_ui import Ui_MainWindow

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Set window properties
        self.setWindowTitle("UIU MARINER - ROV Control System")

        print("[UI] [OK] New UI loaded successfully")

        # Find and store references to UI elements
        self.find_ui_elements()

        # Setup navigation between pages
        self.setup_navigation()

        # Initialize modern compass widget
        self.init_modern_compass()

    # ============================================================================
    # OLD PROGRAMMATIC UI METHODS - NO LONGER USED (kept for reference)
    # ============================================================================

    def create_ui_programmatically_OLD(self):
        """Create modern UI programmatically with sleek dark theme.
        NOTE: This method is no longer used. The UI is now loaded from new_ui_ui.py
        """
        from PyQt6.QtWidgets import (
            QVBoxLayout,
            QHBoxLayout,
            QGroupBox,
            QFrame,
            QGridLayout,
        )

        # Modern color palette
        self.colors = {
            "bg_dark": "#0D1117",
            "bg_secondary": "#161B22",
            "bg_tertiary": "#21262D",
            "accent": "#FF8800",
            "accent_hover": "#FFA040",
            "success": "#00D084",
            "danger": "#FF4D4D",
            "warning": "#FFB800",
            "text_primary": "#E6EDF3",
            "text_secondary": "#8B949E",
            "border": "#30363D",
            "border_accent": "#FF8800",
        }

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Set main window style
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {self.colors['bg_dark']};
            }}
            QWidget {{
                background-color: {self.colors['bg_dark']};
                color: {self.colors['text_primary']};
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }}
            QLabel {{
                color: {self.colors['text_primary']};
                background-color: transparent;
                font-size: 9pt;
            }}
            QGroupBox {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                padding: 10px;
                margin-top: 8px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                color: {self.colors['accent']};
                background-color: {self.colors['bg_tertiary']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: {self.colors['bg_tertiary']};
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 9pt;
                color: {self.colors['text_primary']};
                min-height: 30px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['bg_secondary']};
                border-color: {self.colors['accent']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['bg_dark']};
            }}
            QPushButton#btnArm {{
                background-color: {self.colors['success']};
                color: #000;
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton#btnArm:hover {{
                background-color: #00F0A0;
            }}
            QPushButton#btnEmergencyStop {{
                background-color: {self.colors['danger']};
                color: #FFF;
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton#btnEmergencyStop:hover {{
                background-color: #FF6060;
            }}
            QPushButton#btnManualControl {{
                background-color: {self.colors['bg_tertiary']};
                color: {self.colors['accent']};
                font-size: 9pt;
                font-weight: bold;
                border: 2px solid {self.colors['accent']};
                border-radius: 6px;
            }}
            QPushButton#btnManualControl:hover {{
                background-color: {self.colors['accent']};
                color: #000;
            }}
            QPushButton#btnManualControl:pressed {{
                background-color: {self.colors['success']};
                color: #000;
                border-color: {self.colors['success']};
            }}
        """
        )

        # === TOP BAR ===
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)

        # === MAIN CONTENT === (Use scrollable area for better responsiveness)
        from PyQt6.QtWidgets import QScrollArea

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                border: none;
                background-color: {self.colors['bg_dark']};
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['bg_secondary']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.colors['border']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['accent']};
            }}
        """
        )

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        # Left column: Cameras
        camera_panel = self.create_camera_panel()
        content_layout.addWidget(camera_panel, 65)

        # Right column: Status & Controls
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, 35)

        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

        # === BOTTOM BAR ===
        bottom_bar = self.create_bottom_bar()
        main_layout.addWidget(bottom_bar)

    def create_top_bar_OLD(self):
        """Create modern top navigation bar. (OLD - NO LONGER USED)"""
        from PyQt6.QtWidgets import QFrame, QHBoxLayout

        top_bar = QFrame()
        top_bar.setFixedHeight(60)  # Reduced height
        top_bar.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.colors['bg_secondary']};
                border-bottom: 2px solid {self.colors['border_accent']};
            }}
        """
        )

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(16, 8, 16, 8)

        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "public", "logo.png"
        )
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            # Scale logo to fit top bar (maintain aspect ratio)
            scaled_logo = logo_pixmap.scaled(
                40,
                40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled_logo)
            logo_label.setStyleSheet("background-color: transparent;")
            layout.addWidget(logo_label)

        # Title
        title = QLabel("UIU MARINER")
        title.setStyleSheet(
            f"""
            font-size: 18pt;
            font-weight: bold;
            color: {self.colors['accent']};
            margin-left: 10px;
        """
        )
        layout.addWidget(title)

        layout.addStretch()

        # System time/status
        system_label = QLabel("ROV CONTROL SYSTEM")
        system_label.setStyleSheet(
            f"""
            font-size: 9pt;
            color: {self.colors['text_secondary']};
            font-weight: bold;
        """
        )
        layout.addWidget(system_label)

        return top_bar

    def create_camera_panel_OLD(self):
        """Create modern camera display panel. (OLD - NO LONGER USED)"""
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame

        panel = QFrame()
        panel.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: 12px;
            }}
        """
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Main camera
        main_label = QLabel("PRIMARY CAMERA")
        main_label.setStyleSheet(
            f"""
            font-size: 9pt;
            font-weight: bold;
            color: {self.colors['accent']};
            padding: 6px;
        """
        )
        layout.addWidget(main_label)

        self.lblCameraMain = QLabel(" Waiting for video feed...")
        self.lblCameraMain.setMinimumSize(800, 480)  # Increased camera height
        self.lblCameraMain.setScaledContents(False)
        self.lblCameraMain.setStyleSheet(
            f"""
            background-color: #000;
            border: 2px solid {self.colors['border_accent']};
            border-radius: 6px;
            color: {self.colors['text_secondary']};
            font-size: 11pt;
        """
        )
        self.lblCameraMain.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lblCameraMain)

        # Secondary camera
        secondary_label = QLabel("SECONDARY CAMERA")
        secondary_label.setStyleSheet(
            f"""
            font-size: 8pt;
            font-weight: bold;
            color: {self.colors['text_secondary']};
            padding: 6px;
        """
        )
        layout.addWidget(secondary_label)

        self.lblCameraSmall = QLabel(" Waiting for video feed...")
        self.lblCameraSmall.setMinimumSize(400, 240)  # Increased camera height
        self.lblCameraSmall.setScaledContents(False)
        self.lblCameraSmall.setStyleSheet(
            f"""
            background-color: #000;
            border: 1px solid {self.colors['border']};
            border-radius: 5px;
            color: {self.colors['text_secondary']};
            font-size: 9pt;
        """
        )
        self.lblCameraSmall.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lblCameraSmall)

        return panel

    def create_right_panel_OLD(self):
        """Create modern right side panel with status and controls. (OLD - NO LONGER USED)"""
        from PyQt6.QtWidgets import QVBoxLayout, QFrame

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # System Status
        status_panel = self.create_status_panel()
        layout.addWidget(status_panel)

        # Sensor Readings
        sensor_panel = self.create_sensor_panel()
        layout.addWidget(sensor_panel)

        # Control Buttons
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        layout.addStretch()

        return panel

    def create_status_panel_OLD(self):
        """Create system status panel. (OLD - NO LONGER USED)"""
        from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QHBoxLayout

        group = QGroupBox("SYSTEM STATUS")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Pixhawk status
        pixhawk_row = QHBoxLayout()
        pixhawk_label = QLabel("Pixhawk:")
        pixhawk_label.setStyleSheet("font-weight: bold;")
        self.lblPixhawkStatus = QLabel(" Disconnected")
        self.lblPixhawkStatus.setStyleSheet(f"color: {self.colors['text_secondary']};")
        pixhawk_row.addWidget(pixhawk_label)
        pixhawk_row.addWidget(self.lblPixhawkStatus)
        pixhawk_row.addStretch()
        layout.addLayout(pixhawk_row)

        # Joystick status
        joystick_row = QHBoxLayout()
        joystick_label = QLabel("Controller:")
        joystick_label.setStyleSheet("font-weight: bold;")
        self.lblJoystickStatus = QLabel(" Disconnected")
        self.lblJoystickStatus.setStyleSheet(f"color: {self.colors['text_secondary']};")
        joystick_row.addWidget(joystick_label)
        joystick_row.addWidget(self.lblJoystickStatus)
        joystick_row.addStretch()
        layout.addLayout(joystick_row)

        # Mode status
        mode_row = QHBoxLayout()
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("font-weight: bold;")
        self.lblModeStatus = QLabel("MANUAL")
        self.lblModeStatus.setStyleSheet(f"color: {self.colors['warning']};")
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.lblModeStatus)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Arm status
        arm_row = QHBoxLayout()
        arm_label = QLabel("Armed:")
        arm_label.setStyleSheet("font-weight: bold;")
        self.lblArmStatus = QLabel(" NO")
        self.lblArmStatus.setStyleSheet(f"color: {self.colors['text_secondary']};")
        arm_row.addWidget(arm_label)
        arm_row.addWidget(self.lblArmStatus)
        arm_row.addStretch()
        layout.addLayout(arm_row)

        # Sensor status
        sensor_row = QHBoxLayout()
        sensor_label = QLabel("Sensors:")
        sensor_label.setStyleSheet("font-weight: bold;")
        self.lblSensorStatus = QLabel(" Disconnected")
        self.lblSensorStatus.setStyleSheet(f"color: {self.colors['text_secondary']};")
        sensor_row.addWidget(sensor_label)
        sensor_row.addWidget(self.lblSensorStatus)
        sensor_row.addStretch()
        layout.addLayout(sensor_row)

        return group

    def create_sensor_panel_OLD(self):
        """Create sensor readings panel. (OLD - NO LONGER USED)"""
        from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QGridLayout

        group = QGroupBox("SENSOR TELEMETRY")
        layout = QGridLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 16, 10, 10)

        # Depth
        depth_label = QLabel("Depth")
        depth_label.setStyleSheet(
            f"font-size: 8pt; color: {self.colors['text_secondary']};"
        )
        self.lblDepth = QLabel("0.0 m")
        self.lblDepth.setStyleSheet(
            f"""
            font-size: 16pt;
            font-weight: bold;
            color: {self.colors['accent']};
            padding: 6px;
            background-color: {self.colors['bg_tertiary']};
            border-radius: 5px;
        """
        )
        self.lblDepth.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(depth_label, 0, 0)
        layout.addWidget(self.lblDepth, 1, 0, 1, 2)

        # Temperature
        temp_label = QLabel("Temperature")
        temp_label.setStyleSheet(
            f"font-size: 8pt; color: {self.colors['text_secondary']};"
        )
        self.lblTemperature = QLabel("0.0°C")
        self.lblTemperature.setStyleSheet(
            f"""
            font-size: 13pt;
            font-weight: bold;
            color: {self.colors['text_primary']};
            padding: 5px;
            background-color: {self.colors['bg_tertiary']};
            border-radius: 5px;
        """
        )
        self.lblTemperature.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(temp_label, 2, 0)
        layout.addWidget(self.lblTemperature, 3, 0)

        # Pressure
        pressure_label = QLabel("Pressure")
        pressure_label.setStyleSheet(
            f"font-size: 8pt; color: {self.colors['text_secondary']};"
        )
        self.lblPressure = QLabel("0.0 hPa")
        self.lblPressure.setStyleSheet(
            f"""
            font-size: 13pt;
            font-weight: bold;
            color: {self.colors['text_primary']};
            padding: 5px;
            background-color: {self.colors['bg_tertiary']};
            border-radius: 5px;
        """
        )
        self.lblPressure.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pressure_label, 2, 1)
        layout.addWidget(self.lblPressure, 3, 1)

        return group

    def create_control_panel_OLD(self):
        """Create control buttons panel. (OLD - NO LONGER USED)"""
        from PyQt6.QtWidgets import QVBoxLayout, QGroupBox

        group = QGroupBox("CONTROL PANEL")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 16, 10, 10)

        # ARM button
        self.btnArm = QPushButton(" ARM THRUSTERS")
        self.btnArm.setObjectName("btnArm")
        self.btnArm.setMinimumHeight(45)
        self.btnArm.clicked.connect(self.toggle_arm)
        layout.addWidget(self.btnArm)

        # Emergency Stop
        self.btnEmergencyStop = QPushButton(" EMERGENCY STOP")
        self.btnEmergencyStop.setObjectName("btnEmergencyStop")
        self.btnEmergencyStop.setMinimumHeight(45)
        self.btnEmergencyStop.clicked.connect(self.emergency_stop)
        layout.addWidget(self.btnEmergencyStop)

        # Separator for manual controls
        manual_separator = QLabel("" * 25)
        manual_separator.setStyleSheet(
            f"color: {self.colors['border']}; padding: 6px 0px; font-size: 8pt;"
        )
        manual_separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(manual_separator)

        # Manual Control Section Label
        manual_label = QLabel(" MANUAL CONTROLS")
        manual_label.setStyleSheet(
            f"""
            font-size: 8pt;
            font-weight: bold;
            color: {self.colors['accent']};
            padding: 3px;
        """
        )
        manual_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(manual_label)

        # Manual control buttons in grid layout
        from PyQt6.QtWidgets import QGridLayout, QWidget

        manual_widget = QWidget()
        manual_layout = QGridLayout(manual_widget)
        manual_layout.setSpacing(8)
        manual_layout.setContentsMargins(0, 0, 0, 0)

        # Forward button (top center)
        self.btnForward = QPushButton(" FWD")
        self.btnForward.setObjectName("btnManualControl")
        self.btnForward.setMinimumHeight(40)
        self.btnForward.pressed.connect(lambda: self.send_manual_command("forward"))
        self.btnForward.released.connect(self.stop_manual_command)
        manual_layout.addWidget(self.btnForward, 0, 1)

        # Left button (middle left)
        self.btnLeft = QPushButton(" LEFT")
        self.btnLeft.setObjectName("btnManualControl")
        self.btnLeft.setMinimumHeight(40)
        self.btnLeft.pressed.connect(lambda: self.send_manual_command("left"))
        self.btnLeft.released.connect(self.stop_manual_command)
        manual_layout.addWidget(self.btnLeft, 1, 0)

        # Right button (middle right)
        self.btnRight = QPushButton(" RIGHT")
        self.btnRight.setObjectName("btnManualControl")
        self.btnRight.setMinimumHeight(40)
        self.btnRight.pressed.connect(lambda: self.send_manual_command("right"))
        self.btnRight.released.connect(self.stop_manual_command)
        manual_layout.addWidget(self.btnRight, 1, 2)

        # Backward button (bottom center)
        self.btnBackward = QPushButton(" BWD")
        self.btnBackward.setObjectName("btnManualControl")
        self.btnBackward.setMinimumHeight(40)
        self.btnBackward.pressed.connect(lambda: self.send_manual_command("backward"))
        self.btnBackward.released.connect(self.stop_manual_command)
        manual_layout.addWidget(self.btnBackward, 2, 1)

        layout.addWidget(manual_widget)

        # Toggle Detection
        self.btnToggleDetection = QPushButton(" Toggle Detection")
        self.btnToggleDetection.setMinimumHeight(36)
        self.btnToggleDetection.clicked.connect(self.toggle_detection)
        layout.addWidget(self.btnToggleDetection)

        # Separator
        separator = QLabel("" * 25)
        separator.setStyleSheet(
            f"color: {self.colors['border']}; padding: 6px 0px; font-size: 8pt;"
        )
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)

        # Camera Section Label
        camera_label = QLabel(" CAMERA CONTROLS")
        camera_label.setStyleSheet(
            f"""
            font-size: 8pt;
            font-weight: bold;
            color: {self.colors['accent']};
            padding: 3px;
        """
        )
        camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(camera_label)

        # Camera Configuration
        self.btnCameraConfig = QPushButton(" Camera Settings")
        self.btnCameraConfig.setObjectName("btnCameraConfig")
        self.btnCameraConfig.setMinimumHeight(42)
        self.btnCameraConfig.setStyleSheet(
            f"""
            QPushButton#btnCameraConfig {{
                background-color: {self.colors['accent']};
                color: white;
                font-size: 9pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }}
            QPushButton#btnCameraConfig:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """
        )
        self.btnCameraConfig.clicked.connect(self.open_camera_settings)
        layout.addWidget(self.btnCameraConfig)

        # Restart Camera Feeds
        self.btnRestartCameras = QPushButton(" Restart Cameras")
        self.btnRestartCameras.setObjectName("btnRestartCameras")
        self.btnRestartCameras.setMinimumHeight(38)
        self.btnRestartCameras.setStyleSheet(
            f"""
            QPushButton#btnRestartCameras {{
                background-color: {self.colors['warning']};
                color: #000;
                font-size: 10pt;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }}
            QPushButton#btnRestartCameras:hover {{
                background-color: #FFD040;
            }}
        """
        )
        self.btnRestartCameras.clicked.connect(self.restart_camera_feeds)
        layout.addWidget(self.btnRestartCameras)

        # Separator for media controls
        media_separator = QLabel("" * 25)
        media_separator.setStyleSheet(
            f"color: {self.colors['border']}; padding: 6px 0px; font-size: 8pt;"
        )
        media_separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(media_separator)

        # Media Controls Section Label
        media_label = QLabel(" MEDIA CONTROLS")
        media_label.setStyleSheet(
            f"""
            font-size: 8pt;
            font-weight: bold;
            color: {self.colors['accent']};
            padding: 3px;
        """
        )
        media_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(media_label)

        # Media buttons in grid layout (2 columns)
        from PyQt6.QtWidgets import QGridLayout, QWidget

        media_widget = QWidget()
        media_layout = QGridLayout(media_widget)
        media_layout.setSpacing(8)
        media_layout.setContentsMargins(0, 0, 0, 0)

        # Capture Image Button (Left)
        self.btnCaptureImage = QPushButton("📸 CAPTURE")
        self.btnCaptureImage.setObjectName("btnCaptureImage")
        self.btnCaptureImage.setMinimumHeight(44)
        self.btnCaptureImage.setStyleSheet(
            f"""
            QPushButton#btnCaptureImage {{
                background-color: #2E7D32;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }}
            QPushButton#btnCaptureImage:hover {{
                background-color: #388E3C;
            }}
            QPushButton#btnCaptureImage:pressed {{
                background-color: #1B5E20;
            }}
        """
        )
        self.btnCaptureImage.clicked.connect(self.capture_image)
        media_layout.addWidget(self.btnCaptureImage, 0, 0)

        # Start Recording Button (Right)
        self.btnStartRecording = QPushButton("⏺ RECORD")
        self.btnStartRecording.setObjectName("btnStartRecording")
        self.btnStartRecording.setMinimumHeight(44)
        self.btnStartRecording.setStyleSheet(
            f"""
            QPushButton#btnStartRecording {{
                background-color: #C62828;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }}
            QPushButton#btnStartRecording:hover {{
                background-color: #E53935;
            }}
            QPushButton#btnStartRecording:pressed {{
                background-color: #B71C1C;
            }}
        """
        )
        self.btnStartRecording.clicked.connect(self.toggle_recording)
        media_layout.addWidget(self.btnStartRecording, 0, 1)

        layout.addWidget(media_widget)

        # Stop Recording Button (Full width, only visible during recording)
        self.btnStopRecording = QPushButton("⏹ STOP RECORDING")
        self.btnStopRecording.setObjectName("btnStopRecording")
        self.btnStopRecording.setMinimumHeight(40)
        self.btnStopRecording.setStyleSheet(
            f"""
            QPushButton#btnStopRecording {{
                background-color: #F44336;
                color: white;
                font-size: 9pt;
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 6px;
            }}
            QPushButton#btnStopRecording:hover {{
                background-color: #D32F2F;
            }}
            QPushButton#btnStopRecording:pressed {{
                background-color: #B71C1C;
            }}
        """
        )
        self.btnStopRecording.clicked.connect(self.stop_recording)
        self.btnStopRecording.hide()
        layout.addWidget(self.btnStopRecording)

        # Open Media Folder Button
        self.btnOpenMediaFolder = QPushButton(" 📁 Open Media Folder")
        self.btnOpenMediaFolder.setObjectName("btnOpenMediaFolder")
        self.btnOpenMediaFolder.setMinimumHeight(36)
        self.btnOpenMediaFolder.setStyleSheet(
            f"""
            QPushButton#btnOpenMediaFolder {{
                background-color: {self.colors['accent']};
                color: white;
                font-size: 8pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }}
            QPushButton#btnOpenMediaFolder:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """
        )
        self.btnOpenMediaFolder.clicked.connect(self.open_media_folder)
        layout.addWidget(self.btnOpenMediaFolder)

        return group

    def create_bottom_bar_OLD(self):
        """Create bottom status bar. (OLD - NO LONGER USED)"""
        from PyQt6.QtWidgets import QFrame, QHBoxLayout

        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(35)  # More compact
        bottom_bar.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.colors['bg_secondary']};
                border-top: 1px solid {self.colors['border']};
            }}
        """
        )

        layout = QHBoxLayout(bottom_bar)
        layout.setContentsMargins(16, 6, 16, 6)

        # Connection info (will be updated dynamically)
        self.conn_label = QLabel(" Network: Connecting...")
        self.conn_label.setStyleSheet(
            f"color: {self.colors['warning']}; font-size: 8pt;"
        )
        layout.addWidget(self.conn_label)

        layout.addStretch()

        # Version info
        version_label = QLabel("UIU MARINER v1.0 | ArduSub | 8-Thruster ROV")
        version_label.setStyleSheet(
            f"color: {self.colors['text_secondary']}; font-size: 8pt;"
        )
        layout.addWidget(version_label)

        return bottom_bar

        # Apply dark theme
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 2px solid #3f3f46;
                border-radius: 5px;
                margin-top: 10px;
                padding: 15px;
                font-weight: bold;
                color: #FF8800;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #FF8800;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #FF8800;
            }
            QLabel {
                color: white;
            }
        """
        )

    def find_ui_elements(self):
        """Map new UI elements to expected variable names for compatibility."""
        try:
            # Camera labels - map from new UI to old variable names
            self.lblCameraMain = self.ui.lblCam1Feed
            self.lblCameraSmall = self.ui.lblCam2Feed

            # Status labels - map from new UI sensor status labels
            self.lblPixhawkStatus = self.ui.lblPixhawkStatus
            self.lblJoystickStatus = self.ui.lblJoystickStatus

            # Mode and Arm status - use pixhawk and thrusters value labels
            self.lblModeStatus = self.ui.lblPixhawkValue  # Will show mode
            self.lblArmStatus = self.ui.lblThrustersValue  # Will show armed status

            # Sensor status label
            self.lblSensorStatus = self.ui.lblCommsStatus  # Map to telemetry status

            # Sensor reading labels - map to new UI value labels
            # Note: lblDepth uses lblDepthStatusValue from the depth status frame
            self.lblDepth = self.ui.lblDepthStatusValue
            self.lblTemperature = self.ui.lblTemperatureValue
            # Note: Pressure will show in hPa, not bar
            self.lblPressure = self.ui.lblPressureValue

            # Buttons - map from new UI
            self.btnArm = self.ui.btnArmConnect  # ARM/CONNECT button
            self.btnEmergencyStop = self.ui.btnEmergencyStop

            # Media buttons
            self.btnCaptureImage = self.ui.btnCapture
            self.btnStartRecording = self.ui.btnRecord

            # Create placeholder for detection toggle (not in new UI, will add to settings)
            self.btnToggleDetection = None

            # Connection status label
            self.conn_label = self.ui.lblConnectionStatus

            # Attitude/Compass elements
            self.lblCompass = self.ui.lblCompass
            self.lblHeadingDisplay = self.ui.lblHeadingDisplay
            self.lblPitchValue = self.ui.lblPitchValue
            self.lblRollValue = self.ui.lblRollValue

            # Additional sensor depth label (there's also lblDepthLabel)
            self.lblDepthLabel = self.ui.lblDepthLabel

            # Camera status labels (lblCam1 for main camera, lblCam2 for secondary)
            self.lblCam1Status = self.ui.lblCam1
            self.lblCam2Status = self.ui.lblCam2

            print("[UI] [OK] Mapped new UI elements to expected variable names")
        except Exception as e:
            print(f"[UI] Element mapping error: {e}")
            import traceback

            traceback.print_exc()

    def setup_navigation(self):
        """Setup navigation between different pages in the stacked widget."""
        try:
            # Connect sidebar buttons to switch pages
            self.ui.btnDashboard.clicked.connect(lambda: self.switch_page(0))
            self.ui.btnGallery.clicked.connect(lambda: self.switch_page(1))
            self.ui.btnDataAnalysis.clicked.connect(lambda: self.switch_page(2))
            self.ui.btnSettings.clicked.connect(lambda: self.switch_page(3))

            # Set Dashboard as default page
            self.ui.stackedWidget.setCurrentIndex(0)

            print("[UI] [OK] Navigation setup complete")
        except Exception as e:
            print(f"[UI] Navigation setup error: {e}")

    def init_modern_compass(self):
        """Initialize the modern compass widget to replace the placeholder."""
        try:
            from src.views.workers.modernCompass import ModernCompass

            # Create modern compass widget
            self.compass_widget = ModernCompass()
            self.compass_widget.setMinimumSize(
                150, 150
            )  # Increased for better visibility
            self.compass_widget.setMaximumSize(
                200, 200
            )  # Increased for better visibility

            # Replace the lblCompass placeholder with the actual compass widget
            if hasattr(self, "lblCompass") and self.lblCompass:
                # Get the parent layout
                parent_layout = self.lblCompass.parent().layout()
                if parent_layout:
                    # Find the index of lblCompass in the layout
                    for i in range(parent_layout.count()):
                        if parent_layout.itemAt(i).widget() == self.lblCompass:
                            # Hide the placeholder
                            self.lblCompass.hide()
                            # Insert the compass widget at the same position
                            parent_layout.insertWidget(i, self.compass_widget)
                            break

            # Initialize attitude data
            self.current_heading = 0.0
            self.current_pitch = 0.0
            self.current_roll = 0.0

            print("[COMPASS] [OK] Modern compass widget initialized")
        except Exception as e:
            print(f"[COMPASS] [ERR] Failed to initialize: {e}")
            import traceback

            traceback.print_exc()

    def switch_page(self, index):
        """Switch to a different page in the stacked widget."""
        try:
            self.ui.stackedWidget.setCurrentIndex(index)

            # Load gallery when switching to gallery page
            if index == 1:  # Gallery page
                self.load_gallery()

            # Update button checked states
            self.ui.btnDashboard.setChecked(index == 0)
            self.ui.btnGallery.setChecked(index == 1)
            self.ui.btnDataAnalysis.setChecked(index == 2)
            self.ui.btnSettings.setChecked(index == 3)
        except Exception as e:
            print(f"[UI] Page switch error: {e}")

    def setup_connections(self):
        """Setup signal-slot connections for UI elements."""
        try:
            # Connect main control buttons
            if hasattr(self, "btnArm") and self.btnArm:
                self.btnArm.clicked.connect(self.toggle_arm)

            if hasattr(self, "btnEmergencyStop") and self.btnEmergencyStop:
                self.btnEmergencyStop.clicked.connect(self.emergency_stop)

            # Connect media buttons
            if hasattr(self, "btnCaptureImage") and self.btnCaptureImage:
                self.btnCaptureImage.clicked.connect(self.capture_image)

            if hasattr(self, "btnStartRecording") and self.btnStartRecording:
                self.btnStartRecording.clicked.connect(self.toggle_recording)

            # Connect gallery controls
            if hasattr(self.ui, "btnRefreshGallery"):
                self.ui.btnRefreshGallery.clicked.connect(self.load_gallery)

            if hasattr(self.ui, "cmbGalleryFilter"):
                self.ui.cmbGalleryFilter.currentIndexChanged.connect(self.load_gallery)

            # Connect detection toggle if it exists
            if hasattr(self, "btnToggleDetection") and self.btnToggleDetection:
                self.btnToggleDetection.clicked.connect(self.toggle_detection)

            # Connect zoom buttons
            if hasattr(self.ui, "btnZoomIn") and self.ui.btnZoomIn:
                self.ui.btnZoomIn.clicked.connect(self.zoom_in_cameras)

            if hasattr(self.ui, "btnZoomOut") and self.ui.btnZoomOut:
                self.ui.btnZoomOut.clicked.connect(self.zoom_out_cameras)

            print("[UI] [OK] Button connections established")
        except Exception as e:
            print(f"[UI] Connection setup error: {e}")

    def start_camera_feeds(self):
        """Start dual camera feeds with object detection via MJPEG streams."""
        try:
            # Get MJPEG stream URLs from config
            stream_url0 = self.config["camera"].get(
                "stream_url0", "http://raspberrypi.local:8080/video_feed"
            )
            stream_url1 = self.config["camera"].get(
                "stream_url1", "http://raspberrypi.local:8081/video_feed"
            )

            print(f"[CAMERAS] Camera 0 URL: {stream_url0}")
            print(f"[CAMERAS] Camera 1 URL: {stream_url1}")

            self.camera_manager = DualCameraManager(stream_url0, stream_url1)

            # Connect camera 0 (port 8080) to MAIN display
            self.camera_manager.camera0.frame_ready.connect(self.update_camera_main)
            self.camera_manager.camera0.error_occurred.connect(self.handle_camera_error)
            self.camera_manager.camera0.status_update.connect(
                self.update_camera_status_main
            )

            # Connect camera 1 (port 8081) to CAM2 display
            self.camera_manager.camera1.frame_ready.connect(self.update_camera_small)
            self.camera_manager.camera1.error_occurred.connect(self.handle_camera_error)
            self.camera_manager.camera1.status_update.connect(
                self.update_camera_status_cam2
            )

            self.camera_manager.start_all()
            print("[CAMERAS] [OK] Dual MJPEG camera feeds started")

            # Setup object detection
            self.setup_object_detection()
        except Exception as e:
            print(f"[CAMERAS] [ERR] Failed to start: {e}")

    def setup_object_detection(self):
        """Setup object detection for both cameras."""
        try:
            print("[DETECTION] Initializing object detection...")

            # Create detector for camera 0 (main camera)
            self.detector0 = CameraDetector(camera_id=0)
            self.detector0.set_mode("face")  # Default: face/eye/smile detection
            print(
                f"[DETECTION] Camera 0 detector created - Mode: {self.detector0.mode}, Enabled: {self.detector0.enabled}"
            )

            # Create detector for camera 1 (secondary camera)
            self.detector1 = CameraDetector(camera_id=1)
            self.detector1.set_mode("face")  # Default: face/eye/smile detection
            print(
                f"[DETECTION] Camera 1 detector created - Mode: {self.detector1.mode}, Enabled: {self.detector1.enabled}"
            )

            # Attach detectors to camera workers
            if self.camera_manager:
                self.camera_manager.camera0.set_detector(self.detector0)
                self.camera_manager.camera1.set_detector(self.detector1)

                # Enable detection by default
                self.camera_manager.camera0.enable_detection()
                self.camera_manager.camera1.enable_detection()

                print("[DETECTION] ✅ Object detection ACTIVE on both cameras")
                print(
                    f"[DETECTION] Camera 0: detection_enabled={self.camera_manager.camera0.detection_enabled}"
                )
                print(
                    f"[DETECTION] Camera 1: detection_enabled={self.camera_manager.camera1.detection_enabled}"
                )
                print("[DETECTION] Mode: Face Detection (Face/Eye/Smile)")
                print(
                    "[DETECTION] You should see 'FACE DETECTION' text on camera feeds"
                )
        except Exception as e:
            print(f"[DETECTION] [ERR] Failed to setup: {e}")
            import traceback

            traceback.print_exc()

    def toggle_detection(self):
        """Toggle object detection on/off."""
        try:
            if self.camera_manager:
                if self.camera_manager.camera0.detection_enabled:
                    self.camera_manager.camera0.disable_detection()
                    self.camera_manager.camera1.disable_detection()
                    print("[DETECTION] Disabled")
                else:
                    self.camera_manager.camera0.enable_detection()
                    self.camera_manager.camera1.enable_detection()
                    print("[DETECTION] Enabled")
        except Exception as e:
            print(f"[DETECTION] Toggle error: {e}")

    def zoom_in_cameras(self):
        """Zoom in on both cameras"""
        try:
            if self.camera_manager:
                self.camera_manager.zoom_in_all()
                zoom_level = self.camera_manager.camera0.zoom_level
                print(f"[ZOOM] Zoomed in to {zoom_level:.2f}x")
        except Exception as e:
            print(f"[ZOOM] Error: {e}")

    def zoom_out_cameras(self):
        """Zoom out on both cameras"""
        try:
            if self.camera_manager:
                self.camera_manager.zoom_out_all()
                zoom_level = self.camera_manager.camera0.zoom_level
                print(f"[ZOOM] Zoomed out to {zoom_level:.2f}x")
        except Exception as e:
            print(f"[ZOOM] Error: {e}")

    def start_sensor_telemetry(self):
        """Start sensor telemetry worker."""
        try:
            self.sensor_worker = SensorTelemetryWorker(
                host=self.config["sensors"]["host"],
                port=self.config["sensors"]["port"],
                protocol=self.config["sensors"]["protocol"],
            )

            self.sensor_worker.data_received.connect(
                self.update_sensor_display, Qt.ConnectionType.QueuedConnection
            )
            self.sensor_worker.connection_status.connect(
                self.handle_sensor_status, Qt.ConnectionType.QueuedConnection
            )

            if hasattr(self.sensor_worker, "error_occurred"):
                self.sensor_worker.error_occurred.connect(
                    self.handle_sensor_error, Qt.ConnectionType.QueuedConnection
                )

            self.sensor_worker.start()
            QApplication.processEvents()

        except Exception as e:
            print(f"[SENSORS] [ERR] Failed to start: {e}")
            import traceback

            traceback.print_exc()

    @pyqtSlot(str)
    def handle_sensor_error(self, error_msg):
        """Handle sensor connection errors."""
        print(f"[SENSORS]  Error: {error_msg}")
        # Could trigger UI notification here

    def connect_pixhawk(self):
        """Connect to Pixhawk via MAVLink."""
        try:
            # Get auto-detect setting
            auto_detect = self.config.get("mavlink_auto_detect", False)

            self.pixhawk = PixhawkConnection(
                link=self.config["mavlink_connection"], auto_detect=auto_detect
            )

            if self.pixhawk.connect():
                print("[PIXHAWK] [OK] Connected")
                if hasattr(self, "lblPixhawkStatus") and self.lblPixhawkStatus:
                    status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#00d4ff;">Connected</span></p></body></html>'
                    self.lblPixhawkStatus.setText(status_html)
                if hasattr(self, "lblModeStatus") and self.lblModeStatus:
                    mode_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#00d4ff;\">ONLINE</span></p></body></html>"
                    self.lblModeStatus.setText(mode_html)
            else:
                print("[PIXHAWK] [ERR] Connection failed")
                if hasattr(self, "lblPixhawkStatus") and self.lblPixhawkStatus:
                    status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">Disconnected</span></p></body></html>'
                    self.lblPixhawkStatus.setText(status_html)
                if hasattr(self, "lblModeStatus") and self.lblModeStatus:
                    mode_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#ff5555;\">OFFLINE</span></p></body></html>"
                    self.lblModeStatus.setText(mode_html)
        except Exception as e:
            print(f"[PIXHAWK] [ERR] Error: {e}")
            if hasattr(self, "lblPixhawkStatus") and self.lblPixhawkStatus:
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">Error</span></p></body></html>'
                self.lblPixhawkStatus.setText(status_html)

    def init_joystick(self):
        """Initialize joystick controller."""
        try:
            target = self.config.get("joystick_target")
            self.joystick = JoystickController(target_name=target)

            if self.joystick.is_connected():
                print(f"[JOYSTICK] [OK] Connected: {self.joystick.joystick_name}")
                if hasattr(self, "lblJoystickStatus") and self.lblJoystickStatus:
                    status_html = f'<html><head/><body><p><span style=" font-size:8pt; color:#00d4ff;">{self.joystick.joystick_name} - Ready</span></p></body></html>'
                    self.lblJoystickStatus.setText(status_html)
                # Update the joystick value label to show ONLINE
                if hasattr(self, "ui") and hasattr(self.ui, "lblJoystickValue"):
                    value_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#00d4ff;\">ONLINE</span></p></body></html>"
                    self.ui.lblJoystickValue.setText(value_html)
            else:
                print(f"[JOYSTICK]  No joystick connected")
                if hasattr(self, "lblJoystickStatus") and self.lblJoystickStatus:
                    status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ffa500;">Not Found</span></p></body></html>'
                    self.lblJoystickStatus.setText(status_html)
                # Update the joystick value label to show OFFLINE
                if hasattr(self, "ui") and hasattr(self.ui, "lblJoystickValue"):
                    value_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#ff5555;\">OFFLINE</span></p></body></html>"
                    self.ui.lblJoystickValue.setText(value_html)

        except Exception as e:
            print(f"[JOYSTICK] [ERR] Error: {e}")
            if hasattr(self, "lblJoystickStatus") and self.lblJoystickStatus:
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">Error</span></p></body></html>'
                self.lblJoystickStatus.setText(status_html)
            # Update the joystick value label to show OFFLINE
            if hasattr(self, "ui") and hasattr(self.ui, "lblJoystickValue"):
                value_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#ff5555;\">OFFLINE</span></p></body></html>"
                self.ui.lblJoystickValue.setText(value_html)

    @pyqtSlot(QPixmap)
    def update_camera_small(self, pixmap):
        """Update small camera display."""
        if hasattr(self, "lblCameraSmall") and self.lblCameraSmall:
            self.lblCameraSmall.setPixmap(
                pixmap.scaled(
                    self.lblCameraSmall.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    @pyqtSlot(QPixmap)
    def update_camera_main(self, pixmap):
        """Update main camera display."""
        if hasattr(self, "lblCameraMain") and self.lblCameraMain:
            self.lblCameraMain.setPixmap(
                pixmap.scaled(
                    self.lblCameraMain.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    @pyqtSlot(str)
    def update_camera_status_main(self, status):
        """Update main camera (port 8080) status label."""
        if hasattr(self, "lblCam1Status") and self.lblCam1Status:
            if status == "Connected":
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#00d4ff;">CAM 1 - Connected</span></p></body></html>'
            else:
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">CAM 1 - Disconnected</span></p></body></html>'
            self.lblCam1Status.setText(status_html)

    @pyqtSlot(str)
    def update_camera_status_cam2(self, status):
        """Update secondary camera (port 8081) status label."""
        if hasattr(self, "lblCam2Status") and self.lblCam2Status:
            if status == "Connected":
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#00d4ff;">CAM 2 - Connected</span></p></body></html>'
            else:
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">CAM 2 - Disconnected</span></p></body></html>'
            self.lblCam2Status.setText(status_html)

    @pyqtSlot(dict)
    def update_sensor_display(self, data):
        """Update sensor display with new data."""
        try:
            if hasattr(self, "lblDepth") and self.lblDepth:
                # Format for new UI with HTML styling
                depth_html = f'<html><head/><body><p><span style=" font-family:\'Consolas\'; font-size:16pt; font-weight:600; color:#00d4ff;">{data["depth"]:.1f}</span><span style=" font-family:\'Consolas\'; font-size:10pt; color:#808080;"> m</span></p></body></html>'
                self.lblDepth.setText(depth_html)

                # Also update the depth label in attitude section
                if hasattr(self, "lblDepthLabel") and self.lblDepthLabel:
                    depth_label_html = f'<html><head/><body><p><span style=" font-family:\'Consolas\'; font-size:11pt; font-weight:600; color:#00d4ff;">{data["depth"]:.1f}</span><span style=" font-size:9pt; color:#808080;"> m</span></p></body></html>'
                    self.lblDepthLabel.setText(depth_label_html)

            if hasattr(self, "lblTemperature") and self.lblTemperature:
                # Format for new UI with HTML styling
                temp_html = f'<html><head/><body><p><span style=" font-family:\'Consolas\'; font-size:16pt; font-weight:600; color:#00d4ff;">{data["temperature"]:.1f}</span><span style=" font-family:\'Consolas\'; font-size:10pt; color:#808080;"> °C</span></p></body></html>'
                self.lblTemperature.setText(temp_html)

            if hasattr(self, "lblPressure") and self.lblPressure:
                # Format for new UI with HTML styling
                # Convert hPa to bar (1 bar = 1000 hPa) for consistency with UI design
                pressure_bar = data["pressure"] / 1000.0
                pressure_html = f"<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:16pt; font-weight:600; color:#00d4ff;\">{pressure_bar:.2f}</span><span style=\" font-family:'Consolas'; font-size:10pt; color:#808080;\"> bar</span></p></body></html>"
                self.lblPressure.setText(pressure_html)

            # Force immediate UI update
            QApplication.processEvents()

        except Exception as e:
            print(f"[UI]  Error updating sensor display: {e}")

    def update_attitude_display(self, heading=None, pitch=None, roll=None):
        """Update the attitude/compass display with current orientation data."""
        try:
            # Update stored values
            if heading is not None:
                self.current_heading = heading
            if pitch is not None:
                self.current_pitch = pitch
            if roll is not None:
                self.current_roll = roll

            # Update compass widget
            if hasattr(self, "compass_widget") and self.compass_widget:
                self.compass_widget.heading = self.current_heading

            # Update heading display
            if hasattr(self, "lblHeadingDisplay") and self.lblHeadingDisplay:
                heading_html = f'<html><head/><body><p align="center"><span style=" font-family:\'Consolas\'; font-size:16pt; font-weight:600; color:#ea8a35;">{self.current_heading:.1f}°</span></p><p align="center"><span style=" font-size:9pt; color:#808080;">North</span></p></body></html>'
                self.lblHeadingDisplay.setText(heading_html)

            # Update pitch display
            if hasattr(self, "lblPitchValue") and self.lblPitchValue:
                pitch_color = "#00d4ff" if abs(self.current_pitch) < 15 else "#ffa500"
                pitch_html = f"<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:14pt; font-weight:600; color:{pitch_color};\">{self.current_pitch:.1f}°</span></p></body></html>"
                self.lblPitchValue.setText(pitch_html)

            # Update roll display
            if hasattr(self, "lblRollValue") and self.lblRollValue:
                roll_color = "#00d4ff" if abs(self.current_roll) < 15 else "#ffa500"
                roll_html = f"<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:14pt; font-weight:600; color:{roll_color};\">{self.current_roll:.1f}°</span></p></body></html>"
                self.lblRollValue.setText(roll_html)

        except Exception as e:
            print(f"[ATTITUDE] Error updating display: {e}")

    def update_attitude_from_pixhawk(self):
        """Fetch and update attitude data from Pixhawk."""
        try:
            # Only update if Pixhawk is connected
            if not self.pixhawk or not self.pixhawk.connected:
                return

            # Get attitude data from Pixhawk
            attitude_data = self.pixhawk.get_attitude()

            if attitude_data and attitude_data.get("connected"):
                # Update the display with new attitude data
                self.update_attitude_display(
                    heading=attitude_data.get("heading"),
                    pitch=attitude_data.get("pitch"),
                    roll=attitude_data.get("roll"),
                )
        except Exception as e:
            # Silently fail - this runs frequently
            pass

    @pyqtSlot(bool)
    def handle_sensor_status(self, connected):
        """Handle sensor connection status changes."""
        status_text = "Sensors: Connected" if connected else "Sensors: Disconnected"
        status_color = "#00d4ff" if connected else "#ff5555"
        print(f"[SENSORS] {'[OK]' if connected else '[ERR]'} {status_text}")

        # Update UI label with HTML formatting for new UI
        if hasattr(self, "lblSensorStatus") and self.lblSensorStatus:
            if connected:
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#00d4ff;">Connected</span></p></body></html>'
                self.lblSensorStatus.setText(status_html)
            else:
                status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">Disconnected</span></p></body></html>'
                self.lblSensorStatus.setText(status_html)

        # Update bottom bar network status based on PIXHAWK connection
        # (Pi is connected if Pixhawk MAVProxy is accessible)
        if hasattr(self, "conn_label") and self.conn_label:
            # Check Pi connection via Pixhawk MAVProxy status
            pi_connected = (
                self.pixhawk and self.pixhawk.check_connection()
                if hasattr(self, "pixhawk")
                else False
            )

            if pi_connected:
                pi_host = self.config.get(
                    "mavlink_connection", "tcp:raspberrypi.local:7000"
                )
                # Extract hostname from connection string
                if ":" in pi_host:
                    pi_host = (
                        pi_host.split(":")[1]
                        if len(pi_host.split(":")) > 1
                        else "raspberrypi.local"
                    )
                self.conn_label.setText(f" Network: {pi_host} (Connected)")
                self.conn_label.setStyleSheet("color: #00d4ff;")  # Cyan for connected
            else:
                self.conn_label.setText(" Network: Disconnected")
                self.conn_label.setStyleSheet("color: #ff5555;")  # Red for disconnected

    @pyqtSlot(str)
    def handle_camera_error(self, error_msg):
        """Handle camera errors."""
        print(f"[CAMERA ERROR] {error_msg}")

    def control_loop(self):
        """Main control loop - read joystick and send to Pixhawk."""
        try:
            if not self.joystick or not self.joystick.is_ready():
                return

            if not hasattr(self, "_last_pixhawk_check"):
                self._last_pixhawk_check = 0
                self._pixhawk_connected = False

            current_time = time.time()
            if current_time - self._last_pixhawk_check > 2.0:
                try:
                    self._pixhawk_connected = (
                        self.pixhawk and self.pixhawk.check_connection()
                    )
                except KeyboardInterrupt:
                    raise
                except Exception:
                    self._pixhawk_connected = False
                self._last_pixhawk_check = current_time

            if not self._pixhawk_connected:
                return

            joystick_state = self.joystick.read_joystick()
            channels = self.joystick.compute_thruster_channels(joystick_state)

            if self.armed:
                self.pixhawk.send_rc_channels_override(channels)
            else:
                if not hasattr(self, "_last_arm_warning"):
                    self._last_arm_warning = 0
                if time.time() - self._last_arm_warning > 5.0:
                    if any(abs(ch - 1500) > 10 for ch in channels):
                        print(
                            "[CONTROL]  Commands calculated but NOT sent - System not ARMED!"
                        )
                        print(
                            f"[CONTROL]  Click 'ARM THRUSTERS' button to enable thruster control"
                        )
                        self._last_arm_warning = time.time()

            self.thruster_values = channels

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[CONTROL]  Control loop error: {e}")

    def update_ui(self):
        """Periodic UI updates - display controller and thruster status."""
        try:
            if not hasattr(self, "_ui_cache_pixhawk"):
                self._ui_cache_pixhawk = False
                self._ui_cache_joystick = False

            # Update Pixhawk status with HTML formatting
            if hasattr(self, "lblPixhawkStatus") and self.lblPixhawkStatus:
                is_connected = getattr(self, "_pixhawk_connected", False)

                if is_connected:
                    status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#00d4ff;">Connected</span></p></body></html>'
                    self.lblPixhawkStatus.setText(status_html)
                else:
                    status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">Disconnected</span></p></body></html>'
                    self.lblPixhawkStatus.setText(status_html)

            # Update Pixhawk value label (ONLINE/OFFLINE)
            if hasattr(self, "lblModeStatus") and self.lblModeStatus:
                is_connected = getattr(self, "_pixhawk_connected", False)
                if is_connected:
                    mode_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#00d4ff;\">ONLINE</span></p></body></html>"
                    self.lblModeStatus.setText(mode_html)
                else:
                    mode_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#ff5555;\">OFFLINE</span></p></body></html>"
                    self.lblModeStatus.setText(mode_html)

            # Update Joystick status with HTML formatting
            if hasattr(self, "lblJoystickStatus") and self.lblJoystickStatus:
                if self.joystick and self.joystick.is_connected():
                    ready_text = (
                        "Ready" if self.joystick.is_ready() else "Calibrating..."
                    )
                    joystick_name = self.joystick.joystick_name or "Controller"
                    status_html = f'<html><head/><body><p><span style=" font-size:8pt; color:#00d4ff;">{joystick_name} - {ready_text}</span></p></body></html>'
                    self.lblJoystickStatus.setText(status_html)

                    # Also update the joystick value label to show ONLINE
                    if hasattr(self, "ui") and hasattr(self.ui, "lblJoystickValue"):
                        value_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#00d4ff;\">ONLINE</span></p></body></html>"
                        self.ui.lblJoystickValue.setText(value_html)
                else:
                    status_html = '<html><head/><body><p><span style=" font-size:8pt; color:#ff5555;">No Input Device</span></p></body></html>'
                    self.lblJoystickStatus.setText(status_html)

                    # Also update the joystick value label to show OFFLINE
                    if hasattr(self, "ui") and hasattr(self.ui, "lblJoystickValue"):
                        value_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#ff5555;\">OFFLINE</span></p></body></html>"
                        self.ui.lblJoystickValue.setText(value_html)

        except Exception as e:
            print(f"[UI]  Update error: {e}")

    def toggle_arm(self):
        """Toggle arm/disarm state."""
        if not self.pixhawk or not self.pixhawk.connected:
            print("[ARM] Cannot arm: Pixhawk not connected")
            return

        if self.armed:
            if self.pixhawk.disarm():
                self.armed = False
                if hasattr(self, "lblArmStatus"):
                    status_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#ffa500;\">IDLE</span></p></body></html>"
                    self.lblArmStatus.setText(status_html)
                if hasattr(self, "btnArm"):
                    self.btnArm.setText("🚀 ARM THRUSTERS")
                print("[ARM]  Disarmed")
        else:
            if self.pixhawk.arm():
                self.armed = True
                if hasattr(self, "lblArmStatus"):
                    status_html = "<html><head/><body><p><span style=\" font-family:'Consolas'; font-size:11pt; font-weight:600; color:#00d4ff;\">ARMED</span></p></body></html>"
                    self.lblArmStatus.setText(status_html)
                if hasattr(self, "btnArm"):
                    self.btnArm.setText("⚠️ DISARM")
                print("[ARM] [OK] Armed - CAUTION!")

    def emergency_stop(self):
        """Emergency stop - disarm and neutral all thrusters."""
        print("[EMERGENCY]  EMERGENCY STOP ACTIVATED")

        if self.pixhawk and self.pixhawk.connected:
            # Send neutral commands
            neutral = [1500] * 8
            self.pixhawk.send_rc_channels_override(neutral)

            # Disarm
            if self.armed:
                self.pixhawk.disarm()
                self.armed = False
                if hasattr(self, "lblArmStatus"):
                    self.lblArmStatus.setText("Armed: NO")
                    self.lblArmStatus.setStyleSheet("color: #FF8800;")
                if hasattr(self, "btnArm"):
                    self.btnArm.setText("ARM THRUSTERS")

    def send_manual_command(self, direction):
        """Send manual thruster command when button pressed."""
        # Check if Pixhawk is connected and armed
        if not self.pixhawk or not self.pixhawk.connected:
            print(f"[MANUAL]  Cannot send {direction} command: Pixhawk not connected")
            return

        if not self.armed:
            print(f"[MANUAL]  Cannot send {direction} command: System not armed")
            return

        # Create neutral channels (1500 = neutral)
        channels = [1500] * 8

        # Set thrust based on direction (using moderate power: 1600 or 1400)
        # Channel mapping (typical for ROV):
        # 0-3: Forward/lateral thrusters
        # 4-7: Vertical thrusters

        if direction == "forward":
            # Forward thrusters (channels 0 and 1)
            channels[0] = 1600  # Forward power
            channels[1] = 1600
            print("[MANUAL]  Forward command sent")

        elif direction == "backward":
            # Backward thrusters
            channels[0] = 1400  # Reverse power
            channels[1] = 1400
            print("[MANUAL]  Backward command sent")

        elif direction == "left":
            # Left strafe (differential thrust)
            channels[2] = 1400  # Left power
            channels[3] = 1600
            print("[MANUAL]  Left command sent")

        elif direction == "right":
            # Right strafe
            channels[2] = 1600  # Right power
            channels[3] = 1400
            print("[MANUAL]  Right command sent")

        # Send the command
        try:
            self.pixhawk.send_rc_channels_override(channels)
        except Exception as e:
            print(f"[MANUAL] [ERR] Error sending command: {e}")

    def stop_manual_command(self):
        """Stop manual command when button released (send neutral)."""
        if not self.pixhawk or not self.pixhawk.connected or not self.armed:
            return

        # Send neutral commands to stop thrusters
        neutral = [1500] * 8
        try:
            self.pixhawk.send_rc_channels_override(neutral)
            print("[MANUAL] ⏹ Manual command stopped (neutral)")
        except Exception as e:
            print(f"[MANUAL] [ERR] Error stopping command: {e}")

    def toggle_detection(self):
        """Toggle object detection on all cameras."""
        self.camera_detection_enabled = not self.camera_detection_enabled

        if self.camera_manager:
            self.camera_manager.toggle_all_detection(self.camera_detection_enabled)

        status = "ON" if self.camera_detection_enabled else "OFF"
        print(f"[DETECTION] Object detection: {status}")

    def open_camera_settings(self):
        """Open camera configuration dialog."""
        # Simple info dialog for camera settings
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Camera Settings",
            "Camera configuration is managed in config.json.\n\n"
            "Default pipelines:\n"
            "- Pipeline 0 (Camera 1): UDP port 5000\n"
            "- Pipeline 1 (Camera 2): UDP port 5001\n\n"
            "Edit config.json to modify camera streams.",
            QMessageBox.StandardButton.Ok,
        )

    def update_camera_config(self, camera_config):
        """Update camera configuration."""
        # Update config
        if "camera" not in self.config:
            self.config["camera"] = {}

        self.config["camera"]["pipeline0"] = camera_config["pipeline0"]
        self.config["camera"]["pipeline1"] = camera_config["pipeline1"]

        # Save config to file
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
        try:
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            print("[CONFIG] [OK] Camera configuration saved")
        except Exception as e:
            print(f"[CONFIG] [ERR] Failed to save: {e}")

    def restart_camera_feeds(self):
        """Restart camera feeds with new configuration."""
        print("[CAMERAS] Restarting camera feeds...")

        # Stop existing cameras
        if self.camera_manager:
            self.camera_manager.stop_all()
            self.camera_manager = None

        # Wait a moment
        import time

        time.sleep(0.5)

        # Start new cameras with updated config
        self.start_camera_feeds()

        print("[CAMERAS] [OK] Camera feeds restarted")

    def capture_image(self):
        """Capture image from main camera (port 8080)."""
        if not self.camera_manager:
            print("[MEDIA] [ERR] Camera manager not initialized")
            return

        try:
            # Use camera0 (port 8080) - the main camera feed
            camera = self.camera_manager.camera0
            frame = camera.get_frame()

            if frame is not None:
                filepath = self.media_manager.capture_image(frame, camera_id=0)
                if filepath:
                    from PyQt6.QtWidgets import QMessageBox

                    QMessageBox.information(
                        self, "Capture Complete", f"Image saved to:\n{filepath}"
                    )
                    print(f"[MEDIA] [OK] Image captured: {filepath}")
            else:
                print("[MEDIA]  No frame available for capture")
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self,
                    "Capture Failed",
                    "No camera frame available.\nPlease ensure camera is connected.",
                )
        except Exception as e:
            print(f"[MEDIA] [ERR] Capture failed: {e}")

    def toggle_recording(self):
        """Toggle video recording on/off from main camera (port 8080)."""
        if not self.camera_manager:
            print("[MEDIA] [ERR] Camera manager not initialized")
            return

        try:
            # Check if already recording
            if self.media_manager.is_recording():
                self.stop_recording()
                return

            # Use camera0 (port 8080) - the main camera feed
            camera = self.camera_manager.camera0
            frame = camera.get_frame()

            if frame is None:
                print("[MEDIA]  No frame available for recording")
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self,
                    "Recording Failed",
                    "No camera frame available.\nPlease ensure camera is connected.",
                )
                return

            # Get frame dimensions
            height, width = frame.shape[:2]

            if self.media_manager.start_recording(width, height, 30, camera_id=0):
                # Update button states
                if hasattr(self, "btnStartRecording"):
                    self.btnStartRecording.setText("⏹ STOP")
                    self.btnStartRecording.setStyleSheet(
                        """
                        QPushButton {
                            background-color: #d32f2f;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 10px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #f44336;
                        }
                    """
                    )

                self.recording_timer = QTimer(self)
                self.recording_timer.timeout.connect(self._write_recording_frame)
                self.recording_timer.start(33)  # ~30 FPS

                print("[MEDIA] [OK] Recording started")
        except Exception as e:
            print(f"[MEDIA] [ERR] Toggle recording failed: {e}")
            import traceback

            traceback.print_exc()

    def stop_recording(self):
        """Stop video recording."""
        if not self.media_manager.is_recording():
            print("[MEDIA]  No recording in progress")
            return

        try:
            if self.recording_timer:
                self.recording_timer.stop()
                self.recording_timer = None

            filepath = self.media_manager.stop_recording()

            # Restore button appearance
            if hasattr(self, "btnStartRecording"):
                self.btnStartRecording.setText("⏺ RECORD")
                self.btnStartRecording.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #FF8800;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #FFA040;
                    }
                """
                )

            if filepath:
                from PyQt6.QtWidgets import QMessageBox

                msg = f"Video saved to:\n{filepath}"
                QMessageBox.information(self, "Recording Complete", msg)
            print(f"[MEDIA] [OK] Recording stopped: {filepath}")
        except Exception as e:
            print(f"[MEDIA] [ERR] Stop recording failed: {e}")

    def load_gallery(self):
        """Load media files from the media folder and display in gallery."""
        try:
            from pathlib import Path
            from PyQt6.QtWidgets import (
                QFrame,
                QVBoxLayout,
                QLabel,
                QPushButton,
                QWidget,
            )
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPixmap
            import os

            print("[GALLERY] Loading gallery...")

            # Get filter selection
            filter_type = "All"
            if hasattr(self.ui, "cmbGalleryFilter"):
                filter_text = self.ui.cmbGalleryFilter.currentText()
                print(f"[GALLERY] Filter: {filter_text}")

                # Handle emoji-based filter text
                if "All" in filter_text or "📁" in filter_text:
                    filter_type = "All"
                elif "Image" in filter_text or "📷" in filter_text:
                    filter_type = "Images"
                elif "Video" in filter_text or "🎥" in filter_text:
                    filter_type = "Videos"
                else:
                    filter_type = filter_text  # Fallback to original text

                print(f"[GALLERY] Resolved filter type: {filter_type}")

            # Get media directory - use absolute path
            media_dir = Path(__file__).parent.parent.parent / "media"
            images_dir = media_dir / "images"
            videos_dir = media_dir / "videos"

            print(f"[GALLERY] Media dir: {media_dir}")
            print(f"[GALLERY] Images dir exists: {images_dir.exists()}")
            print(f"[GALLERY] Videos dir exists: {videos_dir.exists()}")

            # Ensure directories exist
            images_dir.mkdir(parents=True, exist_ok=True)
            videos_dir.mkdir(parents=True, exist_ok=True)

            # Collect media files - use set to avoid duplicates
            media_files_set = set()

            print(f"[GALLERY] Searching for files with filter_type: {filter_type}")

            if filter_type in ["All", "Images"]:
                print(f"[GALLERY] Scanning images directory: {images_dir}")
                if images_dir.exists():
                    # Use case-insensitive matching - only lowercase patterns
                    for ext in ["*.png", "*.jpg", "*.jpeg"]:
                        found_files = list(images_dir.glob(ext))
                        print(f"[GALLERY]   {ext}: {len(found_files)} files")
                        for f in found_files:
                            print(f"[GALLERY]     - {f.name}")
                            media_files_set.add((f, "image"))
                else:
                    print(f"[GALLERY] Images directory does not exist!")

            if filter_type in ["All", "Videos"]:
                print(f"[GALLERY] Scanning videos directory: {videos_dir}")
                if videos_dir.exists():
                    # Use case-insensitive matching - only lowercase patterns
                    for ext in ["*.mp4", "*.avi", "*.mov"]:
                        found_files = list(videos_dir.glob(ext))
                        print(f"[GALLERY]   {ext}: {len(found_files)} files")
                        for f in found_files:
                            media_files_set.add((f, "video"))
                else:
                    print(f"[GALLERY] Videos directory does not exist!")

            # Convert set back to list
            media_files = list(media_files_set)
            print(f"[GALLERY] Total unique media files found: {len(media_files)}")

            # Sort by modification time (newest first)
            media_files.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)

            # Check if gallery grid exists
            if not hasattr(self.ui, "gridLayout_gallery"):
                print("[GALLERY] [ERR] gridLayout_gallery not found in UI")
                return

            gallery_grid = self.ui.gridLayout_gallery

            # Remove all existing items except lblGalleryEmpty
            items_to_remove = []
            for i in range(gallery_grid.count()):
                item = gallery_grid.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # Don't delete the empty label
                    if widget.objectName() != "lblGalleryEmpty":
                        items_to_remove.append(widget)

            # Delete the collected items
            for widget in items_to_remove:
                gallery_grid.removeWidget(widget)
                widget.deleteLater()

            # Show/hide empty message
            if hasattr(self.ui, "lblGalleryEmpty"):
                if len(media_files) == 0:
                    try:
                        self.ui.lblGalleryEmpty.setText(
                            "No media files found.\nCapture images or record videos to see them here."
                        )
                        self.ui.lblGalleryEmpty.show()
                        print("[GALLERY] No media files - showing empty message")
                    except RuntimeError as e:
                        print(f"[GALLERY] Warning: Could not update empty label: {e}")
                    return
                else:
                    try:
                        self.ui.lblGalleryEmpty.hide()
                    except RuntimeError:
                        pass  # Label might have been deleted

            # Add media items to gallery
            items_per_row = 4
            for idx, (file_path, file_type) in enumerate(media_files):
                row = idx // items_per_row
                col = idx % items_per_row

                # Create gallery item frame
                frame = QFrame()
                frame.setMinimumSize(250, 200)
                frame.setMaximumSize(250, 200)
                frame.setObjectName(f"gallery_item_frame_{idx}")
                frame.setStyleSheet(
                    """
                    QFrame {
                        background-color: #1a1a1a;
                        border: 1px solid #2a2a2a;
                        border-radius: 8px;
                    }
                    QFrame:hover {
                        border: 1px solid #FF8800;
                        background-color: #252525;
                    }
                """
                )

                layout = QVBoxLayout(frame)
                layout.setContentsMargins(8, 8, 8, 8)
                layout.setSpacing(8)

                # Create preview label
                preview_label = QLabel()
                preview_label.setMinimumSize(234, 150)
                preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                preview_label.setStyleSheet(
                    "background-color: #0a0a0a; border-radius: 4px;"
                )

                if file_type == "image":
                    # Load and display image thumbnail
                    try:
                        pixmap = QPixmap(str(file_path))
                        if not pixmap.isNull():
                            scaled_pixmap = pixmap.scaled(
                                234,
                                150,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            preview_label.setPixmap(scaled_pixmap)
                            print(f"[GALLERY] Loaded image thumbnail: {file_path.name}")
                        else:
                            preview_label.setText("📷 Image")
                            print(f"[GALLERY] Failed to load image: {file_path.name}")
                    except Exception as img_err:
                        print(
                            f"[GALLERY] Error loading image {file_path.name}: {img_err}"
                        )
                        preview_label.setText("📷 Image")
                else:
                    # Video placeholder
                    preview_label.setText("🎥 Video")
                    preview_label.setStyleSheet(
                        """
                        background-color: #0a0a0a; 
                        border-radius: 4px;
                        color: #FF8800;
                        font-size: 24pt;
                    """
                    )

                layout.addWidget(preview_label)

                # Create title label with filename
                title_label = QLabel(file_path.name)
                title_label.setStyleSheet("color: #ffffff; font-size: 9pt;")
                title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                title_label.setWordWrap(True)
                layout.addWidget(title_label)

                # Make frame clickable to open file
                frame.mousePressEvent = (
                    lambda event, path=file_path: self.open_media_file(path)
                )

                # Add to grid
                gallery_grid.addWidget(frame, row, col)
                print(
                    f"[GALLERY] Added item {idx}: {file_path.name} at row={row}, col={col}"
                )

            print(f"[GALLERY] [OK] Loaded {len(media_files)} media files successfully")

        except Exception as e:
            print(f"[GALLERY] [ERR] Failed to load gallery: {e}")
            import traceback

            traceback.print_exc()

    def open_media_file(self, file_path):
        """Open media file with default system application."""
        try:
            import os
            import platform

            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                os.system(f'open "{file_path}"')
            else:  # Linux
                os.system(f'xdg-open "{file_path}"')

            print(f"[GALLERY] Opening: {file_path.name}")
        except Exception as e:
            print(f"[GALLERY] [ERR] Failed to open file: {e}")

    def _write_recording_frame(self):
        """Write frame to video during recording from main camera (port 8080)."""
        if not self.media_manager.is_recording():
            return

        try:
            # Use camera0 (port 8080) - the main camera feed
            camera = self.camera_manager.camera0
            frame = camera.get_frame()
            if frame is not None:
                self.media_manager.write_frame(frame)
        except Exception as e:
            print(f"[MEDIA] [ERR] Failed to write frame: {e}")

    def open_media_folder(self):
        """Open media folder in file explorer."""
        try:
            media_path = self.media_manager.get_media_path()
            import subprocess
            import platform

            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{media_path}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", media_path])
            else:
                subprocess.Popen(["xdg-open", media_path])

            print(f"[MEDIA] [OK] Opened media folder: {media_path}")
        except Exception as e:
            print(f"[MEDIA] [ERR] Failed to open folder: {e}")

    def closeEvent(self, event):
        """Clean up on window close."""
        print("[MARINER] Shutting down...")

        # Stop timers
        self.control_timer.stop()
        self.ui_update_timer.stop()

        if self.recording_timer:
            self.recording_timer.stop()

        # Stop media recording if active
        if self.media_manager:
            self.media_manager.stop()

        # Disarm if armed
        if self.armed and self.pixhawk:
            self.pixhawk.disarm()

        # Close all connections
        if self.camera_manager:
            self.camera_manager.stop_all()

        if self.sensor_worker:
            self.sensor_worker.stop()

        if self.pixhawk:
            self.pixhawk.close()

        if self.joystick:
            self.joystick.close()

        print("[MARINER] [OK] Shutdown complete")
        event.accept()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("UIU MARINER ROV Control")
    app.setOrganizationName("UIU")

    # Create and show main window
    window = MarinerROVControl()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
