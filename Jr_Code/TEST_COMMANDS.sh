#!/bin/bash
# Test Commands for Raspberry Pi

echo "=========================================="
echo "MARINER ROV - QUICK TEST COMMANDS"
echo "=========================================="
echo ""

# Step 1: Check files copied
echo "1. CHECK PROJECT FILES:"
echo "   ls -la /opt/mariner/"
echo ""

# Step 2: Check requirements
echo "2. INSTALL DEPENDENCIES:"
echo "   cd /opt/mariner"
echo "   pip install -r requirements.txt"
echo "   pip install MAVProxy"
echo ""

# Step 3: Make executable
echo "3. MAKE SCRIPTS EXECUTABLE:"
echo "   chmod +x /opt/mariner/pi_scripts/pi_autostart_all.sh"
echo ""

# Step 4: Test Pixhawk Connection
echo "4. TEST PIXHAWK (before startup):"
echo "   ls -la /dev/ttyAMA0"
echo "   python3 -c \"import serial; s=serial.Serial('/dev/ttyAMA0', 57600, timeout=1); print('Pixhawk connected')\""
echo ""

# Step 5: START ALL SERVICES
echo "5. START ALL SERVICES:"
echo "   bash /opt/mariner/pi_scripts/pi_autostart_all.sh start"
echo "   # Wait 10-15 seconds..."
echo ""

# Step 6: Check status
echo "6. CHECK SERVICES RUNNING:"
echo "   bash /opt/mariner/pi_scripts/pi_autostart_all.sh status"
echo ""

# Step 7: Check logs
echo "7. VIEW LOGS (in separate terminals):"
echo "   tail -f /opt/mariner/logs/sensor_server.log"
echo "   tail -f /opt/mariner/logs/camera_server.log"
echo "   tail -f /opt/mariner/logs/mavproxy_relay.log"
echo ""

# Step 8: Test connections
echo "8. TEST TCP CONNECTIONS:"
echo "   netstat -tulpn | grep python3"
echo "   netstat -tulpn | grep mavproxy"
echo ""

# Step 9: Test from ground station
echo "9. ON GROUND STATION (Windows):"
echo "   python launch_mariner.py"
echo "   # Check if cameras and sensor data appear in GUI"
echo ""

# Step 10: Test manual control
echo "10. TEST MANUAL CONTROL:"
echo "   # Connect joystick to Windows"
echo "   # Press Arm button in GUI"
echo "   # Move joystick forward/left/right/backward"
echo ""

echo "=========================================="
echo "If all pass -> ROV Ready! 🚀"
echo "=========================================="
