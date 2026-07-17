import urllib.request
import socket
import time
import json
from pathlib import Path

def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None

def check_web_server():
    print("[1/4] Checking Web Server (FastAPI)...")
    status = get_json("http://localhost:8000/api/status")
    if status:
        print(f"  ✅ Web Server is UP")
        print(f"  - Pixhawk Connected: {status['connections']['pixhawk']}")
        print(f"  - Joystick Connected: {status['connections']['joystick']}")
        print(f"  - Current Depth: {status['telemetry']['depth']}m")
        return status
    else:
        print(f"  ❌ Web Server is DOWN or Unreachable")
    return None

def check_sensor_server():
    print("[2/4] Checking Pi Sensor Server (Port 5002)...")
    config_path = Path("config.json")
    host = "192.168.1.100"
    if config_path.exists():
        with open(config_path) as f:
            host = json.load(f).get("sensors", {}).get("host", host)
            
    try:
        s = socket.create_connection((host, 5002), timeout=3)
        print(f"  ✅ Pi Sensor Server is REACHABLE at {host}:5002")
        data = s.recv(1024).decode().strip()
        print(f"  - Sample Data: {data}")
        s.close()
    except Exception as e:
        print(f"  ❌ Pi Sensor Server is UNREACHABLE: {e}")

def check_pixhawk_direct():
    print("[3/4] Checking Direct MAVLink Connection...")
    try:
        from pymavlink import mavutil
        conn_str = "tcp:192.168.1.100:7000"
        vehicle = mavutil.mavlink_connection(conn_str)
        hb = vehicle.wait_heartbeat(timeout=5)
        if hb:
            print(f"  ✅ Pixhawk is SENDING heartbeats")
            # Pull one VFR_HUD
            msg = vehicle.recv_match(type='VFR_HUD', blocking=True, timeout=2)
            if msg:
                print(f"  - Raw Pixhawk Depth: {msg.alt}m")
            else:
                print("  - VFR_HUD not received yet")
        else:
            print("  ❌ No heartbeat from Pixhawk")
    except Exception as e:
        print(f"  ❌ MAVLink diagnostic error: {e}")

def check_frontend():
    print("[4/4] Checking Frontend Server (Vite)...")
    try:
        with urllib.request.urlopen("http://localhost:5173", timeout=2) as response:
            if response.status == 200:
                print(f"  ✅ Frontend is UP (http://localhost:5173)")
            else:
                print(f"  ⚠️  Frontend returned status {response.status}")
    except Exception:
        print(f"  ❌ Frontend is DOWN")

if __name__ == "__main__":
    report_path = Path("health_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")

        log("="*60)
        log("🚀 UIU MARINER - FULL SYSTEM HEALTH CHECK")
        log("="*60)
        
        # 1
        log("[1/4] Checking Web Server (FastAPI)...")
        status = get_json("http://localhost:8000/api/status")
        if status:
            log("  ✅ Web Server is UP")
            log(f"  - Pixhawk Connected: {status['connections']['pixhawk']}")
            log(f"  - Joystick Connected: {status['connections']['joystick']}")
            log(f"  - Current Depth: {status['telemetry']['depth']}m")
        else:
            log("  ❌ Web Server is DOWN or Unreachable")
        
        log("-" * 40)
        
        # 2
        log("[2/4] Checking Pi Sensor Server (Port 5002)...")
        host = "192.168.1.100"
        try:
            s = socket.create_connection((host, 5002), timeout=3)
            log(f"  ✅ Pi Sensor Server is REACHABLE at {host}:5002")
            data = s.recv(1024).decode().strip()
            log(f"  - Sample Data: {data}")
            s.close()
        except Exception as e:
            log(f"  ❌ Pi Sensor Server is UNREACHABLE: {e}")
            
        log("-" * 40)
        
        # 3
        log("[3/4] Checking Direct MAVLink Connection...")
        try:
            from pymavlink import mavutil
            conn_str = "tcp:192.168.1.100:7000"
            vehicle = mavutil.mavlink_connection(conn_str)
            hb = vehicle.wait_heartbeat(timeout=5)
            if hb:
                log(f"  ✅ Pixhawk is SENDING heartbeats")
                msg = vehicle.recv_match(type='VFR_HUD', blocking=True, timeout=2)
                if msg:
                    log(f"  - Raw Pixhawk Depth: {msg.alt}m")
                else:
                    log("  - VFR_HUD not received yet")
            else:
                log("  ❌ No heartbeat from Pixhawk")
            vehicle.close()
        except Exception as e:
            log(f"  ❌ MAVLink diagnostic error: {e}")
            
        log("-" * 40)
        
        # 4
        log("[4/4] Checking Frontend Server (Vite)...")
        try:
            with urllib.request.urlopen("http://localhost:5173", timeout=2) as response:
                if response.status == 200:
                    log(f"  ✅ Frontend is UP (http://localhost:5173)")
                else:
                    log(f"  ⚠️  Frontend returned status {response.status}")
        except Exception:
            log(f"  ❌ Frontend is DOWN")
            
        log("="*60)
