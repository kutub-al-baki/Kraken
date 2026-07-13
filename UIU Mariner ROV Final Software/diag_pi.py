
import socket
import requests
import time

PI_IP = "192.168.1.100"
PORTS = {
    "MAVLink Relay": 7000,
    "Sensor Server": 5002,
    "Camera 0": 8080,
    "Camera 1": 8081
}

print(f"--- DIAGNOSING PI AT {PI_IP} ---")

for name, port in PORTS.items():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((PI_IP, port))
        print(f"[✅] {name} (Port {port}): Reachable")
        s.close()
    except Exception as e:
        print(f"[❌] {name} (Port {port}): UNREACHABLE - {e}")

print("\n--- TESTING CAMERA STREAM (HEAD) ---")
try:
    resp = requests.head(f"http://{PI_IP}:8080/video_feed", timeout=2)
    print(f"Camera 0 Header: {resp.status_code} - {resp.headers.get('Content-Type')}")
except Exception as e:
    print(f"Camera 0 error: {e}")

try:
    resp = requests.head(f"http://{PI_IP}:8081/video_feed", timeout=2)
    print(f"Camera 1 Header: {resp.status_code} - {resp.headers.get('Content-Type')}")
except Exception as e:
    print(f"Camera 1 error: {e}")
