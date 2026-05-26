#!/usr/bin/env python3
"""
Pixhawk Detection Script for Raspberry Pi
Scans serial ports and baud rates to find Pixhawk connection.

Supports both GPIO UART and USB connections:
  - GPIO UART (/dev/ttyAMA0): Pixhawk connected to RX/TX/GND pins
  - USB Serial (/dev/ttyUSB0): Pixhawk connected via USB adapter
  - USB CDC (/dev/ttyACM0): Pixhawk USB connection alternative

Priority Order:
  1. GPIO UART (/dev/ttyAMA0, /dev/serial0) at 57600 baud
  2. USB Serial (/dev/ttyUSB*, /dev/ttyACM*) at 115200 baud
  3. Fallback to other baud rates
"""

from pymavlink import mavutil
import time
import sys

# Serial ports in priority order (GPIO UART first)
serial_ports = [
    "/dev/ttyAMA0",  # Raspberry Pi GPIO UART (primary) - RX/TX/GND pins
    "/dev/serial0",  # Alias to primary UART
    "/dev/ttyUSB0",  # USB serial adapter
    "/dev/ttyUSB1",  # Additional USB
    "/dev/ttyACM0",  # USB CDC (Arduino/Pixhawk)
    "/dev/ttyACM1",  # Additional USB CDC
    "/dev/ttyS0",  # Another serial port option
]

# Baud rates in priority order (GPIO UART standard first)
baud_rates = [57600, 115200, 38400, 19200, 9600]

print("=" * 60)
print("🔍 PIXHAWK DETECTION SCRIPT")
print("=" * 60)
print()
print("Scanning serial ports for Pixhawk/MAVLink device...")
print("Checking GPIO UART first, then USB connections...")
print()


def check_heartbeat(port, baud):
    """
    Try to connect to a port and wait for HEARTBEAT message
    """
    try:
        print(f"⏳ Checking {port} at {baud} baud...", end=" ")
        sys.stdout.flush()

        # Try to open connection
        master = mavutil.mavlink_connection(port, baud=baud, timeout=3)

        # Wait for heartbeat (timeout 5 seconds)
        msg = master.recv_match(type="HEARTBEAT", blocking=True, timeout=5)

        if msg:
            print("✅ HEARTBEAT RECEIVED!")
            print(f"   Device Type: {msg.type}")
            print(f"   Autopilot: {msg.autopilot}")
            print(f"   System ID: {msg.get_srcSystem()}")
            print(f"   Component ID: {msg.get_srcComponent()}")
            return True, master
        else:
            print("❌ No heartbeat")
            return False, None

    except Exception as e:
        print(f"❌ Error: {str(e)[:40]}")
        return False, None


# Scan all ports and baud rates
found = False
connection = None

for port in serial_ports:
    if found:
        break

    for baud in baud_rates:
        success, conn = check_heartbeat(port, baud)

        if success:
            print()
            print("=" * 60)
            print("✅ PIXHAWK FOUND!")
            print("=" * 60)
            print(f"Port: {port}")
            print(f"Baud Rate: {baud}")
            print()
            print("🔧 Use these settings in your configuration:")
            print(f"   MAVLink Master: {port}")
            print(f"   Baud Rate: {baud}")
            print()
            print("📝 Update pi_mavproxy_server.py with:")
            print(f"   --master {port} --baudrate {baud}")
            print()
            found = True
            connection = conn
            break

if not found:
    print()
    print("=" * 60)
    print("❌ NO PIXHAWK FOUND")
    print("=" * 60)
    print()
    print("🔧 Troubleshooting:")
    print()
    print("FOR GPIO UART CONNECTIONS (/dev/ttyAMA0):")
    print("   1. Check physical connection (RX/TX/GND pins)")
    print("   2. Verify UART is enabled in raspi-config:")
    print("      sudo raspi-config → Interface Options → Serial Port")
    print("      - Enable serial port hardware: YES")
    print("      - Disable login shell over serial: YES")
    print("   3. Disable serial console if enabled:")
    print("      sudo systemctl disable serial-getty@ttyAMA0.service")
    print("   4. Verify device permissions:")
    print("      ls -l /dev/ttyAMA0")
    print("      sudo usermod -a -G dialout $USER")
    print()
    print("FOR ALL CONNECTIONS:")
    print("   1. Verify Pixhawk is powered on (LED should blink)")
    print("   2. Check cable is data-capable (not charge-only)")
    print("   3. Try different USB port (if USB connection)")
    print("   4. Check ArduSub firmware is installed on Pixhawk")
    print("   5. Reset Pixhawk (power cycle or press reset button)")
    print()
    print("📋 Available serial devices:")
    import subprocess

    try:
        result = subprocess.run(
            ["ls", "-l", "/dev/tty*"], capture_output=True, text=True
        )
        print(result.stdout)
    except:
        print("   Could not list devices")

    sys.exit(1)

# Test communication
if connection:
    print("=" * 60)
    print("🧪 TESTING COMMUNICATION")
    print("=" * 60)
    print()
    print("Requesting parameter list...")

    try:
        # Request parameters
        connection.mav.param_request_list_send(
            connection.target_system, connection.target_component
        )

        # Wait for first parameter
        msg = connection.recv_match(type="PARAM_VALUE", blocking=True, timeout=5)
        if msg:
            print(f"✅ Parameter received: {msg.param_id} = {msg.param_value}")
            print()
            print("✅ Communication working properly!")
        else:
            print("⚠️  No parameter response (but heartbeat OK)")

    except Exception as e:
        print(f"⚠️  Communication test error: {e}")

    print()
    print("=" * 60)
    print("✅ DETECTION COMPLETE")
    print("=" * 60)

    connection.close()
    sys.exit(0)
