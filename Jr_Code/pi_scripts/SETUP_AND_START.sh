#!/bin/bash

# ========================================
# SETUP AND START ROV SERVICES
# Run this ONCE on Raspberry Pi
# ========================================

echo "=========================================="
echo "🤖 UIU MARINER - Pi Setup"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Make all scripts executable
echo "1️⃣  Making scripts executable..."
chmod +x *.sh *.py
echo "   ✅ Done"
echo ""

# Get Ground Station IP
echo "2️⃣  Network Configuration"
echo ""
read -p "Enter your Windows PC IP address (e.g., 192.168.0.104): " GROUND_STATION_IP

if [ -z "$GROUND_STATION_IP" ]; then
    echo "❌ IP address is required!"
    exit 1
fi

echo ""
echo "   Ground Station IP: $GROUND_STATION_IP"
echo ""

# Check Pixhawk connection
echo "3️⃣  Checking Pixhawk connection..."
echo "   Expected: /dev/ttyAMA0 at 57600 baud"
echo ""

if [ -e "/dev/ttyAMA0" ]; then
    echo "   ✅ Pixhawk found at /dev/ttyAMA0"
else
    echo "   ⚠️  /dev/ttyAMA0 not found"
    echo "   💡 Run: python3 detect_pixhawk.py to find it"
fi
echo ""

# Check for cameras
echo "4️⃣  Checking cameras..."
if command -v libcamera-hello &> /dev/null; then
    echo "   💡 Run: ./detect_cameras.sh to find cameras"
else
    echo "   ⚠️  libcamera tools not found"
fi
echo ""

# Ask user preference
echo "5️⃣  Service Startup Options:"
echo ""
echo "   A) Auto-start on boot (Recommended)"
echo "      - Services start automatically when Pi boots"
echo "      - No manual commands needed"
echo "      - Uses systemd services"
echo ""
echo "   B) Manual start (screen sessions)"
echo "      - Start services manually when needed"
echo "      - Easy to view logs"
echo "      - Stop/restart anytime"
echo ""
read -p "Choose option (A/B): " OPTION

case "$OPTION" in
    [Aa])
        echo ""
        echo "🔧 Installing auto-start services..."
        sudo bash -c "cat > /tmp/install_rov.sh << 'EOFINSTALL'
#!/bin/bash
SCRIPT_DIR=\"$SCRIPT_DIR\"
GROUND_STATION_IP=\"$GROUND_STATION_IP\"
ACTUAL_USER=\"\${SUDO_USER:-\$USER}\"

# Create sensor service
cat > /etc/systemd/system/rov-sensors.service << EOF
[Unit]
Description=ROV Sensor Server (BMP388)
After=network.target
Wants=network.target

[Service]
Type=simple
User=\$ACTUAL_USER
WorkingDirectory=\$SCRIPT_DIR
ExecStart=/usr/bin/python3 \$SCRIPT_DIR/pi_sensor_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create MAVProxy service
cat > /etc/systemd/system/rov-mavproxy.service << EOF
[Unit]
Description=ROV MAVProxy Server (Pixhawk)
After=network.target
Wants=network.target

[Service]
Type=simple
User=\$ACTUAL_USER
WorkingDirectory=\$SCRIPT_DIR
ExecStart=/usr/bin/python3 \$SCRIPT_DIR/pi_mavproxy_server.py --master /dev/ttyAMA0 --baudrate 57600 --port 7000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create camera 0 service
cat > /etc/systemd/system/rov-camera0.service << EOF
[Unit]
Description=ROV Camera 0 Stream
After=network.target
Wants=network.target

[Service]
Type=simple
User=\$ACTUAL_USER
WorkingDirectory=\$SCRIPT_DIR
ExecStart=/bin/bash \$SCRIPT_DIR/cam0.sh \$GROUND_STATION_IP
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create camera 1 service
cat > /etc/systemd/system/rov-camera1.service << EOF
[Unit]
Description=ROV Camera 1 Stream
After=network.target
Wants=network.target

[Service]
Type=simple
User=\$ACTUAL_USER
WorkingDirectory=\$SCRIPT_DIR
ExecStart=/bin/bash \$SCRIPT_DIR/cam1.sh \$GROUND_STATION_IP
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable
systemctl daemon-reload
systemctl enable rov-sensors rov-mavproxy rov-camera0 rov-camera1
systemctl start rov-sensors rov-mavproxy rov-camera0 rov-camera1

echo \"\"
echo \"✅ Auto-start services installed!\"
echo \"\"
EOFINSTALL
"
        sudo bash /tmp/install_rov.sh
        sudo rm /tmp/install_rov.sh
        
        echo ""
        echo "✅ Services installed and started!"
        echo ""
        echo "📊 Check status:"
        echo "   sudo systemctl status rov-sensors"
        echo "   sudo systemctl status rov-mavproxy"
        echo "   sudo systemctl status rov-camera0"
        echo "   sudo systemctl status rov-camera1"
        echo ""
        echo "📋 View logs:"
        echo "   sudo journalctl -u rov-sensors -f"
        echo "   sudo journalctl -u rov-mavproxy -f"
        echo ""
        echo "🎉 Services will start automatically on boot!"
        ;;
        
    [Bb])
        echo ""
        echo "🚀 Starting services manually..."
        ./start_all_services.sh "$GROUND_STATION_IP"
        echo ""
        echo "✅ Services started in screen sessions!"
        echo ""
        echo "📊 View sessions:"
        echo "   screen -ls"
        echo ""
        echo "📋 Attach to logs:"
        echo "   screen -r sensors"
        echo "   screen -r mavproxy"
        echo "   screen -r cam0"
        echo "   screen -r cam1"
        echo ""
        echo "💡 Detach: Press Ctrl+A then D"
        echo "🛑 Stop all: ./stop_all_services.sh"
        ;;
        
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "🖥️  Now on your Windows PC:"
echo "   cd \"E:\UIU MARINER\mariner-software-1.0\""
echo "   python launch_mariner.py"
echo ""
echo "🎮 Everything should connect automatically!"
echo ""
