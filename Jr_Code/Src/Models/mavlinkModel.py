"""
MAVLink State Model
Represents the current state and data from the Pixhawk autopilot.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum
import time


class ConnectionState(Enum):
    """Connection states"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class TelemetryData:
    """Telemetry data from Pixhawk"""

    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    heading: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    groundspeed: float = 0.0

    # Battery info
    battery_voltage: float = 0.0
    battery_current: float = 0.0
    battery_remaining: int = 0

    # System status
    system_armed: bool = False
    is_flying: bool = False

    # Timestamp
    last_update: float = field(default_factory=time.time)


@dataclass
class RCChannels:
    """RC channel values (8 channels for 8 thrusters)"""

    channels: list = field(default_factory=lambda: [1500] * 8)

    def __post_init__(self):
        """Ensure 8 channels"""
        while len(self.channels) < 8:
            self.channels.append(1500)
        self.channels = self.channels[:8]

    def get_channel(self, channel: int) -> int:
        """Get channel value (1-indexed)"""
        if 1 <= channel <= 8:
            return self.channels[channel - 1]
        return 1500

    def set_channel(self, channel: int, value: int):
        """Set channel value (1-indexed), clamped to 1000-2000"""
        if 1 <= channel <= 8:
            self.channels[channel - 1] = max(1000, min(2000, value))


class MAVLinkState:
    """Overall MAVLink connection and vehicle state"""

    def __init__(self):
        self.connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.telemetry: TelemetryData = TelemetryData()
        self.rc_channels: RCChannels = RCChannels()
        self.system_id: int = 0
        self.component_id: int = 0
        self.autopilot_type: int = 0
        self.system_type: int = 0
        self.vehicle_mode: str = "MANUAL"

        # Timestamps
        self.connection_established_time: Optional[float] = None
        self.last_heartbeat_time: Optional[float] = None
        self.last_message_time: Optional[float] = None

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connection_state == ConnectionState.CONNECTED

    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat_time = time.time()
        if self.connection_established_time is None:
            self.connection_established_time = self.last_heartbeat_time

    def reset(self):
        """Reset to initial state"""
        self.connection_state = ConnectionState.DISCONNECTED
        self.telemetry = TelemetryData()
        self.rc_channels = RCChannels()
        self.system_id = 0
        self.component_id = 0
        self.connection_established_time = None
        self.last_heartbeat_time = None
        self.last_message_time = None
