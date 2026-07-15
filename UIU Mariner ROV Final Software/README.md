# UIU MARINER - Advanced ROV Control Suite v5.0.0
Professional-grade GCS for Underwater Robotics Systems

UIU MARINER is a high-performance, web-based Ground Station Control (GCS) system designed for 8-thruster ROVs. It replaces standard ArduSub interfaces with a custom, high-frequency software mixer and a modern, high-fidelity dashboard.

![ROV GCS Dashboard Screenshot](media/dashboard_preview.jpg)

---

## 🌟 Key Features

### 🎮 **High-Precision Control**
Full 6-DOF (Degrees of Freedom) support for Xbox 360, Xbox One, and PlayStation controllers. Our custom joystick engine is optimized for high-pressure underwater maneuvers with zero-lag response.

### 🚀 **Advanced Software Mixing**
Bypass the limitations of traditional flight controllers with our Python-based mixing algorithm. This allows for custom thruster arrangements and on-the-fly bias corrections for asymmetric frame designs.

### ⚓ **Cascaded PID Depth Hold**
Experience rock-solid vertical stability with our dual-stage cascaded PID controller. It works alongside intelligent signal filtering (Median + EMA) to eliminate sensor noise and maintain depth with millimeter precision.

### 📹 **Integrated Vision Suite**
Live low-latency WebRTC streaming from multiple onboard cameras. Features include:
- Instant camera switching
- Smooth 1.0x to 4.0x Digital Zoom
- One-click high-resolution photo capture
- Internal MP4 video recording at 30 FPS
- OpenCV-based object detection with overlay

### 🌐 **Modern Web Ecosystem**
Built on a high-speed **FastAPI** backend and a reactive **React + Vite** frontend. The interface is clean, sleek, and fully responsive for various display sizes.

---

## 🛠️ Quick Start

Ensure you have [Python 3.9+](https://python.org) and [Node.js 18+](https://nodejs.org) installed.

### 1. Installation
```powershell
# Setup virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install core system
pip install -r requirements.txt

# Install frontend
cd frontend
npm install
cd ..
```

### 2. Deployment
To launch the entire platform (Backend + Frontend + GCS):
```powershell
python launch_mariner.py
```
*Wait for the [WEB] startup messages. The dashboard will automatically open in your default browser.*

To launch the full vehicle stack first, then the ground station UI:
```powershell
python start_full_system.py
```
This SSHes into the Raspberry Pi, starts the Pi services, then launches the local FastAPI + React ground station.

---

## 📖 In-Depth Documentation

For detailed information on system configuration and operation, please refer to the following guides:

1.  **[Physical Hardware Setup](docs/HARDWARE_SETUP.md)**: Simplified guide for connecting and configuring the Pi and Pixhawk.
2.  **[System Setup Guide](docs/SETUP.md)**: Hardware requirements, Ground Station installation, and software launch.
2.  **[Controller Reference](docs/CONTROLLER.md)**: Joystick mappings, advanced mixing theory, and cascaded PID tuning.
3.  **[API & Integration](docs/API.md)**: Real-time WebSocket schema and REST endpoint reference for custom extensions.
4.  **[Research & Architecture](docs/RESEARCH_PAPER.md)**: Detailed academic paper on the cascaded PID and universal mixing theory.
5.  **[Competitive Advantage](docs/COMPETITIVE_ADVANTAGE.md)**: Why UIU MARINER is better than QGroundControl or Mission Planner.
6.  **[Computer Vision & AI](docs/COMPUTER_VISION.md)**: Details on the 5-mode intelligent vision and measurement engine.
6.  **[Camera Setup Protocol](docs/CAMERA_SETUP.md)**: Current Raspberry Pi WebRTC camera server and launch flow.

---

## ⚡ Safety & Reliability
- **Emergency Stop System**: Hardware-zeroing with instant response (Button 2 / X).
- **Redundant State Management**: Backend/Frontend keeps thruster states synchronized in real-time.
- **Pre-Arm Safety**: Multi-stage arming process with visual indicators on the HUD.

---

© 2026 UIU Underwater Robotics And Automation Crew
A product of the **UIU-AURA-CREW** Engineering Team
Professional Series ROV Solutions
