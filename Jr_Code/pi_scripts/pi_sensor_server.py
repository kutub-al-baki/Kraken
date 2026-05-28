#!/usr/bin/env python3
"""
Sensor Server for Raspberry Pi
Reads BMP388 sensor data and sends to Ground Station via TCP socket
Based on tested code from sensorServer.py
"""

import smbus
import time
import socket
import sys


# I2C Configuration
I2C_BUS = 1  # I2C bus number (1 is standard on Raspberry Pi)
BMP388_ADDR = 0x77  # BMP388 I2C address

# BMP388 Registers
BMP388_TEMP_REG = 0x04
BMP388_PRESS_REG = 0x07
BMP388_ALT_REG = 0x08


def initialize_sensor(bus):
    """Initialize BMP388 sensor."""
    print("[SENSOR] Initializing BMP388...")
    bus.write_byte_data(BMP388_ADDR, 0x1B, 0xB6)  # Soft reset
    time.sleep(0.5)
    bus.write_byte_data(BMP388_ADDR, 0x1B, 0x33)  # Normal mode
    time.sleep(0.5)
    print("[SENSOR] ✅ BMP388 initialized")


def read_temperature(bus):
    """Read temperature from BMP388."""
    try:
        temp_data = bus.read_i2c_block_data(BMP388_ADDR, BMP388_TEMP_REG, 2)
        raw_temp = (temp_data[1] << 8) | temp_data[0]
        return raw_temp / 256.0  # Convert to Celsius
    except Exception as e:
        print(f"[SENSOR] ❌ Temperature read error: {e}")
        return 0.0


def read_pressure(bus):
    """Read pressure from BMP388."""
    try:
        data = bus.read_i2c_block_data(BMP388_ADDR, BMP388_PRESS_REG, 3)
        pressure_raw = data[0] | (data[1] << 8) | (data[2] << 16)
        return pressure_raw / 256.0  # Pressure in Pa
    except Exception as e:
        print(f"[SENSOR] ❌ Pressure read error: {e}")
        return 0.0


def read_altitude(bus):
    """Read altitude/depth from BMP388."""
    try:
        data = bus.read_i2c_block_data(BMP388_ADDR, BMP388_ALT_REG, 3)
        altitude_raw = data[0] | (data[1] << 8) | (data[2] << 16)
        return altitude_raw / 100.0  # Altitude in meters
    except Exception as e:
        print(f"[SENSOR] ❌ Altitude read error: {e}")
        return 0.0


def start_sensor_server(host="0.0.0.0", port=5002):
    """
    Start TCP server to send sensor data to Ground Station.

    Args:
        host: Server bind address (0.0.0.0 = all interfaces)
        port: TCP port number (default: 5002 to avoid conflict with camera on 5000/5001)
    """
    bus = smbus.SMBus(I2C_BUS)

    # Create TCP server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)

    print(f"[SENSOR] 🚀 Server listening on {host}:{port}")
    print("[SENSOR] Waiting for Ground Station connection...")

    while True:
        try:
            conn, addr = server.accept()
            print(f"[SENSOR] ✅ Connected to {addr}")

            # Initialize sensor
            initialize_sensor(bus)

            # Send data loop
            while True:
                try:
                    temperature = read_temperature(bus)
                    pressure = read_pressure(bus)
                    depth = read_altitude(bus)

                    # Format: "temperature,pressure,depth\n"
                    data_string = f"{temperature},{pressure},{depth}\n"
                    conn.sendall(data_string.encode())

                    print(
                        f"[SENSOR] Sent: T={temperature:.2f}°C P={pressure:.2f}Pa D={depth:.2f}m"
                    )

                    time.sleep(1)  # Send every second

                except BrokenPipeError:
                    print("[SENSOR] ⚠️ Connection closed by client")
                    break
                except Exception as e:
                    print(f"[SENSOR] ❌ Error sending data: {e}")
                    break

            conn.close()
            print("[SENSOR] Connection closed, waiting for new connection...")

        except KeyboardInterrupt:
            print("\n[SENSOR] Shutting down...")
            break
        except Exception as e:
            print(f"[SENSOR] ❌ Server error: {e}")
            time.sleep(5)

    server.close()
    print("[SENSOR] Server stopped")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BMP388 Sensor Server for ROV")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Bind address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=5002, help="TCP port (default: 5002)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("BMP388 SENSOR SERVER - UIU MARINER")
    print("=" * 60)

    try:
        start_sensor_server(host=args.host, port=args.port)
    except PermissionError:
        print("\n❌ Permission denied! Run with sudo:")
        print(f"  sudo python3 {sys.argv[0]} --host {args.host} --port {args.port}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
