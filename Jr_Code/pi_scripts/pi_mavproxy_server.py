#!/usr/bin/env python3
"""
MAVLink TCP Relay Server for Raspberry Pi
Bidirectionally relays MAVLink messages between Pixhawk and Ground Station.
This is a native MAVLink relay (not text-based MAVProxy commands).

Connection Types Supported:
  - GPIO UART (/dev/ttyAMA0): Pixhawk connected via RX/TX/GND pins
  - USB Serial (/dev/ttyUSB0): Pixhawk connected via USB
  - USB CDC (/dev/ttyACM0): Pixhawk USB connection alternative

Default Configuration:
  Serial Port: /dev/ttyAMA0 (Raspberry Pi GPIO UART pins)
  Baud Rate: 57600 (standard for Pixhawk on GPIO UART)
  TCP Port: 7000 (for Ground Station connections)
"""

import socket
import threading
import time
import sys
import os
from pathlib import Path
from pymavlink import mavutil


class MAVLinkTCPRelay:
    """Relay MAVLink messages between serial Pixhawk and TCP clients."""

    def __init__(
        self, serial_port="/dev/ttyAMA0", baud=57600, tcp_host="0.0.0.0", tcp_port=7000
    ):
        """
        Initialize MAVLink TCP relay server.

        Args:
            serial_port: Path to Pixhawk serial port
                - "/dev/ttyAMA0": Raspberry Pi GPIO UART (RX/TX/GND pins)
                - "/dev/serial0": Raspberry Pi primary serial alias
                - "/dev/ttyUSB0": USB serial adapter
                - "/dev/ttyACM0": USB CDC device
            baud: Serial baud rate (57600 recommended for GPIO UART)
            tcp_host: TCP server bind address (0.0.0.0 = all interfaces)
            tcp_port: TCP server port (default 7000)
        """
        self.serial_port = serial_port
        self.baud = baud
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port

        self.pixhawk = None
        self.server_socket = None
        self.clients = []
        self.clients_lock = threading.Lock()
        self.running = True

    def connect_pixhawk(self):
        """
        Connect to Pixhawk via serial port.

        For GPIO UART connections on Raspberry Pi:
          - Use /dev/ttyAMA0 (RX on GPIO 15, TX on GPIO 14)
          - Use baud rate 57600 (or 115200 if configured in ArduSub)
          - Ensure GPIO pins are not in use by other services (disable serial console)

        Returns:
            True if connection successful, False otherwise
        """
        print(f"\n[PIXHAWK] Connecting to {self.serial_port} @ {self.baud} baud...")
        try:
            self.pixhawk = mavutil.mavlink_connection(
                self.serial_port,
                baud=self.baud,
                autoreconnect=True,
            )
            print(f"[✅] Pixhawk connected on {self.serial_port}!")
            return True
        except Exception as e:
            print(f"[❌] Failed to connect to Pixhawk: {e}")
            return False

    def start_tcp_server(self):
        """Start TCP server for Ground Station connections."""
        print(f"\n[SERVER] Starting TCP server on {self.tcp_host}:{self.tcp_port}...")
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.tcp_host, self.tcp_port))
            self.server_socket.listen(5)
            print(f"[✅] TCP server listening on {self.tcp_host}:{self.tcp_port}")

            # Start accepting connections in a thread
            threading.Thread(target=self._accept_connections, daemon=True).start()

        except Exception as e:
            print(f"[❌] Failed to start TCP server: {e}")
            return False

        return True

    def _accept_connections(self):
        """Accept incoming TCP connections."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"[CLIENT] ✅ Connected from {addr}")

                with self.clients_lock:
                    self.clients.append(conn)

                # Handle client in a separate thread
                threading.Thread(
                    target=self._handle_client_messages, args=(conn, addr), daemon=True
                ).start()

            except Exception as e:
                if self.running:
                    print(f"[SERVER] ⚠️ Accept error: {e}")
                break

    def _handle_client_messages(self, conn, addr):
        """Handle incoming MAVLink messages from a client."""
        try:
            conn.settimeout(30)  # 30 second timeout

            while self.running:
                try:
                    # Receive MAVLink message from client
                    data = conn.recv(1024)

                    if not data:
                        print(f"[CLIENT] Connection closed by {addr}")
                        break

                    # Forward to Pixhawk
                    if self.pixhawk:
                        try:
                            self.pixhawk.write(data)
                        except Exception as e:
                            print(f"[FORWARD] ⚠️ Error forwarding to Pixhawk: {e}")

                except socket.timeout:
                    # Timeout is OK, just continue
                    pass
                except Exception as e:
                    print(f"[CLIENT] ⚠️ Error handling client: {e}")
                    break

        finally:
            with self.clients_lock:
                if conn in self.clients:
                    self.clients.remove(conn)
            conn.close()
            print(f"[CLIENT] Disconnected: {addr}")

    def relay_pixhawk_to_clients(self):
        """Continuously read from Pixhawk and relay to all clients."""
        print("\n[RELAY] Starting bidirectional relay...")

        while self.running:
            try:
                if not self.pixhawk:
                    time.sleep(0.1)
                    continue

                # Read MAVLink message from Pixhawk (non-blocking)
                msg = self.pixhawk.recv_match(blocking=False, timeout=0)

                if msg:
                    # Get the raw message buffer - pymavlink stores it in the message object
                    try:
                        # The raw buffer is available directly from read_dict or msg_buf
                        # We'll re-encode the message properly
                        if hasattr(msg, "get_msgbuf"):
                            msg_bytes = msg.get_msgbuf()
                        elif hasattr(self.pixhawk, "msg_buf"):
                            msg_bytes = self.pixhawk.msg_buf
                        else:
                            # Fallback: re-pack the message
                            msg_bytes = self.pixhawk.mav.encode(msg)

                        if not msg_bytes:
                            msg_bytes = None

                        # Send to all connected clients
                        with self.clients_lock:
                            dead_clients = []
                            for client in self.clients:
                                try:
                                    if msg_bytes:
                                        client.sendall(msg_bytes)
                                except Exception as e:
                                    print(f"[RELAY] ⚠️ Error sending to client: {e}")
                                    dead_clients.append(client)

                            # Remove dead clients
                            for client in dead_clients:
                                self.clients.remove(client)
                                try:
                                    client.close()
                                except:
                                    pass

                        # Log heartbeats periodically
                        if msg.get_type() == "HEARTBEAT":
                            if not hasattr(self, "_last_hb_log"):
                                self._last_hb_log = 0
                            if time.time() - self._last_hb_log > 5:
                                print(
                                    f"[RELAY] ❤️ Heartbeat from Pixhawk → {len(self.clients)} clients"
                                )
                                self._last_hb_log = time.time()

                    except Exception as e:
                        print(f"[RELAY] ⚠️ Error encoding message: {e}")
                else:
                    time.sleep(0.01)  # Small delay to prevent CPU spinning

            except Exception as e:
                print(f"[RELAY] ⚠️ Relay error: {e}")
                time.sleep(0.1)

    def run(self):
        """Main server loop."""
        print("=" * 60)
        print("MAVLink TCP RELAY SERVER - UIU MARINER")
        print("=" * 60)
        print(f"Serial: {self.serial_port} @ {self.baud} baud")
        print(f"TCP: {self.tcp_host}:{self.tcp_port}")
        print("=" * 60)

        try:
            # Connect to Pixhawk
            if not self.connect_pixhawk():
                print("[❌] Failed to connect to Pixhawk")
                return False

            # Start TCP server
            if not self.start_tcp_server():
                print("[❌] Failed to start TCP server")
                return False

            # Start relay loop (blocks)
            self.relay_pixhawk_to_clients()

        except KeyboardInterrupt:
            print("\n\n[SERVER] Shutting down...")
        except Exception as e:
            print(f"\n[❌] Fatal error: {e}")
            return False
        finally:
            self.shutdown()

        return True

    def shutdown(self):
        """Clean shutdown."""
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        with self.clients_lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()

        if self.pixhawk:
            try:
                self.pixhawk.close()
            except:
                pass

        print("[SERVER] Shutdown complete")


def check_prerequisites(serial_port):
    """Run pre-flight checks before starting."""
    print("\n" + "=" * 60)
    print("PRE-RUN CHECKS")
    print("=" * 60)

    # Check 1: Serial device exists
    print(f"\n[CHECK] Serial device: {serial_port}")
    if Path(serial_port).exists():
        print(f"[✅] Device {serial_port} found")
    else:
        print(f"[⚠️] Warning: Device {serial_port} not detected")
        print("     (May appear when Pixhawk boots up)")

    # Check 2: Port availability
    print("\n[CHECK] Port availability...")
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        test_socket.bind(("0.0.0.0", 7000))
        print("[✅] Port 7000 is available")
        test_socket.close()
    except OSError as e:
        print(f"[❌] Port 7000 already in use: {e}")
        test_socket.close()
        return False

    # Check 3: Network connectivity
    print("\n[CHECK] Network interface...")
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"[✅] Hostname: {hostname}")
        print(f"[✅] Local IP: {local_ip}")
    except Exception as e:
        print(f"[⚠️] Could not resolve network: {e}")

    print("\n" + "=" * 60)
    print("PRE-RUN CHECKS COMPLETE")
    print("=" * 60 + "\n")

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MAVLink TCP Relay Server for ROV")
    parser.add_argument(
        "--master",
        type=str,
        default="/dev/ttyAMA0",
        help="Serial device for Pixhawk (default: /dev/ttyAMA0)",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=57600,
        help="Serial baud rate (default: 57600)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="TCP server bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port", type=int, default=7000, help="TCP server port (default: 7000)"
    )

    args = parser.parse_args()

    try:
        # Run pre-flight checks
        if not check_prerequisites(args.master):
            print("\n[⚠️] Some checks failed. Continuing anyway...")

        # Start relay server
        relay = MAVLinkTCPRelay(
            serial_port=args.master,
            baud=args.baudrate,
            tcp_host=args.host,
            tcp_port=args.port,
        )

        success = relay.run()
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
