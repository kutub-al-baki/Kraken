"""
UIU MARINER - MAVLink Pixhawk Connection Manager
================================================
Handles communication with Pixhawk autopilot via MAVLink protocol.
Supports:
  - Automatic connection detection
  - Vehicle arming/disarming
  - Flight mode changes
  - Direct thruster control via RC_CHANNELS_OVERRIDE
  - Automatic reconnection on connection loss
  - Heartbeat monitoring

Author: UIU MARINER Development Team
"""

from pymavlink import mavutil
import time
import sys
import os
from pathlib import Path

# Constants for connection management
DEFAULT_HEARTBEAT_TIMEOUT = 60.0  # seconds
DEFAULT_RECONNECT_INTERVAL = 10.0  # seconds
RC_OVERRIDE_CHECK_INTERVAL = 0.5  # seconds
RC_OVERRIDE_RATE_LIMIT = 0.05  # 20 Hz max
SUCCESSFUL_SEND_TIMEOUT = 5.0  # seconds


class PixhawkConnection:
    """
    MAVLink connection manager for Pixhawk autopilot running ArduSub firmware.

    This class handles:
    - Connection establishment and auto-detection
    - Heartbeat monitoring for connection health
    - Vehicle control (arm, disarm, mode changes)
    - Thruster control via RC channel override
    - Automatic reconnection on failure

    Example:
        connection = PixhawkConnection("tcp:192.168.0.104:7000")
        if connection.connect():
            connection.arm()
            channels = [1500] * 8
            connection.send_rc_channels_override(channels)
    """

    def __init__(self, link="auto", auto_detect=True):
        """
        Initialize Pixhawk connection with specified parameters.

        Args:
            link (str): MAVLink connection string. Options:
                - "auto": Auto-detect connection (requires simple_auto_connect)
                - "tcp:HOST:PORT": TCP connection (e.g., "tcp:192.168.0.104:7000")
                - "udp:HOST:PORT": UDP connection (e.g., "udp:127.0.0.1:14550")
                - "/dev/ttyAMA0:57600": GPIO UART serial (Raspberry Pi RX/TX/GND pins)
                - "/dev/ttyUSB0:115200": USB serial adapter connection
                - "/dev/ttyACM0:115200": USB CDC device connection

            auto_detect (bool): If True, attempt auto-detection of connection when
                               initial connection fails. Uses portScanner to find
                               GPIO UART and USB connections with appropriate baud rates.

        Note:
            GPIO UART (/dev/ttyAMA0) is the primary connection on Raspberry Pi.
            If connected via GPIO pins (RX/TX/GND), use /dev/ttyAMA0:57600.
            USB connections typically use /dev/ttyUSB0:115200 or /dev/ttyACM0:115200.
        """
        # Connection parameters
        self.link = link
        self.auto_detect = auto_detect
        self.vehicle = None
        self.connected = False

        # Timing parameters for connection monitoring
        self.last_heartbeat_time = time.time()
        self.last_successful_send_time = time.time()
        self.heartbeat_timeout = DEFAULT_HEARTBEAT_TIMEOUT
        self.last_reconnect_attempt = 0
        self.reconnect_interval = DEFAULT_RECONNECT_INTERVAL

        # Rate limiting for RC override messages
        self._last_check_time = 0
        self._last_error_time = 0
        self._last_sent_channels = None
        self._last_send_time = 0.0
        self._last_rc_log_time = 0

    def connect(self):
        """
        Establish MAVLink connection to Pixhawk with automatic fallback strategies.

        Connection attempts:
        1. Try Pi/MAVProxy auto-detection (if link="auto")
        2. Try direct connection to specified link
        3. Fallback to serial port scanning if specified
        4. Retry connection with auto-detected port

        Returns:
            MAVLink vehicle object if successful, None otherwise
        """
        try:
            # Step 1: Auto-detect Pi and MAVProxy if requested
            if self.link == "auto" and self.auto_detect:
                self._attempt_pi_auto_detection()

            # Step 2: Attempt connection to determined link
            if not self._establish_mavlink_connection():
                # Step 3: Fallback to serial port scanning
                if self.auto_detect and self.link != "auto":
                    return self._retry_with_port_detection()

                self.connected = False
                return None

            return self.vehicle

        except Exception as e:
            print(f"[❌] Connection failed: {e}")
            self.connected = False
            return None

    def _attempt_pi_auto_detection(self):
        """
        Attempt to auto-detect Raspberry Pi and MAVProxy connection.

        This tries to import and use simple_auto_connect module to detect
        the Pi's connection string, or falls back to serial port scanning.
        """
        print("[AUTO-CONNECT] Detecting Raspberry Pi and MAVProxy...")
        detected_link = self._auto_detect_pi_mavproxy()

        if detected_link:
            self.link = detected_link
            print(f"[AUTO-CONNECT] ✅ Using: {self.link}")
        else:
            print("[AUTO-CONNECT] ❌ Failed to auto-detect Pi/MAVProxy")
            print("[AUTO-DETECT] Attempting to find Pixhawk on serial ports...")
            detected_link = self._auto_detect_port()

            if detected_link:
                self.link = detected_link
            else:
                print("[❌] Could not auto-detect any connection")
                self.connected = False

    def _establish_mavlink_connection(self) -> bool:
        """
        Establish MAVLink connection and validate with heartbeat.

        This performs the actual connection attempt and waits for a heartbeat
        to confirm communication with the Pixhawk is established.

        Returns:
            True if heartbeat received, False otherwise
        """
        try:
            print(f"[CONNECT] Attempting to connect → {self.link}")

            # Parse connection string to extract baud rate for serial connections
            device, baud = self._parse_connection_string(self.link)

            # Create MAVLink connection with autoreconnect enabled
            if baud:
                # Serial connection with explicit baud rate
                self.vehicle = mavutil.mavlink_connection(
                    device, baud=baud, autoreconnect=True
                )
            else:
                # TCP/UDP connection (baud not needed)
                self.vehicle = mavutil.mavlink_connection(device, autoreconnect=True)

            # Wait for heartbeat message to confirm connection
            print(f"[CONNECT] Waiting for heartbeat...")
            self.vehicle.wait_heartbeat(timeout=10)

            # Connection successful - log details
            print(f"[✅] Heartbeat received — Pixhawk Connected!")
            print(
                f"    System ID: {self.vehicle.target_system}, "
                f"Component ID: {self.vehicle.target_component}"
            )

            self.connected = True
            self.last_heartbeat_time = time.time()
            return True

        except Exception as e:
            print(f"[❌] MAVLink connection error: {e}")
            return False

    def _parse_connection_string(self, link: str):
        """
        Parse connection string to extract device and baud rate.

        For serial connections like "/dev/ttyAMA0:57600", this splits
        the string into device path and baud rate.

        Args:
            link (str): Connection string (e.g., "/dev/ttyAMA0:57600" or "tcp:192.168.1.1:7000")

        Returns:
            tuple: (device, baud_rate) where baud_rate is None for TCP/UDP connections
        """
        # Check if this is a TCP/UDP connection
        if link.startswith("tcp:") or link.startswith("udp:"):
            return link, None

        # Check if this is a serial connection with baud rate
        if ":" in link and not link.startswith("tcp:") and not link.startswith("udp:"):
            parts = link.split(":")
            device = parts[0]
            try:
                baud = int(parts[1])
                return device, baud
            except (ValueError, IndexError):
                # Invalid baud rate, return as-is
                return link, None

        # No baud rate specified
        return link, None

    def _retry_with_port_detection(self):
        """
        Retry connection after attempting port auto-detection.

        This is called as a fallback when initial connection fails.
        It attempts to find the Pixhawk on common serial ports and retries
        the connection with the detected port.

        Returns:
            MAVLink vehicle object if successful, None otherwise
        """
        print("[AUTO-DETECT] Attempting to find Pixhawk on serial ports...")
        detected_link = self._auto_detect_port()

        if detected_link:
            self.link = detected_link
            self.auto_detect = False  # Prevent infinite recursion
            return self.connect()

        return None

    def _auto_detect_pi_mavproxy(self):
        """
        Auto-detect Raspberry Pi and MAVProxy connection.

        Attempts to import simple_auto_connect module which searches for
        the Pi and returns the appropriate connection string for MAVProxy.

        Returns:
            Connection string (e.g., "tcp:raspberrypi.local:7000") if successful
            None if Pi/MAVProxy cannot be auto-detected
        """
        try:
            # Add parent directory to path to find simple_auto_connect module
            parent_dir = Path(__file__).parent.parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            # Import auto-connect detection module
            # Note: This module must be in the project root directory
            from simple_auto_connect import get_connection_string

            connection_string = get_connection_string()
            return connection_string

        except ImportError as e:
            print(f"[AUTO-CONNECT] ⚠️ simple_auto_connect module not available: {e}")
            return None
        except Exception as e:
            print(f"[AUTO-CONNECT] ❌ Error: {e}")
            return None

    def _auto_detect_port(self):
        """
        Auto-detect Pixhawk on common serial ports.

        Uses the portScanner module to scan through common serial port
        configurations (e.g., /dev/ttyUSB0, /dev/ttyACM0) and baud rates
        to find the Pixhawk.

        Returns:
            Connection string in format "PORT:BAUD" if found (e.g., "/dev/ttyUSB0:115200")
            None if no Pixhawk detected
        """
        try:
            from .portScanner import quick_scan

            return quick_scan(verbose=True)
        except ImportError:
            print("[AUTO-DETECT] ⚠️ portScanner module not available")
            return None
        except Exception as e:
            print(f"[AUTO-DETECT] ❌ Error during port scanning: {e}")
            return None

    def set_mode(self, mode="MANUAL"):
        """
        Set ArduSub flight mode.

        Common ArduSub modes:
        - MANUAL: Direct manual control (no stabilization)
        - STABILIZE: Self-level stabilization assistance
        - ALT_HOLD: Maintains altitude (depth in water)
        - DEPTH_HOLD: Maintains depth setpoint
        - POSHOLD: Position hold using GPS/drift

        Args:
            mode (str): Flight mode name (case-insensitive)

        Returns:
            True if mode change successful, False otherwise
        """
        if not self.connected:
            print("[❌] Not connected to Pixhawk - cannot change mode")
            return False

        try:
            self.vehicle.set_mode_apm(mode)
            print(f"[MODE] → {mode}")
            return True
        except Exception as e:
            print(f"[❌] Failed to set mode: {e}")
            return False

    def arm(self):
        """
        Arm the vehicle (enable thrusters for control).

        Arming sends a MAV_CMD_COMPONENT_ARM_DISARM command with parameter=1.
        This enables the propeller thrusters for control. Must be armed before
        sending RC_CHANNELS_OVERRIDE commands.

        Returns:
            True if arm command sent successfully, False otherwise

        Note:
            - Requires connected vehicle
            - Many autopilots have pre-arm safety checks
            - Some modes cannot be armed until checks pass
        """
        if not self.connected:
            print("[❌] Not connected to Pixhawk - cannot arm")
            return False

        try:
            # Send arm command using MAVLink command_long message
            # Parameter 1=1 means ARM, 0 would mean DISARM
            self.vehicle.mav.command_long_send(
                self.vehicle.target_system,
                self.vehicle.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                1,  # param1: 1=arm, 0=disarm
                0,  # param2: unused
                0,  # param3: unused
                0,  # param4: unused
                0,  # param5: unused
                0,  # param6: unused
                0,  # param7: unused
            )
            print("[✅] Thrusters armed!")
            return True
        except Exception as e:
            print(f"[❌] Arming failed: {e}")
            return False

    def disarm(self):
        """
        Disarm the vehicle (disable thrusters).

        Sends MAV_CMD_COMPONENT_ARM_DISARM command with parameter=0.
        This stops all thruster control and prevents accidents.

        Returns:
            True if disarm command sent successfully, False otherwise

        Note:
            - Can only disarm if vehicle is in MANUAL mode or landed
            - Some autopilots require motor output to be neutral before disarming
        """
        if not self.connected:
            print("[❌] Not connected to Pixhawk - cannot disarm")
            return False

        try:
            # Send disarm command using MAVLink command_long message
            # Parameter 1=0 means DISARM
            self.vehicle.mav.command_long_send(
                self.vehicle.target_system,
                self.vehicle.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                0,  # param1: 1=arm, 0=disarm
                0,  # param2: unused
                0,  # param3: unused
                0,  # param4: unused
                0,  # param5: unused
                0,  # param6: unused
                0,  # param7: unused
            )
            print("[⚠️] Thrusters disarmed")
            return True
        except Exception as e:
            print(f"[❌] Disarming failed: {e}")
            return False

    def send_rc_channels_override(self, channels):
        """
        Send RC_CHANNELS_OVERRIDE message to directly control thrusters.

        This is the primary method for controlling thruster PWM values. Each
        channel corresponds to one thruster/propeller on the ROV.

        ArduSub Standard Frame Configuration (BlueROV2 8-Thruster):
            Channel 1: Forward/Backward rotation (Port)
            Channel 2: Lateral movement (Starboard)
            Channel 3: Vertical thrust (Front, Counter-clockwise)
            Channel 4: Vertical thrust (Rear, Counter-clockwise)
            Channel 5: Forward/Backward rotation (Starboard)
            Channel 6: Yaw control (Port)
            Channel 7: Vertical thrust (Front, Clockwise)
            Channel 8: Vertical thrust (Rear, Clockwise)

        Args:
            channels (list): List of 8 PWM values where:
                - 1000 = full reverse
                - 1500 = neutral (no thrust)
                - 2000 = full forward

        Returns:
            True if override message sent successfully, False otherwise

        Note:
            - Vehicle must be ARMED for thrusters to respond
            - Updates rate-limited to ~20 Hz to avoid overwhelming autopilot
            - Connection status checked periodically (0.5s intervals)
        """
        # Check connection status periodically (not every call for efficiency)
        self._check_connection_with_rate_limit()

        # Validate connection
        if not self.connected:
            self._log_connection_error_with_throttle()
            return False

        # Validate channel count
        if len(channels) != 8:
            print(f"[❌] Expected 8 channels, got {len(channels)}")
            return False

        # Sanitize and normalize channel values
        channels = self._clamp_channel_values(channels)

        # Apply debouncing and rate limiting
        if self._should_skip_rc_send(channels):
            return True

        # Log override message periodically (avoid spam)
        self._log_rc_override_periodically(channels)

        # Send the RC override message
        return self._send_rc_override_message(channels)

    def _check_connection_with_rate_limit(self):
        """
        Check connection status, but only periodically to avoid overhead.

        Connection checks are rate-limited to every 0.5 seconds to prevent
        excessive checking from interfering with thruster commands.
        """
        now = time.time()
        if now - self._last_check_time > RC_OVERRIDE_CHECK_INTERVAL:
            self.check_connection()
            self._last_check_time = now

    def _log_connection_error_with_throttle(self):
        """
        Log connection error, but only periodically to avoid console spam.

        This prevents the console from being flooded with repeated error
        messages, which can actually cause timing issues.
        """
        now = time.time()
        if not self._last_error_time or (now - self._last_error_time) > 5.0:
            print("[❌] Not connected to Pixhawk - cannot send thruster commands")
            self._last_error_time = now

    def _clamp_channel_values(self, channels: list) -> list:
        """
        Clamp all channel values to valid PWM range (1000-2000).

        Args:
            channels (list): Raw channel values (may be out of range)

        Returns:
            list: Channels clamped to [1000-2000] range
        """
        return [max(1000, min(2000, int(ch))) for ch in channels]

    def _should_skip_rc_send(self, channels: list) -> bool:
        """
        Determine if RC override should be skipped due to debouncing/rate limiting.

        Skips sending if:
        1. Channels haven't changed from last send
        2. Less than 50ms (20 Hz) has passed since last send

        Args:
            channels (list): Current channel values to send

        Returns:
            True if send should be skipped, False otherwise
        """
        now = time.time()

        # Skip if same as last sent AND rate limit not exceeded
        if (
            self._last_sent_channels == channels
            and (now - self._last_send_time) < RC_OVERRIDE_RATE_LIMIT
        ):
            return True

        return False

    def _log_rc_override_periodically(self, channels: list):
        """
        Log RC override message, but only every 2 seconds to avoid spam.

        Args:
            channels (list): Channel values being sent
        """
        now = time.time()
        if now - self._last_rc_log_time > 2.0:
            print(f"[RC_OVERRIDE] Sending → Ch1-8: {channels}")
            self._last_rc_log_time = now

    def _send_rc_override_message(self, channels: list) -> bool:
        """
        Send RC_CHANNELS_OVERRIDE MAVLink message to autopilot.

        This is the actual low-level message send operation. Failure to send
        marks the connection as disconnected.

        Args:
            channels (list): Validated channel values [ch1-ch8]

        Returns:
            True if send successful, False on error
        """
        try:
            # Send RC override message to autopilot
            self.vehicle.mav.rc_channels_override_send(
                self.vehicle.target_system, self.vehicle.target_component, *channels
            )

            # Update tracking variables
            self._last_sent_channels = channels
            self._last_send_time = time.time()
            self.last_successful_send_time = self._last_send_time

            # Confirm connection if was previously unconfirmed
            if not self.connected:
                self.connected = True
                print("[PIXHAWK] ✅ Connection confirmed via RC_CHANNELS_OVERRIDE!")

            return True

        except Exception as e:
            print(f"[❌] Failed to send RC override: {e}")
            self.connected = False  # Mark as disconnected on error
            return False

    def send_manual_control(self, x=0, y=0, z=500, r=0):
        """
        Send MANUAL_CONTROL message (alternative to RC_CHANNELS_OVERRIDE).

        This provides direct normalized control inputs instead of PWM values.
        Useful for higher-level control interfaces.

        Args:
            x (int): Forward/backward motion (-1000 to 1000)
                    negative = forward, positive = backward
            y (int): Left/right motion (-1000 to 1000)
                    negative = left, positive = right
            z (int): Throttle / depth control (0 to 1000)
                    500 = neutral for ArduSub
                    0 = descend, 1000 = ascend
            r (int): Yaw rotation (-1000 to 1000)
                    negative = rotate left, positive = rotate right

        Returns:
            True if message sent successfully, False otherwise

        Note:
            - Less commonly used than RC_CHANNELS_OVERRIDE for direct control
            - Useful for autonomous guidance systems
        """
        if not self.connected:
            print("[❌] Not connected to Pixhawk - cannot send manual control")
            return False

        try:
            # Send MANUAL_CONTROL message
            self.vehicle.mav.manual_control_send(
                self.vehicle.target_system,
                x,  # forward/back
                y,  # left/right
                z,  # throttle
                r,  # yaw
                0,  # buttons (16-bit bitmask)
            )
            return True
        except Exception as e:
            print(f"[❌] Failed to send manual control: {e}")
            return False

    def check_connection(self) -> bool:
        """
        Check if connection to Pixhawk is still alive and healthy.

        This method uses dual strategies to verify connection:
        1. **Heartbeat monitoring**: Listens for MAVLink HEARTBEAT messages
        2. **Successful sends**: Tracks RC_CHANNELS_OVERRIDE success

        Connection is considered alive if:
        - Recent heartbeat received (< heartbeat_timeout), OR
        - Recent successful send (< 5 seconds ago)

        Automatically triggers reconnection attempts if connection lost.

        Returns:
            True if connected and responding, False if disconnected
        """
        # Validate vehicle object exists
        if not self.vehicle:
            self.connected = False
            self._try_auto_reconnect()
            return False

        try:
            # Check for incoming HEARTBEAT messages
            msg = self.vehicle.recv_match(type="HEARTBEAT", blocking=False, timeout=0)

            if msg:
                # Heartbeat received - connection is healthy
                self.last_heartbeat_time = time.time()
                if not self.connected:
                    print("[PIXHAWK] ✅ Connection restored via heartbeat!")
                self.connected = True
            else:
                # No heartbeat received - check if we've lost connection
                self._evaluate_connection_status()

            return self.connected

        except Exception as e:
            print(f"[PIXHAWK] ❌ Connection check failed: {e}")
            self.connected = False
            self._try_auto_reconnect()
            return False

    def _evaluate_connection_status(self):
        """
        Evaluate connection status based on heartbeat and send timeouts.

        Updates self.connected based on:
        - Time since last heartbeat
        - Time since last successful RC send

        This uses a dual-criteria approach so that even if heartbeats
        are not being received, we stay connected if RC sends are working.
        """
        now = time.time()
        time_since_heartbeat = now - self.last_heartbeat_time
        time_since_send = now - self.last_successful_send_time

        # Check if truly disconnected (no heartbeat AND no recent sends)
        recent_send = time_since_send < SUCCESSFUL_SEND_TIMEOUT

        if time_since_heartbeat > self.heartbeat_timeout and not recent_send:
            # No heartbeat AND no recent successful send = truly disconnected
            if self.connected:
                print(
                    f"[PIXHAWK] ❌ Connection lost! "
                    f"(No heartbeat for {time_since_heartbeat:.1f}s, "
                    f"no send for {time_since_send:.1f}s)"
                )
            self.connected = False
            self._try_auto_reconnect()
        else:
            # Keep connection alive if we're sending successfully
            if recent_send and not self.connected:
                self.connected = True
                print("[PIXHAWK] ✅ Connection confirmed via RC_CHANNELS_OVERRIDE!")

    def _try_auto_reconnect(self):
        """
        Attempt to reconnect to Pixhawk after connection loss.

        Reconnect attempts are rate-limited to every reconnect_interval seconds
        to avoid excessive reconnection attempts that could cause issues.

        For TCP connections, relies on autoreconnect feature of MAVLink.
        For serial connections, attempts to close and recreate the connection.
        """
        now = time.time()

        # Rate-limit reconnection attempts
        if now - self.last_reconnect_attempt < self.reconnect_interval:
            return

        self.last_reconnect_attempt = now
        print("[PIXHAWK] 🔄 Attempting auto-reconnect...")

        try:
            # Close existing connection for non-TCP links
            # (TCP handles reconnection automatically)
            if self.vehicle and not self.link.startswith("tcp"):
                try:
                    self.vehicle.close()
                except Exception:
                    pass
                self.vehicle = None

            # Recreate MAVLink connection if needed
            if not self.vehicle:
                print(f"[CONNECT] Attempting to connect → {self.link}")
                # Parse connection string to handle serial baud rates correctly
                device, baud = self._parse_connection_string(self.link)
                if baud:
                    self.vehicle = mavutil.mavlink_connection(
                        device, baud=baud, autoreconnect=True
                    )
                else:
                    self.vehicle = mavutil.mavlink_connection(
                        device, autoreconnect=True
                    )

            # Check for heartbeat to confirm reconnection
            msg = self.vehicle.recv_match(type="HEARTBEAT", blocking=True, timeout=3)

            if msg:
                print(f"[✅] Heartbeat received — Pixhawk Connected!")
                print(
                    f"    System ID: {msg.get_srcSystem()}, "
                    f"Component ID: {msg.get_srcComponent()}"
                )
                self.connected = True
                self.last_heartbeat_time = time.time()
            else:
                print(f"[⏳] No heartbeat received, will retry later")
                self.connected = False

        except KeyboardInterrupt:
            # Re-raise keyboard interrupt to allow clean shutdown
            raise
        except Exception as e:
            print(f"[PIXHAWK] ❌ Auto-reconnect failed: {e}")
            self.connected = False

    def get_attitude(self) -> dict:
        """
        Get current vehicle attitude (orientation) data.

        Returns:
            Dictionary with attitude information:
            - heading (float): Heading in degrees (0-360)
            - pitch (float): Pitch angle in degrees
            - roll (float): Roll angle in degrees
            - connected (bool): True if data retrieved successfully

        Note:
            Returns default values (0.0) if not connected or no data available.
        """
        import math

        if not self.connected or not self.vehicle:
            return {"connected": False, "heading": 0.0, "pitch": 0.0, "roll": 0.0}

        try:
            # Try to receive ATTITUDE message (non-blocking)
            msg = self.vehicle.recv_match(type="ATTITUDE", blocking=False, timeout=0.1)

            if msg:
                # Convert radians to degrees
                roll_deg = math.degrees(msg.roll)
                pitch_deg = math.degrees(msg.pitch)
                yaw_rad = msg.yaw

                # Convert yaw from radians to degrees and normalize to 0-360
                heading_deg = math.degrees(yaw_rad)
                if heading_deg < 0:
                    heading_deg += 360

                return {
                    "connected": True,
                    "heading": heading_deg,
                    "pitch": pitch_deg,
                    "roll": roll_deg,
                }
            else:
                # No message available, return last known values or defaults
                return {"connected": True, "heading": 0.0, "pitch": 0.0, "roll": 0.0}
        except Exception as e:
            print(f"[ATTITUDE] Error getting attitude data: {e}")
            return {"connected": False, "heading": 0.0, "pitch": 0.0, "roll": 0.0}

    def get_status(self) -> dict:
        """
        Get current vehicle status and connection information.

        Performs a connection health check and returns detailed status about
        the Pixhawk connection and vehicle configuration.

        Returns:
            Dictionary with status information:
            - connected (bool): True if connected and responding
            - system_id (int): MAVLink system ID (usually 1)
            - component_id (int): MAVLink component ID (usually 1)
            - last_heartbeat (float): Seconds since last heartbeat received

        Example:
            status = connection.get_status()
            if status['connected']:
                print(f"Vehicle System ID: {status['system_id']}")
        """
        # Update connection status first
        self.check_connection()

        if not self.connected:
            return {"connected": False}

        try:
            # Gather connection and vehicle information
            return {
                "connected": True,
                "system_id": self.vehicle.target_system,
                "component_id": self.vehicle.target_component,
                "last_heartbeat": time.time() - self.last_heartbeat_time,
            }
        except Exception:
            return {"connected": False}

    def close(self):
        """
        Close MAVLink connection and cleanup resources.

        This should be called during application shutdown to gracefully
        close the connection and ensure proper cleanup.

        Note:
            - Vehicle should be disarmed before closing
            - Safe to call multiple times
        """
        if self.vehicle:
            print("[DISCONNECT] Closing MAVLink connection")
            try:
                self.vehicle.close()
            except Exception:
                pass
            finally:
                self.vehicle = None
                self.connected = False
