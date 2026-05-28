# Pi Scripts - Raspberry Pi Server Components

This folder contains all the server-side code that runs on the Raspberry Pi.

## Quick Start

Deploy from Ground Station:

```powershell
.\deploy_to_pi.ps1
```

Then on Pi:

```bash
cd ~/mariner/pi_scripts
./start_all_services.sh
```

## Files

### Camera Servers

- **`pi_camera_server.py`** - MJPEG camera server using Flask + Picamera2
- **`start_cameras.sh`** - Start both cameras on ports 8080 and 8081

### Sensor & MAVLink

- **`pi_sensor_server.py`** - BMP388 depth/temperature sensor server
- **`pi_mavproxy_server.py`** - MAVLink relay between Pixhawk and Ground Station

### Startup Scripts

- **`start_all_services.sh`** - Start all services (cameras, sensors, mavproxy)
- **`stop_all_services.sh`** - Stop all services

### Utilities

- **`detect_cameras.py`** - Detect available Pi cameras
- **`detect_pixhawk.py`** - Detect Pixhawk serial connection
- **`get_ground_station_ip.py`** - Auto-detect Ground Station IP

### Legacy (Optional)

- **`cam.py`** - Original working camera code
- **`usb_camera_server.py`** - USB camera support
- Other autostart scripts

## Ports

- **8080** - Camera 0 MJPEG stream
- **8081** - Camera 1 MJPEG stream
- **5002** - Sensor telemetry (TCP)
- **7000** - MAVLink relay (TCP)

## Usage

**Start everything:**

```bash
./start_all_services.sh
```

**View logs:**

```bash
screen -ls              # List running services
screen -r cam0          # View camera 0 log
screen -r cam1          # View camera 1 log
screen -r sensors       # View sensor log
screen -r mavproxy      # View MAVLink log
# Press Ctrl+A then D to detach
```

**Stop everything:**

```bash
./stop_all_services.sh
```

## Testing

Test cameras in browser:

- http://raspberrypi.local:8080/video_feed
- http://raspberrypi.local:8081/video_feed
