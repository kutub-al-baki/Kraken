# 🚀 Quick Reference - UIU MARINER

## Deploy to Pi (One Command)

```powershell
.\deploy_to_pi.ps1
```

This syncs all `pi_scripts` files to your Raspberry Pi automatically.

## First Time Setup

**On Pi (after first deployment):**

```bash
ssh pi@raspberrypi.local
pip3 install pymavlink pyserial flask picamera2 opencv-python-headless numpy
```

## Start Services

**On Pi:**

```bash
cd ~/mariner/pi_scripts
./start_all_services.sh
```

**View logs:**

```bash
screen -ls          # List services
screen -r cam0      # Camera 0
screen -r cam1      # Camera 1
screen -r sensors   # Sensors
screen -r mavproxy  # MAVLink
```

## Test Cameras

Open in browser:

- http://raspberrypi.local:8080/video_feed
- http://raspberrypi.local:8081/video_feed

## Run Ground Station

```bash
python launch_mariner.py
```

## Common Commands

| Task           | Command                                                                         |
| -------------- | ------------------------------------------------------------------------------- |
| Deploy updates | `.\deploy_to_pi.ps1`                                                            |
| Start all      | `ssh pi@raspberrypi.local "cd ~/mariner/pi_scripts && ./start_all_services.sh"` |
| Stop all       | `ssh pi@raspberrypi.local "pkill -f 'pi_.*_server'"`                            |
| View camera 0  | `ssh pi@raspberrypi.local "screen -r cam0"`                                     |

## Ports

- **8080** - Camera 0
- **8081** - Camera 1
- **5002** - Sensors
- **7000** - MAVLink

That's it! 🎉
