# Ethernet Tether Setup for Underwater Operations

## Problem

Your Pi shows `eth0` is UP but has no IPv4 address:

```
eth0: inet6 fe80::83e1:a66e:deb:9917  ← Only IPv6, no IPv4!
```

This prevents communication between Ground Station and ROV.

## Solution: Configure Static IP

### On Raspberry Pi

**1. Edit DHCP configuration:**

```bash
sudo nano /etc/dhcpcd.conf
```

**2. Add these lines at the end:**

```bash
# Static IP for Ethernet tether (underwater operations)
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8
```

**3. Save and exit:**

- Press `Ctrl+X`
- Press `Y` to confirm
- Press `Enter`

**4. Reboot:**

```bash
sudo reboot
```

**5. Verify after reboot:**

```bash
ifconfig eth0
# Should now show: inet 192.168.1.100
```

### On Ground Station (Windows)

**1. Open Network Connections:**

- Press `Win + R`
- Type: `ncpa.cpl`
- Press Enter

**2. Configure Ethernet adapter:**

- Right-click on Ethernet adapter
- Select "Properties"
- Double-click "Internet Protocol Version 4 (TCP/IPv4)"

**3. Set static IP:**

```
○ Use the following IP address:
  IP address: 192.168.1.10
  Subnet mask: 255.255.255.0
  Default gateway: 192.168.1.1

○ Use the following DNS server addresses:
  Preferred DNS: 8.8.8.8
  Alternate DNS: 8.8.4.4
```

**4. Click OK → OK**

### Test Connection

**From Ground Station:**

```powershell
# Test ping
ping 192.168.1.100

# Test SSH
ssh pi@192.168.1.100
```

**Expected result:**

```
Reply from 192.168.1.100: bytes=32 time<1ms TTL=64
```

## Update Configuration

**Update config.json to use Ethernet IP:**

For Ethernet operations, you can either:

**Option 1: Update config.json directly:**

```json
{
  "camera": {
    "stream_url0": "http://192.168.1.100:8080/video_feed",
    "stream_url1": "http://192.168.1.100:8081/video_feed"
  },
  "mavlink_connection": "tcp:192.168.1.100:7000",
  "sensors": {
    "host": "192.168.1.100"
  }
}
```

**Option 2: Use deployment with IP:**

```powershell
.\deploy_to_pi.ps1 -PiHost 192.168.1.100
```

## Verify All Services Work

**1. Deploy to Pi:**

```powershell
.\deploy_to_pi.ps1 -PiHost 192.168.1.100
```

**2. Start services on Pi:**

```bash
ssh pi@192.168.1.100
cd ~/mariner/pi_scripts
./start_all_services.sh
```

**3. Test cameras in browser:**

```
http://192.168.1.100:8080/video_feed
http://192.168.1.100:8081/video_feed
```

**4. Run Ground Station:**

```powershell
python launch_mariner.py
```

## Network Summary

| Component      | WiFi (Testing)    | Ethernet (Underwater) |
| -------------- | ----------------- | --------------------- |
| Pi Hostname    | raspberrypi.local | 192.168.1.100         |
| Ground Station | Auto-DHCP         | 192.168.1.10          |
| Camera 0       | :8080             | :8080                 |
| Camera 1       | :8081             | :8081                 |
| MAVLink        | :7000             | :7000                 |
| Sensors        | :5002             | :5002                 |

## Troubleshooting

### Pi still has no IP after reboot

```bash
# Check dhcpcd service
sudo systemctl status dhcpcd

# Restart networking
sudo systemctl restart dhcpcd

# Check configuration
cat /etc/dhcpcd.conf | grep -A 5 eth0
```

### Can't ping from Ground Station

```bash
# On Pi: Check if IP is assigned
ip addr show eth0

# On Ground Station: Check cable and adapter
ipconfig
# Should show 192.168.1.10 on Ethernet adapter

# Disable Windows Firewall temporarily to test
```

### Services won't connect

```bash
# Make sure services are listening on all interfaces (0.0.0.0)
# Check with:
sudo netstat -tulpn | grep -E '8080|8081|5002|7000'
```

## Yes, All Functionality Works Over Ethernet! ✅

The system is designed to work over ANY IP connection:

- ✅ Camera streaming (HTTP)
- ✅ MAVLink control (TCP)
- ✅ Sensor telemetry (TCP)
- ✅ SSH for management

Just configure static IPs and update the addresses in config.json or use IP instead of hostname!
