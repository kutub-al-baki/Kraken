# UIU MARINER - ROV Ground Station Control System# UIU MARINER - ROV Control System

**Professional Ground Station Control Software for the UIU MARINER Underwater Robotics Project**## 🌊 Overview

---Complete software solution for controlling an underwater ROV (Remotely Operated Vehicle) using:

## Overview- **Hardware**: Pixhawk flight controller running ArduSub firmware

- **Communication**: MAVLink protocol over UDP/TCP/Serial

UIU MARINER is a ground-based control system for operating an 8-thruster autonomous underwater vehicle (AUV). The system communicates with the ROV via a Raspberry Pi intermediary, enabling real-time thruster control, telemetry monitoring, and camera feeds.- **Input**: Xbox 360 / compatible gamepad

- **Interface**: PyQt6 desktop application

### System Architecture

## 🏗️ System Architecture

````

Ground Station (Windows PC)```

    ├── PyQt6 GUI (Views)┌─────────────────┐

    ├── Control Logic (Controllers)│   PC Software   │

    ├── Data Models (Models)│  (This Repo)    │

    └── Communication Services (Services)├─────────────────┤

        ↓ TCP/UDP│ • PyQt6 GUI     │

Raspberry Pi (Network Bridge)│ • Joystick      │

    ├── MAVLink Relay Server (port 7000)│ • MAVLink       │

    └── Serial (/dev/ttyAMA0)└────────┬────────┘

        ↓ Serial UART @ 57600 baud         │ Ethernet UDP

Pixhawk Flight Controller         │ 192.168.0.104:14550

    ├── ArduSub Firmware┌────────▼────────┐

    └── RC Channels Output (8x Thrusters + 8x ESCs)│  Raspberry Pi   │

```│   (Optional)    │

└────────┬────────┘

### Key Features         │ UART/TELEM2

┌────────▼────────┐

- **Real-time Thruster Control**: 8-channel RC override via MAVLink protocol│    Pixhawk      │

- **Xbox Controller Support**: Direct joystick input mapping to thruster channels│  ArduSub v4.5+  │

- **Live Telemetry**: Altitude, depth, heading, battery status└────────┬────────┘

- **Dual Camera Feeds**: MJPEG HTTP streaming with Flask + Picamera2         │ PWM Signals

- **Professional MVC Architecture**: Clean separation of concerns┌────────▼────────┐

- **Auto-connect**: Automatically discovers Pi and establishes MAVLink connection│  8x Thrusters   │

- **Mock Mode**: Test GUI without hardware│   + ESCs        │

└─────────────────┘

---```



## Installation## 📦 Installation



### Prerequisites### 1. Prerequisites



- **Windows 10/11** (64-bit)- **Python 3.8+** (3.10 recommended)

- **Python 3.8+**- **Xbox 360 Controller** or compatible gamepad

- **Virtual Environment** (recommended)- **Pixhawk** running ArduSub firmware (v4.5.6 or later)

- **Network connection** to Pixhawk/Raspberry Pi (camera streams work via HTTP)



### Setup### 2. Install Dependencies



1. **Clone Repository**```powershell

   ```powershell# Clone or navigate to this directory

   git clone https://github.com/muddasirfaiyaj66/uiu-mariner-1.gitcd "F:\Web Development\uiu-mariner\uiu-mariner-1"

   cd uiu-mariner-1

   ```# Create virtual environment (recommended)

python -m venv .venv

2. **Create Virtual Environment**

   ```powershell# Activate virtual environment

   python -m venv .venv.\.venv\Scripts\Activate.ps1

   .\.venv\Scripts\Activate.ps1

   ```# Install required packages

pip install -r requirements.txt

3. **Install Dependencies**```

   ```powershell

   pip install -r requirements.txt### 3. Configure Connection

````

Edit `config.json`:

4. **Configure Network**

   - Edit `config.json` with your Pi's IP or hostname```json

   - Default: `tcp:raspberrypi.local:7000`{

"mavlink_connection": "udp:192.168.0.104:14550",

--- "joystick_target": "xbox",

"update_rate_hz": 10

## Usage}

````

### Starting the Application

**Connection String Examples:**

```powershell

# Activate virtual environment- UDP: `"udp:192.168.0.104:14550"` (default)

.\.venv\Scripts\Activate.ps1- TCP: `"tcp:10.42.0.185:5760"`

- Serial: `"serial:/dev/ttyUSB0:57600"` (Linux) or `"serial:COM3:57600"` (Windows)

# Launch application

python launch_mariner.py## 🚀 Usage

````

### Launch Application

### Main Controls

````powershell

| Action | Method |# From project root

|--------|--------|python src/ui/rovControlApp.py

| **Connect to ROV** | Click "Connect" or auto-connect on launch |```

| **Arm/Disarm** | GUI button or Xbox "X" button |

| **Forward/Reverse** | Left stick Y-axis |Or use the launcher script:

| **Yaw Left/Right** | Left stick X-axis |

| **Vertical Up/Down** | Right stick Y-axis |```powershell

| **Mode Switch** | ROV modes (Manual/Stabilize/Acro) |.\launch.ps1

````

### Configuration

### Control Layout (Xbox 360)

Edit `config.json` to customize:

**Left Stick:**

```json

{- **Y-Axis**: Forward/Backward (Thrusters 1, 8)

  "mavlink_connection": "tcp:raspberrypi.local:7000",- **X-Axis**: Left/Right Rotation (Thrusters 2, 5)

  "joystick_target": null,

  "camera": {**Right Stick:**

    "pipeline0": "udpsrc port=5000 ! ...",

    "pipeline1": "udpsrc port=5001 ! ..."- **Y-Axis**: Up/Down (Thrusters 3, 4, 6, 7)

  },

  "sensors": {**Buttons:**

    "host": "raspberrypi.local",

    "port": 5002,- **Start**: Emergency Stop (all thrusters to neutral)

    "mock_mode": false,- **Back**: Reserved

    "auto_connect": true- **A/B/X/Y**: Reserved for future features

  }

}### GUI Controls

```

1. **Connect**: Click "Reconnect Pixhawk" if connection fails

---2. **Set Mode**: Choose MANUAL or STABILIZE mode

3. **Arm**: Click "ARM THRUSTERS" (thrusters will remain at neutral until joystick input)

## Project Structure4. **Control**: Use joystick to pilot ROV

5. **Emergency**: Click "EMERGENCY STOP" or press Start button to immediately stop all thrusters

```

src/## 🔧 Configuration

├── models/                   # Data models and state management

│   ├── mavlinkModel.py      # Pixhawk state and telemetry### Thruster Channel Mapping

│   └── __init__.py

├── views/                    # PyQt6 GUI componentsCurrent configuration (ArduSub standard frame):

│   ├── mainWindow.py        # Main application window

│   ├── workers/             # QThread workers| Channel | Function         | Thruster Position |

│   │   ├── cameraWorker.py  # Video stream processing| ------- | ---------------- | ----------------- |

│   │   ├── sensorWorker.py  # Telemetry collection| 1       | Forward/Backward | Left Front        |

│   │   └── __init__.py| 2       | Left/Right Yaw   | Right Lateral     |

│   ├── main_window.ui       # Qt Designer layout| 3       | Up/Down          | Front Vertical    |

│   └── __init__.py| 4       | Up/Down          | Rear Vertical     |

├── controllers/              # Business logic| 5       | Left/Right Yaw   | Left Lateral      |

│   ├── rovController.py     # Main orchestration| 6       | Up/Down          | Front Vertical    |

│   ├── joystickController.py # Xbox input mapping| 7       | Up/Down          | Rear Vertical     |

│   └── __init__.py| 8       | Forward/Backward | Right Front       |

├── services/                 # Communication & utilities

│   ├── mavlinkConnection.py # Pixhawk MAVLink protocol**Note**: If your thruster configuration differs, modify `compute_thruster_channels()` in `src/controllers/joystickController.py`.

│   ├── portScanner.py       # Serial port detection

│   └── __init__.py### Network Setup

└── __init__.py

**Direct Connection (PC ↔ Pixhawk):**

config.json                   # Runtime configuration

launch_mariner.py             # Application entry point1. Connect Pixhawk USB to PC

requirements.txt              # Python dependencies2. Check COM port in Device Manager

README.md                     # This file3. Use `"serial:COM3:57600"` in config.json

```

**Via Raspberry Pi:**

---

1. Connect PC and Pi to same network

## Architecture Details2. Configure Pi as MAVLink router (see `docs/pi-setup.md`)

3. Use `"udp:<PI_IP>:14550"` in config.json

### Model-View-Controller (MVC) Pattern

## 📁 Project Structure

**Models** (`src/models/`)

- Store application state (telemetry, connection status, RC channels)```

- Independent of UI and network logicmariner-software-1.0/

- Example: `MAVLinkState` holds all Pixhawk vehicle data├── src/

│ ├── connections/

**Views** (`src/views/`)│ │ └── mavlinkConnection.py # MAVLink communication

- PyQt6 GUI components│ ├── controllers/

- Workers (QThread) for async operations│ │ └── joystickController.py # Joystick input processing

- Display model data to user│ ├── ui/

│ │ └── rovControlApp.py # Main GUI application

**Controllers** (`src/controllers/`)│ └── resources/ # Images, icons (future)

- Orchestrate between views, models, and services├── media/

- Example: `ROVController` handles arm/disarm, mode switching│ ├── images/

- Emit signals for UI updates│ └── videos/

├── config.json # Configuration file

**Services** (`src/services/`)├── requirements.txt # Python dependencies

- Low-level communication (MAVLink, serial)├── launch.ps1 # Windows launcher script

- Network operations├── launch.sh # Linux launcher script

- System utilities└── README.md # This file

````

### Communication Flow

## 🛠️ Troubleshooting

1. **Startup**: `launch_mariner.py` → `MarinerApp` → `ROVController`

2. **Connect**: `ROVController.connect_to_pixhawk()` → `PixhawkConnection` → TCP to Pi### "No joystick detected"

3. **Control Loop**: Joystick input → RC channel values → `send_rc_channels_override()`

4. **Telemetry**: Pixhawk HEARTBEAT → parsed by controller → UI update signal- Ensure controller is plugged in via USB

- Press Xbox button to power on

---- Check Windows Game Controllers settings



## Raspberry Pi Integration### "Connection failed"



### Required Pi Services- Verify IP address and port in `config.json`

- Ensure Pixhawk/Pi is powered on and connected to network

The ROV's Raspberry Pi must run:- Check firewall settings (allow UDP port 14550)

- Test with QGroundControl to verify MAVLink connection

1. **MAVLink Relay Server** (`pi_scripts/pi_mavproxy_server.py`)

   - Bridges ground station TCP → Pixhawk serial### "Cannot arm"

   - Relays all MAVLink messages bidirectionally

   - Runs on port 7000- Ensure Pixhawk is receiving valid MAVLink heartbeat

- Check ArduSub pre-arm checks in QGroundControl

2. **Camera Server** (`pi_scripts/pi_camera_server.py`) - **NEW MJPEG Implementation!**

   - Flask + Picamera2 based HTTP streaming
   - Simple, reliable, browser-testable
   - Streams MJPEG video via HTTP (ports 8080, 8081)
   - Separate instances for each camera
   - See `pi_scripts/CAMERA_README.md` for details

### Thrusters not responding



3. **Sensor Server** (`pi_scripts/pi_sensor_server.py`)- Confirm vehicle is ARMED (status shows "Armed: YES")

   - Sends telemetry (depth, temperature, pressure) via TCP- Check ESC calibration in QGroundControl

   - Runs on port 5002- Verify thruster channel mapping matches your physical setup

- Ensure joystick axes are moving (check "Joystick Input" panel)

### Pi Setup & Deployment

**Deploy to Pi (one command):**

```powershell
# Windows
.\deploy_to_pi.ps1

# Or with custom host
.\deploy_to_pi.ps1 -PiHost 192.168.1.100
```

This syncs all `pi_scripts` to the Raspberry Pi automatically.

**First time on Pi:**
```bash
ssh pi@raspberrypi.local
pip3 install pymavlink pyserial flask picamera2 opencv-python-headless numpy
cd ~/mariner/pi_scripts
./start_all_services.sh
```

## 🧪 Testing Without Hardware

To test joystick input without connecting to Pixhawk:

1. Comment out `self.connect_pixhawk()` in `mainWindow.py`
2. Run application
3. Move joystick and observe thruster values update in GUI

---

## 🔐 Safety Features

## MAVLink Protocol

- **Emergency Stop**: Immediately disarms and neutralizes all thrusters

### Supported MAVLink Messages- **Arm Guard**: Thrusters cannot activate without explicit arming

- **Dead Zone**: Small joystick movements ignored (±3%)

| Message | Purpose | Parameters |- **Value Clamping**: All PWM values clamped to 1000-2000 range

|---------|---------|------------|- **Connection Monitoring**: Control disabled if Pixhawk disconnects

| **HEARTBEAT** | Connection keep-alive | sys_id, component_id, mode |

| **RC_CHANNELS_OVERRIDE** | Send 8 thruster commands | channels 1-8 (1000-2000 µs) |## 📚 Additional Resources

| **COMMAND_LONG** | ARM/DISARM, Mode change | command_id + parameters |

| **SERVO_OUTPUT_RAW** | Read current servo outputs | 8x servo pulse widths |- [ArduSub Documentation](https://www.ardusub.com/)

| **SYS_STATUS** | Battery and health data | voltage, current, battery % |- [MAVLink Protocol](https://mavlink.io/en/)

| **GLOBAL_POSITION_INT** | GPS/IMU position data | lat, lon, alt, heading |- [Pygame Documentation](https://www.pygame.org/docs/)

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)

### Thruster Channel Mapping

## 🤝 Team UIU HYDRA

| Channel | Function | Thruster Location |

|---------|----------|------------------|Developed for the UIU MARINER autonomous underwater vehicle project.

| 1 | Forward/Backward | Left Front |

| 2 | Yaw Left | Left Lateral |**Version**: 1.0

| 3-4 | Vertical Up | Front L/R |**Last Updated**: November 2025

| 5 | Yaw Right | Right Lateral |**License**: MIT

| 6-7 | Vertical Down | Rear L/R |

| 8 | Forward/Backward | Right Front |---



**PWM Values**: `1000` = full reverse, `1500` = neutral, `2000` = full forward## Quick Start Checklist



---- [ ] Python 3.8+ installed

- [ ] Dependencies installed (`pip install -r requirements.txt`)

## Troubleshooting- [ ] Xbox controller connected

- [ ] `config.json` configured with correct IP/port

### Connection Issues- [ ] Pixhawk powered on and connected

- [ ] ArduSub firmware v4.5.6+ installed

**"Pixhawk not connected"**- [ ] Run `python src/ui/rovControlApp.py`

- Verify Pi is running: `ping raspberrypi.local`- [ ] Verify Pixhawk connection (green status)

- Check Pi MAVLink relay: `ps aux | grep pi_mavproxy`- [ ] Set mode to MANUAL

- Verify serial: `ls -la /dev/ttyAMA0`- [ ] ARM thrusters

- [ ] Test joystick control

**"No telemetry data"**- [ ] Emergency stop accessible!

- Confirm Pixhawk is powered

- Check firmware: AUTOPILOT_VERSION message**Happy Diving! 🌊🤖**

- Restart relay: `pkill -f pi_mavproxy_server.py`

**"Thrusters not responding"**
- Verify ESC arming (red LED)
- Check RC values are 1000-2000
- Confirm SERVO_OUTPUT_RAW messages

### Performance Optimization

- **High CPU**: Reduce camera resolution in config
- **Network Lag**: Use Ethernet or dual-band WiFi
- **Jittery Video**: Adjust GStreamer framerate

---

## Development

### Adding New Features

1. **UI Component**: Edit `src/views/mainWindow.py`
2. **State**: Extend `src/models/mavlinkModel.py`
3. **Logic**: Add to `src/controllers/rovController.py`
4. **Communication**: Extend `src/services/mavlinkConnection.py`

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to public methods
- Use logging module

---

## Dependencies

### Python Packages
- **PyQt6** - GUI framework
- **pymavlink** - MAVLink protocol
- **pygame** - Joystick input
- **opencv-python** - Image processing
- **numpy** - Numerical computing

### System Libraries
- **GStreamer** (for video)

Install with:
```powershell
pip install -r requirements.txt
````

---

## Hardware Requirements

**Ground Station:**

- Windows 10/11 PC
- 4GB RAM minimum
- USB for Xbox controller

**Raspberry Pi 4:**

- 4GB RAM
- 32GB microSD
- UART to Pixhawk

**Pixhawk 4:**

- ArduSub firmware
- 8x PWM ESC outputs

---

## Version History

- **v2.0** (Current) - MVC refactor, professional architecture
- **v1.0** - Initial release

---

**Last Updated:** November 2025  
**Project:** UIU MARINER Team
