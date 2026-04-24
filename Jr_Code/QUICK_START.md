<!-- dos2unix start_all_services.sh  -->
<!-- dos2unix stop_all_services.sh  -->

# Mariner ROV - Quick Start Guide

## Ethernet Setup (for Underwater Tether)

**Configure static IP on Raspberry Pi for Ethernet connection:**

```bash
# On Raspberry Pi (using NetworkManager)
sudo nmcli connection modify "Wired connection 1" ipv4.addresses 192.168.1.100/24
sudo nmcli connection modify "Wired connection 1" ipv4.gateway 192.168.1.1
sudo nmcli connection modify "Wired connection 1" ipv4.dns "8.8.8.8"
sudo nmcli connection modify "Wired connection 1" ipv4.method manual

# Apply changes
sudo nmcli connection down "Wired connection 1"
sudo nmcli connection up "Wired connection 1"

# Verify
ifconfig eth0
# Should show: inet 192.168.1.100
```

**Configure static IP on Ground Station PC:**

Windows:

1. Control Panel → Network Connections → Ethernet adapter
2. Right-click → Properties → IPv4
3. Use this IP address:
   - IP: `192.168.1.10`
   - Subnet: `255.255.255.0`
   - Gateway: `192.168.1.1`

**Test connection:**

```bash
ping 192.168.1.100
```

## Deploy to Raspberry Pi

**One command to sync everything:**

```powershell
# On Windows
.\deploy_to_pi.ps1
```

Or with custom Pi address (Ethernet):

```powershell
.\deploy_to_pi.ps1 -PiHost 192.168.1.100
```

**Note:** If using Ethernet tether, make sure both Pi and Ground Station have static IPs configured first (see Ethernet Setup above).

This will automatically:

- Sync all pi_scripts to Pi
- Create necessary directories
- Make scripts executable

## First Time Setup on Pi

After deployment, SSH into Pi and install dependencies:

```bash
ssh pi@raspberrypi.local

# Install Python dependencies
pip3 install pymavlink pyserial flask picamera2 opencv-python-headless numpy

# Optional: Setup autostart on boot
sudo cp ~/mariner/pi_scripts/mariner_autostart.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mariner_autostart.service
```

## Running on Pi

**Start all services:**

```bash
cd ~/mariner/pi_scripts
./start_all_services.sh
```

**Or start individual services:**

```bash
# Cameras only
./start_cameras.sh

# Check what's running
screen -ls
```

**View logs:**

```bash
# View camera logs
screen -r cam0
screen -r cam1

# View other services
screen -r sensors
screen -r mavproxy

# Detach from screen: Ctrl+A then D
```

**Stop all services:**

```bash
pkill -f pi_camera_server
pkill -f pi_sensor_server
pkill -f pi_mavproxy_server
```

## On Ground Station (Windows/Mac)

```bash
# Run GUI application
python launch_mariner.py
```

**Expected GUI indicators when Pi is running:**

- Camera feeds: Live video from 2 cameras
- Sensor data: Depth, temperature, pressure
- Connection status: Connected/Disconnected
- Thruster status: Armed/Disarmed indicator

## Troubleshooting

| Issue                 | Solution                                                        |
| --------------------- | --------------------------------------------------------------- |
| Pi not connecting     | Check: `cd ~ && bash pi_scripts/pi_autostart_all.sh status`     |
| Cameras not streaming | Restart cameras: Kill process on Pi and run start command again |
| No sensor data        | Check I2C connection: `i2cdetect -y 1` on Pi                    |
| Pixhawk not detected  | Check serial: `ls -la /dev/ttyAMA0` on Pi                       |

## Port Summary

- **MAVLink TCP**: 7000 (Ground Station ↔ Pi)
- **Sensor TCP**: 5002 (BMP388 telemetry)
- **Camera HTTP**: 8080, 8081 (MJPEG video streams via Flask)
  - Camera 0: http://raspberrypi.local:8080/video_feed
  - Camera 1: http://raspberrypi.local:8081/video_feed

## Camera System

Uses **Flask + Picamera2** for MJPEG streaming over HTTP:

- Camera 0: http://raspberrypi.local:8080/video_feed
- Camera 1: http://raspberrypi.local:8081/video_feed

Test in any web browser!

Done! 🚀
