#!/bin/bash
# ============================================================================
# UIU MARINER - Pi Automated Startup Script
# ============================================================================
# This script automatically initializes all PIU components on Raspberry Pi:
#   - PyMAVLink connection to Pixhawk
#   - Sensor server (BMP388)
#   - Camera streaming servers (H.264 UDP)
#   - Thruster control setup
#   - Logging system
#
# Usage:
#   bash pi_autostart_all.sh     (Start all services)
#   bash pi_autostart_all.sh stop (Stop all services)
#
# Installation:
#   chmod +x pi_autostart_all.sh
#   sudo cp pi_autostart_all.sh /opt/mariner/
#   sudo chown pi:pi /opt/mariner/pi_autostart_all.sh
#
# Autostart on Boot (via cron):
#   crontab -e
#   Add: @reboot bash /opt/mariner/pi_autostart_all.sh
#
# Or via systemd:
#   sudo cp pi_autostart_all.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable pi_autostart_all.service
#   sudo systemctl start pi_autostart_all.service
# ============================================================================

# Note: set -e removed to allow script to continue even if some services fail

# ============================================================================
# CONFIGURATION
# ============================================================================

PI_USER="pi"
PI_HOME="/home/pi"
PROJECT_DIR="${PI_HOME}"
VENV_DIR="${PROJECT_DIR}/venv"
LOGS_DIR="${PROJECT_DIR}/logs"
PID_DIR="${PROJECT_DIR}/pids"  # Use home directory to avoid permission issues

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}[✓] $1${NC}"
}

print_error() {
    echo -e "${RED}[✗] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[*] $1${NC}"
}

check_directory() {
    if [ ! -d "$1" ]; then
        print_error "Directory not found: $1"
        return 1
    fi
    print_success "Found: $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "Command not found: $1"
        return 1
    fi
    print_success "Found: $1"
}

# ============================================================================
# STARTUP FUNCTIONS
# ============================================================================

setup_environment() {
    print_header "Setting up environment"
    
    # Create directories
    mkdir -p "$LOGS_DIR"
    mkdir -p "$PID_DIR"
    
    # Create virtual environment if not exists
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    print_info "Updating pip..."
    pip install --upgrade pip > /dev/null 2>&1
    
    # Install requirements
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        print_info "Installing dependencies from requirements.txt..."
        pip install -r "$PROJECT_DIR/requirements.txt" > /dev/null 2>&1
        print_success "Dependencies installed"
    fi
}

check_pixhawk_connection() {
    print_header "Checking Pixhawk Connection"
    
    print_info "Checking if Pixhawk serial device exists..."
    
    # Check if serial device exists
    if [ -e "/dev/ttyAMA0" ]; then
        print_success "Serial device /dev/ttyAMA0 found"
        return 0
    elif [ -e "/dev/ttyUSB0" ]; then
        print_warning "Using /dev/ttyUSB0 instead of /dev/ttyAMA0"
        return 0
    elif [ -e "/dev/ttyACM0" ]; then
        print_warning "Using /dev/ttyACM0 instead of /dev/ttyAMA0"
        return 0
    else
        print_warning "Pixhawk serial device not found (will be checked by MAVProxy)"
        return 0  # Don't fail, let MAVProxy handle it
    fi
}

start_sensor_server() {
    print_header "Starting Sensor Server"
    
    # Check if I2C is enabled
    if [ ! -e "/dev/i2c-1" ] && [ ! -e "/dev/i2c-0" ]; then
        print_warning "I2C device not found. Enable with: sudo raspi-config → Interface Options → I2C"
        print_warning "Skipping sensor server..."
        return 0
    fi
    
    print_info "Launching sensor telemetry server (BMP388)..."
    print_warning "Sensor server requires sudo for I2C access..."
    
    # Run with sudo for I2C access
    sudo nohup python3 "$PROJECT_DIR/pi_scripts/pi_sensor_server.py" \
        > "$LOGS_DIR/sensor_server.log" 2>&1 &
    
    SENSOR_PID=$!
    echo "$SENSOR_PID" > "$PID_DIR/sensor_server.pid"
    
    sleep 2
    
    # Check if process is still running
    if sudo ps -p $SENSOR_PID > /dev/null 2>&1; then
        print_success "Sensor server started (PID: $SENSOR_PID)"
        return 0
    else
        print_warning "Sensor server may have failed - check logs: tail -f $LOGS_DIR/sensor_server.log"
        # Don't fail - continue with other services
        return 0
    fi
}

start_camera_servers() {
    print_header "Starting Camera Servers"
    
    # Get Ground Station IP (from SSH connection or network)
    GROUND_STATION_IP=$(python3 "$PROJECT_DIR/pi_scripts/get_ground_station_ip.py" 2>/dev/null | tail -1 || echo "192.168.1.255")
    
    # Validate it's a proper IP address, otherwise use broadcast
    if [[ ! $GROUND_STATION_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        GROUND_STATION_IP="192.168.1.255"
    fi
    
    print_info "Ground Station IP: $GROUND_STATION_IP"
    print_info "Launching camera 0 streaming server (UDP port 5000)..."
    
    nohup python3 "$PROJECT_DIR/pi_scripts/pi_camera_server.py" 0 "$GROUND_STATION_IP" 5000 \
        > "$LOGS_DIR/camera_server_0.log" 2>&1 &
    
    CAM0_PID=$!
    echo "$CAM0_PID" > "$PID_DIR/camera_server_0.pid"
    
    sleep 1
    print_info "Launching camera 1 streaming server (UDP port 5001)..."
    
    nohup python3 "$PROJECT_DIR/pi_scripts/pi_camera_server.py" 1 "$GROUND_STATION_IP" 5001 \
        > "$LOGS_DIR/camera_server_1.log" 2>&1 &
    
    CAM1_PID=$!
    echo "$CAM1_PID" > "$PID_DIR/camera_server_1.pid"
    
    sleep 2
    
    # Camera servers might fail if cameras aren't connected - don't fail the whole script
    if ps -p $CAM0_PID > /dev/null 2>&1 || ps -p $CAM1_PID > /dev/null 2>&1; then
        print_success "Camera servers started (at least one camera active)"
        return 0
    else
        print_warning "Camera servers may have failed - check if cameras are connected"
        return 0  # Don't fail - continue with other services
    fi
}

start_mavproxy_relay() {
    print_header "Starting MAVProxy TCP Relay"
    
    print_info "Launching MAVProxy relay server (TCP port 7000)..."
    
    # Check if MAVProxy is installed
    if ! command -v mavproxy.py &> /dev/null; then
        print_warning "MAVProxy not installed. Installing..."
        pip install MAVProxy > /dev/null 2>&1
    fi
    
    nohup mavproxy.py --master=/dev/ttyAMA0 --baud=57600 --out=tcpin:0.0.0.0:7000 \
        --daemon --non-interactive \
        > "$LOGS_DIR/mavproxy.log" 2>&1 &
    
    MAVPROXY_PID=$!
    echo "$MAVPROXY_PID" > "$PID_DIR/mavproxy.pid"
    
    sleep 3
    
    if ps -p $MAVPROXY_PID > /dev/null 2>&1; then
        print_success "MAVProxy relay started (PID: $MAVPROXY_PID)"
        return 0
    else
        print_warning "MAVProxy relay may have failed - check if Pixhawk is connected"
        print_info "Check logs: tail -f $LOGS_DIR/mavproxy.log"
        return 0  # Don't fail - might work once Pixhawk is connected
    fi
}

initialize_thrusters() {
    print_header "Initializing Thruster Control"
    
    print_info "Thrusters will be initialized by Ground Station..."
    print_success "Thruster control ready (controlled via MAVLink from Ground Station)"
    return 0
}

# ============================================================================
# SHUTDOWN FUNCTIONS
# ============================================================================

stop_all_services() {
    print_header "Stopping all services"
    
    # Stop sensor server
    if [ -f "$PID_DIR/sensor_server.pid" ]; then
        SENSOR_PID=$(cat "$PID_DIR/sensor_server.pid")
        if ps -p $SENSOR_PID > /dev/null; then
            kill $SENSOR_PID
            print_success "Sensor server stopped"
        fi
        rm -f "$PID_DIR/sensor_server.pid"
    fi
    
    # Stop camera servers
    for i in 0 1; do
        if [ -f "$PID_DIR/camera_server_${i}.pid" ]; then
            CAM_PID=$(cat "$PID_DIR/camera_server_${i}.pid")
            if ps -p $CAM_PID > /dev/null; then
                kill $CAM_PID
                print_success "Camera server $i stopped"
            fi
            rm -f "$PID_DIR/camera_server_${i}.pid"
        fi
    done
    
    # Stop MAVProxy
    if [ -f "$PID_DIR/mavproxy.pid" ]; then
        MAVPROXY_PID=$(cat "$PID_DIR/mavproxy.pid")
        if ps -p $MAVPROXY_PID > /dev/null; then
            kill $MAVPROXY_PID
            print_success "MAVProxy relay stopped"
        fi
        rm -f "$PID_DIR/mavproxy.pid"
    fi
    
    print_success "All services stopped"
}

show_status() {
    print_header "Service Status"
    
    echo -e "${BLUE}Running Services:${NC}"
    
    [ -f "$PID_DIR/sensor_server.pid" ] && ps -p $(cat "$PID_DIR/sensor_server.pid") > /dev/null && \
        echo -e "  ${GREEN}✓${NC} Sensor Server (PID: $(cat "$PID_DIR/sensor_server.pid"))" || \
        echo -e "  ${RED}✗${NC} Sensor Server (stopped)"
    
    for i in 0 1; do
        [ -f "$PID_DIR/camera_server_${i}.pid" ] && ps -p $(cat "$PID_DIR/camera_server_${i}.pid") > /dev/null && \
            echo -e "  ${GREEN}✓${NC} Camera Server $i (PID: $(cat "$PID_DIR/camera_server_${i}.pid"))" || \
            echo -e "  ${RED}✗${NC} Camera Server $i (stopped)"
    done
    
    [ -f "$PID_DIR/mavproxy.pid" ] && ps -p $(cat "$PID_DIR/mavproxy.pid") > /dev/null && \
        echo -e "  ${GREEN}✓${NC} MAVProxy Relay (PID: $(cat "$PID_DIR/mavproxy.pid"))" || \
        echo -e "  ${RED}✗${NC} MAVProxy Relay (stopped)"
    
    echo -e "\n${BLUE}Pixhawk Connection:${NC}"
    if [ -e "/dev/ttyAMA0" ]; then
        echo -e "  ${GREEN}✓${NC} Serial device available (/dev/ttyAMA0)"
    else
        echo -e "  ${RED}✗${NC} Serial device not found"
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    case "${1:-start}" in
        start)
            print_header "UIU MARINER - Automatic Startup"
            
            # Setup
            setup_environment || exit 1
            
            # Checks
            check_directory "$PROJECT_DIR" || print_warning "Project directory not found, using $PROJECT_DIR"
            check_command "python3" || exit 1
            
            # Start services (continue even if some fail)
            check_pixhawk_connection
            start_sensor_server
            start_camera_servers
            start_mavproxy_relay
            initialize_thrusters
            
            print_header "Startup Complete - Check Status Below"
            sleep 1
            show_status
            ;;
            
        stop)
            stop_all_services
            ;;
            
        status)
            show_status
            ;;
            
        restart)
            stop_all_services
            sleep 2
            main start
            ;;
            
        *)
            echo "Usage: $0 {start|stop|status|restart}"
            exit 1
            ;;
    esac
}

main "$@"
