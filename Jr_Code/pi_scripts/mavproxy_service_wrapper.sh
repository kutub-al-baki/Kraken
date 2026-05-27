#!/bin/bash
# MAVProxy Auto-Start Service Script
# Automatically detects Pixhawk on /dev/ttyACM0 or /dev/ttyACM1

MAX_ATTEMPTS=30
ATTEMPTS=0
PIXHAWK_DEV=""
BAUDRATE=57600
TCP_PORT=7000

echo "🚀 MAVProxy Auto-Start Service"
echo "================================"

# Wait for Pixhawk to be detected
echo "1. Waiting for Pixhawk device..."
while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if [ -e /dev/ttyAMA0 ]; then
        PIXHAWK_DEV=/dev/ttyAMA0
        echo "   ✅ Found Pixhawk on /dev/ttyAMA0"
        break
    elif [ -e /dev/ttyACM0 ]; then
        PIXHAWK_DEV=/dev/ttyACM0
        echo "   ✅ Found Pixhawk on /dev/ttyACM0"
        break
    elif [ -e /dev/ttyACM1 ]; then
        PIXHAWK_DEV=/dev/ttyACM1
        echo "   ✅ Found Pixhawk on /dev/ttyACM1"
        break
    fi
    sleep 1
    ATTEMPTS=$((ATTEMPTS+1))
    if [ $((ATTEMPTS % 5)) -eq 0 ]; then
        echo "   ⏳ Still waiting... (${ATTEMPTS}/${MAX_ATTEMPTS})"
    fi
done

if [ -z "$PIXHAWK_DEV" ]; then
    echo "   ❌ Pixhawk not found after ${MAX_ATTEMPTS} seconds"
    exit 1
fi

# Wait for Pixhawk firmware to fully initialize
echo "2. Waiting for Pixhawk firmware initialization..."
sleep 3

# Start MAVProxy
echo "3. Starting MAVProxy..."
echo "   Device: $PIXHAWK_DEV"
echo "   Baudrate: $BAUDRATE"
echo "   TCP Port: $TCP_PORT"

# Run MAVProxy (this will keep running)
exec mavproxy.py \
    --master=$PIXHAWK_DEV \
    --baudrate=$BAUDRATE \
    --out=tcp:0.0.0.0:$TCP_PORT
