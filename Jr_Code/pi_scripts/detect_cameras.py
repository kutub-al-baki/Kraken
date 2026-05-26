#!/usr/bin/env python3
"""
Camera Detection Script for Raspberry Pi
Detects all available cameras (Pi Camera Module and USB webcams)
Returns structured data for GUI integration
"""

import subprocess
import json
import os
import sys


def detect_pi_cameras():
    """Detect Raspberry Pi Camera Modules using libcamera."""
    cameras = []

    try:
        # Check if libcamera-hello is available
        result = subprocess.run(
            ["which", "libcamera-hello"], capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            print("❌ libcamera tools not installed", file=sys.stderr)
            return cameras

        # List cameras using libcamera
        result = subprocess.run(
            ["libcamera-hello", "--list-cameras"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout:
            # Parse output
            lines = result.stdout.split("\n")
            current_camera = None

            for line in lines:
                # Look for camera index lines like "0 : imx219"
                if ":" in line and len(line.strip()) > 0:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        try:
                            cam_id = int(parts[0].strip())
                            cam_model = (
                                parts[1].strip().split()[0]
                                if parts[1].strip()
                                else "Unknown"
                            )

                            cameras.append(
                                {
                                    "id": cam_id,
                                    "type": "pi_camera",
                                    "name": f"Pi Camera {cam_id} ({cam_model})",
                                    "model": cam_model,
                                    "device": f"/dev/video{cam_id}",
                                    "interface": "libcamera",
                                }
                            )
                        except (ValueError, IndexError):
                            continue

            if cameras:
                print(f"✅ Found {len(cameras)} Pi Camera(s)", file=sys.stderr)
            else:
                print("❌ No Pi Cameras detected", file=sys.stderr)
        else:
            print("❌ libcamera-hello failed or no cameras found", file=sys.stderr)

    except subprocess.TimeoutExpired:
        print("❌ Camera detection timed out", file=sys.stderr)
    except Exception as e:
        print(f"❌ Error detecting Pi cameras: {e}", file=sys.stderr)

    return cameras


def detect_usb_cameras():
    """Detect USB webcams using v4l2."""
    cameras = []

    try:
        # Get all video devices
        video_devices = []
        for i in range(10):  # Check video0 to video9
            device_path = f"/dev/video{i}"
            if os.path.exists(device_path):
                video_devices.append(device_path)

        if not video_devices:
            print("❌ No video devices found at /dev/video*", file=sys.stderr)
            return cameras

        print(f"📹 Found {len(video_devices)} video device(s)", file=sys.stderr)

        # Check if v4l2-ctl is available
        result = subprocess.run(
            ["which", "v4l2-ctl"], capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            print(
                "⚠️  v4l2-utils not installed, limited info available", file=sys.stderr
            )
            # Add basic entries without detailed info
            for device in video_devices:
                device_id = int(device.replace("/dev/video", ""))
                cameras.append(
                    {
                        "id": device_id,
                        "type": "usb",
                        "name": f"USB Camera {device_id}",
                        "model": "Unknown",
                        "device": device,
                        "interface": "v4l2",
                    }
                )
            return cameras

        # Get detailed info for each device
        for device in video_devices:
            try:
                result = subprocess.run(
                    ["v4l2-ctl", "--device", device, "--info"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    card_type = "Unknown"
                    driver_name = "Unknown"

                    for line in result.stdout.split("\n"):
                        if "Card type" in line:
                            card_type = line.split(":", 1)[1].strip()
                        elif "Driver name" in line:
                            driver_name = line.split(":", 1)[1].strip()

                    device_id = int(device.replace("/dev/video", ""))

                    # Filter out metadata devices (they share the same physical device)
                    # Usually metadata devices have 'metadata' in driver or card name
                    if (
                        "metadata" not in driver_name.lower()
                        and "metadata" not in card_type.lower()
                    ):
                        cameras.append(
                            {
                                "id": device_id,
                                "type": "usb",
                                "name": f"{card_type}",
                                "model": card_type,
                                "device": device,
                                "driver": driver_name,
                                "interface": "v4l2",
                            }
                        )
                        print(
                            f"✅ USB Camera: {card_type} at {device}", file=sys.stderr
                        )

            except subprocess.TimeoutExpired:
                print(f"⚠️  Timeout checking {device}", file=sys.stderr)
            except Exception as e:
                print(f"⚠️  Error checking {device}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"❌ Error detecting USB cameras: {e}", file=sys.stderr)

    return cameras


def main():
    """Main detection routine."""
    print("=" * 50, file=sys.stderr)
    print("📹 CAMERA DETECTION - Raspberry Pi", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print("", file=sys.stderr)

    all_cameras = []

    # Detect Pi cameras
    print("1️⃣  Checking for Pi Camera Modules...", file=sys.stderr)
    print("-" * 50, file=sys.stderr)
    pi_cameras = detect_pi_cameras()
    all_cameras.extend(pi_cameras)
    print("", file=sys.stderr)

    # Detect USB cameras
    print("2️⃣  Checking for USB Webcams...", file=sys.stderr)
    print("-" * 50, file=sys.stderr)
    usb_cameras = detect_usb_cameras()
    all_cameras.extend(usb_cameras)
    print("", file=sys.stderr)

    # Summary
    print("=" * 50, file=sys.stderr)
    print("📊 DETECTION SUMMARY", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"Total Cameras Found: {len(all_cameras)}", file=sys.stderr)
    print(f"  - Pi Cameras: {len(pi_cameras)}", file=sys.stderr)
    print(f"  - USB Cameras: {len(usb_cameras)}", file=sys.stderr)
    print("", file=sys.stderr)

    # Output JSON to stdout (for GUI parsing)
    result = {
        "success": True,
        "total": len(all_cameras),
        "cameras": all_cameras,
        "pi_cameras": len(pi_cameras),
        "usb_cameras": len(usb_cameras),
    }

    print(json.dumps(result, indent=2))

    return 0 if all_cameras else 1


if __name__ == "__main__":
    sys.exit(main())
