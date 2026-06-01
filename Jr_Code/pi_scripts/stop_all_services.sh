#!/bin/bash

# ========================================
# Stop All ROV Services on Raspberry Pi
# ========================================

echo "🛑 Stopping UIU MARINER ROV Services..."
echo "========================================"

# Stop Camera 1
if screen -list | grep -q "cam1"; then
    echo "1️⃣  Stopping Camera 1..."
    screen -X -S cam1 quit
    echo "   ✅ Camera 1 stopped"
else
    echo "1️⃣  Camera 1 not running"
fi

# Stop Camera 0
if screen -list | grep -q "cam0"; then
    echo "2️⃣  Stopping Camera 0..."
    screen -X -S cam0 quit
    echo "   ✅ Camera 0 stopped"
else
    echo "2️⃣  Camera 0 not running"
fi

# Stop MAVProxy
if screen -list | grep -q "mavproxy"; then
    echo "3️⃣  Stopping MAVProxy..."
    screen -X -S mavproxy quit
    echo "   ✅ MAVProxy stopped"
else
    echo "3️⃣  MAVProxy not running"
fi

# Stop Sensor Server
if screen -list | grep -q "sensors"; then
    echo "4️⃣  Stopping Sensor Server..."
    screen -X -S sensors quit
    echo "   ✅ Sensor Server stopped"
else
    echo "4️⃣  Sensor Server not running"
fi

# Wait a moment for processes to clean up
sleep 1

# Show final status
echo ""
echo "========================================"
echo "✅ All Services Stopped"
echo "========================================"
echo ""
echo "📊 Remaining Screen Sessions:"
screen -ls || echo "   No screen sessions running"

echo ""
echo "💡 To restart services:"
echo "   ./start_all_services.sh YOUR_GROUND_STATION_IP"
echo ""
