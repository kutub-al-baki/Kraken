"""
UIU MARINER - Serial Port Scanner
Auto-detect Pixhawk connection on various serial ports and baud rates
Useful for Raspberry Pi to Pixhawk connections
"""

from pymavlink import mavutil
import time
from typing import Optional, Tuple, List


class PixhawkPortScanner:
    """
    Scans multiple serial ports and baud rates to find Pixhawk connection.
    Useful when the exact port or baud rate is unknown.
    """

    # Common serial port names (prioritized order - most common first)
    # NOTE: For Raspberry Pi with GPIO UART connections, /dev/ttyAMA0 and /dev/serial0
    # are the primary GPIO UART ports. These are used when Pixhawk is connected via
    # RX/TX/GND pins (not USB).
    DEFAULT_SERIAL_PORTS = [
        "/dev/ttyAMA0",  # Raspberry Pi GPIO UART (primary) - RX/TX/GND pins
        "/dev/serial0",  # Raspberry Pi primary serial (alias for ttyAMA0)
        "/dev/ttyUSB0",  # USB serial adapter 0
        "/dev/ttyUSB1",  # USB serial adapter 1
        "/dev/ttyACM0",  # USB CDC devices (Pixhawk alternative)
        "/dev/ttyACM1",  # USB CDC devices alternate
        "COM3",  # Windows COM port
        "COM4",  # Windows COM port
        "COM5",  # Windows COM port
    ]

    # Common baud rates for Pixhawk/ArduSub (prioritized order)
    # NOTE: Pixhawk defaults to 57600 when connected via GPIO UART
    # 115200 is also common but 57600 is more stable on long tethers
    DEFAULT_BAUD_RATES = [
        57600,  # Standard for Pixhawk on GPIO UART connections
        115200,  # Alternative common rate for Pixhawk
        921600,  # High-speed
        38400,  # Lower speed option
    ]

    def __init__(
        self,
        ports: Optional[List[str]] = None,
        baud_rates: Optional[List[int]] = None,
        timeout: int = 5,
        heartbeat_timeout: int = 10,
    ):
        """
        Initialize port scanner.

        Args:
            ports: List of serial ports to scan (defaults to common ports)
            baud_rates: List of baud rates to try (defaults to common rates)
            timeout: Connection timeout in seconds
            heartbeat_timeout: Time to wait for heartbeat in seconds
        """
        self.ports = ports if ports else self.DEFAULT_SERIAL_PORTS
        self.baud_rates = baud_rates if baud_rates else self.DEFAULT_BAUD_RATES
        self.timeout = timeout
        self.heartbeat_timeout = heartbeat_timeout

    def check_heartbeat(self, port: str, baud: int) -> bool:
        """
        Check if a Pixhawk heartbeat is received on given port/baud.

        Args:
            port: Serial port path
            baud: Baud rate to test

        Returns:
            True if heartbeat received, False otherwise
        """
        try:
            print(f"[SCANNER] Checking {port} @ {baud} baud...")

            # Try to connect
            master = mavutil.mavlink_connection(port, baud=baud, timeout=self.timeout)

            # Wait for heartbeat
            msg = master.recv_match(
                type="HEARTBEAT", blocking=True, timeout=self.heartbeat_timeout
            )

            if msg:
                print(f"[SCANNER] ✅ Heartbeat received on {port} @ {baud} baud")
                print(f"[SCANNER]    Type: {msg.type}, Autopilot: {msg.autopilot}")
                master.close()
                return True
            else:
                print(f"[SCANNER] ⏱️ No heartbeat on {port} @ {baud} baud (timeout)")
                master.close()
                return False

        except Exception as e:
            print(f"[SCANNER] ❌ Failed to open {port} @ {baud} baud: {e}")
            return False

    def scan(self) -> Optional[Tuple[str, int]]:
        """
        Scan all configured ports and baud rates to find Pixhawk.

        Returns:
            Tuple of (port, baud_rate) if found, None otherwise
        """
        print("[SCANNER] Starting Pixhawk auto-detection...")
        print(f"[SCANNER] Ports to scan: {len(self.ports)}")
        print(f"[SCANNER] Baud rates to try: {self.baud_rates}")
        print()

        for port in self.ports:
            for baud in self.baud_rates:
                if self.check_heartbeat(port, baud):
                    print()
                    print(f"[SCANNER] 🎯 Device found: {port} @ {baud} baud")
                    return (port, baud)

        print()
        print("[SCANNER] ❌ No Pixhawk found on any port/baud combination")
        return None

    def scan_with_retry(
        self, max_attempts: int = 3, delay: int = 2
    ) -> Optional[Tuple[str, int]]:
        """
        Scan with multiple retry attempts.

        Args:
            max_attempts: Maximum number of scan attempts
            delay: Delay between attempts in seconds

        Returns:
            Tuple of (port, baud_rate) if found, None otherwise
        """
        for attempt in range(1, max_attempts + 1):
            print(f"[SCANNER] Attempt {attempt}/{max_attempts}")
            result = self.scan()

            if result:
                return result

            if attempt < max_attempts:
                print(f"[SCANNER] Retrying in {delay} seconds...")
                time.sleep(delay)

        return None

    def get_connection_string(self, port: str, baud: int) -> str:
        """
        Convert port and baud to MAVLink connection string.

        Args:
            port: Serial port path
            baud: Baud rate

        Returns:
            Connection string in format "port:baud"
        """
        return f"{port}:{baud}"


def quick_scan(verbose: bool = True) -> Optional[str]:
    """
    Quick convenience function to scan for Pixhawk and return connection string.

    Args:
        verbose: Whether to print scan progress

    Returns:
        Connection string if found, None otherwise

    Example:
        >>> connection_string = quick_scan()
        >>> if connection_string:
        >>>     master = mavutil.mavlink_connection(connection_string)
    """
    scanner = PixhawkPortScanner()
    result = scanner.scan()

    if result:
        port, baud = result
        connection_string = scanner.get_connection_string(port, baud)
        if verbose:
            print(f"[SCANNER] Connection string: {connection_string}")
        return connection_string

    return None


def main():
    """
    Run standalone port scanner.
    """
    print("=" * 60)
    print("UIU MARINER - Pixhawk Port Scanner")
    print("=" * 60)
    print()

    # Create scanner with default settings
    scanner = PixhawkPortScanner()

    # Scan for device
    result = scanner.scan_with_retry(max_attempts=2, delay=3)

    if result:
        port, baud = result
        connection_string = scanner.get_connection_string(port, baud)

        print()
        print("=" * 60)
        print("✅ SUCCESS!")
        print(f"   Port: {port}")
        print(f"   Baud Rate: {baud}")
        print(f"   Connection String: {connection_string}")
        print()
        print("Add this to your config.json:")
        print(f'   "mavlink_connection": "{connection_string}"')
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ FAILED - No Pixhawk detected")
        print()
        print("Troubleshooting:")
        print("  1. Check physical connections")
        print("  2. Verify Pixhawk is powered on")
        print("  3. Check if ArduSub firmware is loaded")
        print("  4. Try manually with: screen /dev/ttyUSB0 115200")
        print("=" * 60)


if __name__ == "__main__":
    main()
