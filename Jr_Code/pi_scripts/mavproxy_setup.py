#!/usr/bin/env python3
# ============================================================================
# UIU MARINER - Pi MAVProxy Setup & Connection Tester
# ============================================================================
# This script helps set up and test the MAVProxy TCP relay server on Pi
# MAVProxy acts as a bridge between:
#   - Pixhawk (connected via serial /dev/ttyAMA0)
#   - Ground Station (connected via TCP port 7000)
#
# Usage:
#   python3 mavproxy_setup.py          # Interactive setup
#   python3 mavproxy_setup.py test     # Test connection
#   python3 mavproxy_setup.py install  # Install MAVProxy
#
# ============================================================================

import sys
import subprocess
import time
import os
from pathlib import Path


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_success(msg):
    print(f"{Colors.GREEN}[✓] {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}[✗] {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[!] {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}[*] {msg}{Colors.END}")


def print_header(msg):
    print(f"\n{Colors.BLUE}{'='*50}{Colors.END}")
    print(f"{Colors.BLUE}{msg}{Colors.END}")
    print(f"{Colors.BLUE}{'='*50}{Colors.END}\n")


def check_mavproxy_installed():
    """Check if MAVProxy is installed"""
    try:
        result = subprocess.run(
            ["mavproxy.py", "--version"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except:
        return False


def install_mavproxy():
    """Install MAVProxy"""
    print_header("Installing MAVProxy")

    try:
        print_info("Installing MAVProxy via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "MAVProxy"], check=True)

        if check_mavproxy_installed():
            print_success("MAVProxy installed successfully")
            return True
        else:
            print_error("MAVProxy installation verification failed")
            return False

    except Exception as e:
        print_error(f"Failed to install MAVProxy: {e}")
        return False


def test_pixhawk_connection():
    """Test connection to Pixhawk"""
    print_header("Testing Pixhawk Connection")

    sys.path.insert(0, "/opt/mariner")

    try:
        from src.services.mavlinkConnection import PixhawkConnection

        print_info("Attempting connection to Pixhawk via /dev/ttyAMA0:57600...")

        pixhawk = PixhawkConnection(link="/dev/ttyAMA0:57600", auto_detect=True)

        if pixhawk.connect():
            print_success("Connected to Pixhawk!")
            print_info(f"Connection: {pixhawk.link}")

            if pixhawk.vehicle:
                print_info(f"Flight mode: {pixhawk.vehicle.flightmode}")
                print_info(f"Armed status: {pixhawk.vehicle.armed}")
                print_info(f"System status: {pixhawk.vehicle.system_status.state}")

            return True
        else:
            print_error("Failed to connect to Pixhawk")
            return False

    except Exception as e:
        print_error(f"Connection error: {e}")
        return False


def test_mavproxy_relay():
    """Test MAVProxy relay server"""
    print_header("Testing MAVProxy Relay Server")

    if not check_mavproxy_installed():
        print_warning("MAVProxy not installed")
        return False

    try:
        print_info("Starting MAVProxy relay (press Ctrl+C to stop)...")
        print_info(
            "Command: mavproxy.py --master=/dev/ttyAMA0:57600 --out=tcpin:0.0.0.0:7000"
        )

        subprocess.run(
            ["mavproxy.py", "--master=/dev/ttyAMA0:57600", "--out=tcpin:0.0.0.0:7000"],
            timeout=10,
        )

        return True

    except KeyboardInterrupt:
        print_info("\nRelay stopped by user")
        return True
    except subprocess.TimeoutExpired:
        print_warning("Relay test timeout (this is normal)")
        return True
    except Exception as e:
        print_error(f"Relay error: {e}")
        return False


def setup_autostart():
    """Set up autostart on boot"""
    print_header("Setting Up Autostart")

    service_file = "/etc/systemd/system/mariner_autostart.service"
    script_file = "/opt/mariner/pi_autostart_all.sh"

    print_info("Setting up systemd service for automatic startup...")

    # Check if script exists
    if not os.path.exists(script_file):
        print_error(f"Script not found: {script_file}")
        return False

    print_info(f"Using service file: {service_file}")
    print_info(f"Using startup script: {script_file}")

    try:
        print_info("Enabling service (requires sudo)...")
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(
            ["sudo", "systemctl", "enable", "mariner_autostart.service"], check=True
        )
        subprocess.run(
            ["sudo", "systemctl", "start", "mariner_autostart.service"], check=True
        )

        print_success("Autostart enabled!")
        print_info("The system will now automatically start all services on boot")

        return True

    except Exception as e:
        print_error(f"Failed to set up autostart: {e}")
        print_warning("You may need to run with sudo, or set up manually")
        return False


def show_manual_startup():
    """Show manual startup commands"""
    print_header("Manual Startup Commands")

    print_info("To start services manually, use these commands:\n")

    print(f"{Colors.YELLOW}1. Start MAVProxy Relay:{Colors.END}")
    print("   mavproxy.py --master=/dev/ttyAMA0:57600 --out=tcpin:0.0.0.0:7000\n")

    print(f"{Colors.YELLOW}2. In another terminal, start Sensor Server:{Colors.END}")
    print("   cd /opt/mariner")
    print("   python3 pi_scripts/pi_sensor_server.py\n")

    print(f"{Colors.YELLOW}3. In another terminal, start Camera Servers:{Colors.END}")
    print("   cd /opt/mariner")
    print("   python3 pi_scripts/pi_camera_server.py camera_0 &")
    print("   python3 pi_scripts/pi_camera_server.py camera_1 &\n")

    print(f"{Colors.YELLOW}4. Or use the autostart script:{Colors.END}")
    print("   bash /opt/mariner/pi_autostart_all.sh start")
    print("   bash /opt/mariner/pi_autostart_all.sh status")
    print("   bash /opt/mariner/pi_autostart_all.sh stop\n")


def interactive_menu():
    """Interactive menu"""
    print_header("UIU MARINER - Pi Setup Wizard")

    while True:
        print(f"\n{Colors.BLUE}What would you like to do?{Colors.END}")
        print("  1. Check if MAVProxy is installed")
        print("  2. Install MAVProxy")
        print("  3. Test Pixhawk connection")
        print("  4. Test MAVProxy relay server")
        print("  5. Set up autostart on boot")
        print("  6. Show manual startup commands")
        print("  7. Exit")

        choice = input("\nEnter choice (1-7): ").strip()

        if choice == "1":
            if check_mavproxy_installed():
                print_success("MAVProxy is installed")
            else:
                print_error("MAVProxy is not installed")

        elif choice == "2":
            install_mavproxy()

        elif choice == "3":
            test_pixhawk_connection()

        elif choice == "4":
            test_mavproxy_relay()

        elif choice == "5":
            setup_autostart()

        elif choice == "6":
            show_manual_startup()

        elif choice == "7":
            print_success("Exiting")
            break

        input("\nPress Enter to continue...")


def main():
    """Main entry point"""

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "test":
            test_pixhawk_connection()
            test_mavproxy_relay()

        elif command == "install":
            install_mavproxy()

        elif command == "setup":
            setup_autostart()

        elif command == "help":
            print_header("UIU MARINER - MAVProxy Setup")
            print("Usage: python3 mavproxy_setup.py [command]\n")
            print("Commands:")
            print("  test     - Test Pixhawk and MAVProxy connections")
            print("  install  - Install MAVProxy")
            print("  setup    - Set up autostart")
            print("  help     - Show this help")
            print("  (none)   - Interactive menu")

        else:
            print_error(f"Unknown command: {command}")

    else:
        interactive_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
