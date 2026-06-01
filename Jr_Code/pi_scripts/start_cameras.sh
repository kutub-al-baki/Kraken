#!/bin/bash
# Start both camera servers on Raspberry Pi
# Camera 0 on port 8080, Camera 1 on port 8081

echo "=========================================="
echo "UIU MARINER - Camera Servers"
echo "=========================================="

# Kill any existing camera processes
echo "Stopping any existing camera servers..."
pkill -f "pi_camera_server.py"
sleep 1

# Start Camera 0 on port 8080
echo "Starting Camera 0 on port 8080..."
python3 /home/pi/mariner/pi_scripts/pi_camera_server.py 0 8080 > /tmp/camera0.log 2>&1 &
CAM0_PID=$!
echo "Camera 0 PID: $CAM0_PID"

# Wait a bit before starting second camera
sleep 2

# Start Camera 1 on port 8081
echo "Starting Camera 1 on port 8081..."
python3 /home/pi/mariner/pi_scripts/pi_camera_server.py 1 8081 > /tmp/camera1.log 2>&1 &
CAM1_PID=$!
echo "Camera 1 PID: $CAM1_PID"

echo ""
echo "=========================================="
echo "Camera servers started!"
echo "Camera 0: http://$(hostname -I | awk '{print $1}'):8080/video_feed"
echo "Camera 1: http://$(hostname -I | awk '{print $1}'):8081/video_feed"
echo "=========================================="
echo ""
echo "Logs:"
echo "  Camera 0: tail -f /tmp/camera0.log"
echo "  Camera 1: tail -f /tmp/camera1.log"
echo ""
echo "To stop: pkill -f pi_camera_server.py"
