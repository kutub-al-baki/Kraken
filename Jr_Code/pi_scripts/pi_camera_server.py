#!/usr/bin/env python3
"""
Camera Server for Raspberry Pi
Streams MJPEG video from Raspberry Pi cameras via Flask HTTP server
Based on working cam.py code with Picamera2
"""

from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import sys
import argparse


class CameraServer:
    """Flask-based MJPEG camera server using Picamera2"""

    def __init__(self, camera_id=0, width=1920, height=1080, port=8080, host="0.0.0.0"):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.port = port
        self.host = host
        self.camera = None
        self.app = Flask(__name__)

        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route("/video_feed")
        def video_feed():
            return Response(
                self._generate_frames(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )

        @self.app.route("/status")
        def status():
            return {
                "camera_id": self.camera_id,
                "resolution": f"{self.width}x{self.height}",
                "status": "running" if self.camera else "stopped",
            }

    def _generate_frames(self):
        """Generate MJPEG frames"""
        while True:
            try:
                frame = self.camera.capture_array()
                ret, buffer = cv2.imencode(".jpg", frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                    )
            except Exception as e:
                print(f"[CAMERA {self.camera_id}] Frame capture error: {e}")
                break

    def start(self):
        """Initialize camera and start Flask server"""
        try:
            print(f"[CAMERA {self.camera_id}] Initializing Picamera2...")
            self.camera = Picamera2(self.camera_id)

            # Configure camera
            config = self.camera.create_preview_configuration(
                main={"format": "XRGB8888", "size": (self.width, self.height)}
            )
            self.camera.configure(config)
            self.camera.start()

            print(f"[CAMERA {self.camera_id}] Camera initialized successfully")
            print(
                f"[CAMERA {self.camera_id}] Starting Flask server on {self.host}:{self.port}"
            )
            print(
                f"[CAMERA {self.camera_id}] Stream URL: http://{self.host}:{self.port}/video_feed"
            )

            # Run Flask server
            self.app.run(host=self.host, port=self.port, threaded=True)

        except Exception as e:
            print(f"[CAMERA {self.camera_id}] Failed to start: {e}")
            sys.exit(1)

    def stop(self):
        """Stop camera"""
        if self.camera:
            self.camera.stop()
            print(f"[CAMERA {self.camera_id}] Camera stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Stream Raspberry Pi camera via Flask MJPEG server"
    )
    parser.add_argument(
        "camera_id", type=int, choices=[0, 1], help="Camera ID (0 or 1)"
    )
    parser.add_argument("port", type=int, help="HTTP port number")
    parser.add_argument(
        "--width", type=int, default=1920, help="Video width (default: 1920)"
    )
    parser.add_argument(
        "--height", type=int, default=1080, help="Video height (default: 1080)"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host address (default: 0.0.0.0)"
    )

    args = parser.parse_args()

    server = CameraServer(
        camera_id=args.camera_id,
        width=args.width,
        height=args.height,
        port=args.port,
        host=args.host,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print(f"\n[CAMERA {args.camera_id}] Interrupted. Stopping...")
        server.stop()
        print(f"[CAMERA {args.camera_id}] Stopped")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python3 pi_camera_server.py <camera_id> <port> [--width WIDTH] [--height HEIGHT] [--host HOST]"
        )
        print("\nExamples:")
        print("  Camera 0 on port 8080:")
        print("    python3 pi_camera_server.py 0 8080")
        print("\n  Camera 1 on port 8081:")
        print("    python3 pi_camera_server.py 1 8081")
        print("\n  Custom resolution:")
        print("    python3 pi_camera_server.py 0 8080 --width 1280 --height 720")
        sys.exit(1)

    main()
