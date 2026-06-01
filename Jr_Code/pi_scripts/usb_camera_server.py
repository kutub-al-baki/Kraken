#!/usr/bin/env python3
"""
USB Webcam Streaming Server for Raspberry Pi
Streams from USB webcam (or any v4l2 device) via GStreamer UDP/RTP
"""

import subprocess
import sys
import argparse
import os


def start_usb_camera_stream(
    device="/dev/video0",
    ground_station_ip="192.168.0.100",
    port=5000,
    width=640,
    height=480,
    framerate=30,
    payload=96,
):
    """
    Stream USB webcam using GStreamer

    Args:
        device: Video device path (e.g., /dev/video0)
        ground_station_ip: Destination IP for stream
        port: UDP port for streaming
        width: Video width
        height: Video height
        framerate: Frames per second
        payload: RTP payload type
    """

    print("=" * 60)
    print("📹 USB WEBCAM STREAM - UIU MARINER")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"Destination: {ground_station_ip}:{port}")
    print(f"Resolution: {width}x{height}@{framerate}fps")
    print(f"Payload: {payload}")
    print("=" * 60)
    print()

    # Check if device exists
    if not os.path.exists(device):
        print(f"❌ Error: Device {device} not found!")
        print()
        print("📋 Available video devices:")
        subprocess.run(["ls", "-l", "/dev/video*"])
        sys.exit(1)

    # GStreamer pipeline for USB webcam
    # v4l2src → videoconvert → x264enc → rtph264pay → udpsink
    pipeline = (
        f"v4l2src device={device} ! "
        f"video/x-raw,width={width},height={height},framerate={framerate}/1 ! "
        f"videoconvert ! "
        f"x264enc tune=zerolatency bitrate=2000 speed-preset=superfast ! "
        f"rtph264pay config-interval=1 pt={payload} ! "
        f"udpsink host={ground_station_ip} port={port}"
    )

    print("🚀 Starting GStreamer pipeline...")
    print()
    print(f"Pipeline: {pipeline}")
    print()
    print("💡 Press Ctrl+C to stop")
    print()

    try:
        # Run gst-launch-1.0
        subprocess.run(["gst-launch-1.0", "-v"] + pipeline.split(), check=True)
    except KeyboardInterrupt:
        print()
        print("⏹️  Stream stopped by user")
    except subprocess.CalledProcessError as e:
        print()
        print(f"❌ Error: GStreamer pipeline failed: {e}")
        print()
        print("🔧 Troubleshooting:")
        print(
            "   1. Install GStreamer: sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad"
        )
        print("   2. Check device permissions: ls -l", device)
        print("   3. Test device: v4l2-ctl --device=" + device + " --all")
        print("   4. Try different device: /dev/video0, /dev/video1, etc.")
        sys.exit(1)
    except FileNotFoundError:
        print()
        print("❌ Error: gst-launch-1.0 not found!")
        print()
        print("📦 Install GStreamer:")
        print(
            "   sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad"
        )
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stream USB webcam to Ground Station via UDP/RTP"
    )

    parser.add_argument(
        "device",
        nargs="?",
        default="/dev/video0",
        help="Video device (default: /dev/video0)",
    )

    parser.add_argument("ground_station_ip", help="Ground Station IP address")

    parser.add_argument("port", type=int, help="UDP port for streaming")

    parser.add_argument(
        "--width", type=int, default=640, help="Video width (default: 640)"
    )

    parser.add_argument(
        "--height", type=int, default=480, help="Video height (default: 480)"
    )

    parser.add_argument(
        "--framerate", type=int, default=30, help="Framerate (default: 30)"
    )

    parser.add_argument(
        "--payload", type=int, default=96, help="RTP payload type (default: 96)"
    )

    args = parser.parse_args()

    start_usb_camera_stream(
        device=args.device,
        ground_station_ip=args.ground_station_ip,
        port=args.port,
        width=args.width,
        height=args.height,
        framerate=args.framerate,
        payload=args.payload,
    )
