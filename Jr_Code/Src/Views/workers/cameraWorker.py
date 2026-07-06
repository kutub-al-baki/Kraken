"""
Camera Worker Module
Handles dual camera feeds from Raspberry Pi via MJPEG HTTP streams
"""

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap


class CameraWorker(QThread):
    """
    Worker thread for camera streaming.
    Receives MJPEG video stream via HTTP and displays the direct feed.
    """

    frame_ready = pyqtSignal(QPixmap)
    fps_update = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(
        str
    )  # New signal for status updates (Connected/Disconnected)

    def __init__(
        self,
        stream_url,
        camera_id=0,
        flip_horizontal=True,
        flip_vertical=False,
        parent=None,
    ):
        super().__init__(parent)
        self.stream_url = stream_url
        self.running = False
        self.camera_id = camera_id
        self.cap = None
        self.current_frame = None
        self.flip_horizontal = flip_horizontal
        self.flip_vertical = flip_vertical

        self.fps_counter = 0
        self.fps_start_time = 0

        # Object detection support
        self.detector = None
        self.detection_enabled = False

        # Zoom support
        self.zoom_level = 1.0  # 1.0 = no zoom, 2.0 = 2x zoom, etc.
        self.zoom_min = 1.0
        self.zoom_max = 5.0
        self.zoom_step = 0.25

    def run(self):
        """Main camera capture loop with MJPEG stream."""
        import time

        self.running = True
        self.fps_start_time = time.time()
        retry_count = 0
        max_retries = 3

        try:
            while self.running and retry_count < max_retries:
                print(
                    f"[CAM{self.camera_id}] Attempting to open MJPEG stream (attempt {retry_count + 1}/{max_retries})..."
                )
                print(f"[CAM{self.camera_id}] URL: {self.stream_url}")

                # Open MJPEG stream via HTTP
                self.cap = cv2.VideoCapture(self.stream_url)

                if not self.cap.isOpened():
                    retry_count += 1
                    error_msg = f"Camera {self.camera_id}: Failed to open MJPEG stream"
                    self.error_occurred.emit(error_msg)
                    self.status_update.emit("Disconnected")  # Emit status update
                    print(f"[CAM{self.camera_id}] ❌ Failed to open: {self.stream_url}")

                    if retry_count < max_retries:
                        print(f"[CAM{self.camera_id}] Retrying in 2 seconds...")
                        time.sleep(2)
                    else:
                        print(
                            f"[CAM{self.camera_id}] Max retries reached, showing placeholder"
                        )
                        self._show_placeholder()
                        return
                    continue

                print(f"[CAM{self.camera_id}] ✅ MJPEG stream opened successfully")
                self.status_update.emit("Connected")  # Emit connected status
                break

            frame_timeout_count = 0
            max_frame_timeout = 30
            frame_skip_counter = 0
            FRAME_SKIP = 1  # Less aggressive frame skipping for MJPEG

            while self.running:
                ret, frame = self.cap.read()

                if not ret:
                    frame_timeout_count += 1
                    if frame_timeout_count >= max_frame_timeout:
                        print(
                            f"[CAM{self.camera_id}] Too many frame read failures, reconnecting..."
                        )
                        # Try to reconnect
                        if self.cap:
                            self.cap.release()
                        time.sleep(1)
                        self.cap = cv2.VideoCapture(self.stream_url)
                        if not self.cap.isOpened():
                            self._show_placeholder()
                            break
                        frame_timeout_count = 0
                    time.sleep(0.1)
                    continue

                frame_timeout_count = 0

                # Optional frame skipping for performance
                frame_skip_counter += 1
                if frame_skip_counter <= FRAME_SKIP:
                    continue
                frame_skip_counter = 0

                # Ensure consistent resolution (1920x1080 for HD)
                if frame.shape[:2] != (1080, 1920):
                    frame = cv2.resize(
                        frame, (1920, 1080), interpolation=cv2.INTER_LINEAR
                    )

                # Flip camera if needed
                frame = self._apply_flip(frame)

                # Apply zoom if needed
                if self.zoom_level > 1.0:
                    frame = self._apply_zoom(frame)

                # Apply object detection if enabled
                if self.detection_enabled and self.detector:
                    frame = self.detector.process_frame(frame)
                    # Debug output every 100 frames
                    if self.fps_counter % 100 == 0:
                        print(
                            f"[CAM{self.camera_id}] Detection running: {self.detector.mode}"
                        )

                # Add camera overlay
                frame = self._add_camera_overlay(frame)

                # Convert to QPixmap and emit
                pixmap = self._frame_to_pixmap(frame)
                self.frame_ready.emit(pixmap)

                # Store current frame for capture
                self.current_frame = frame.copy()

                # Update FPS
                self.fps_counter += 1
                if time.time() - self.fps_start_time >= 1.0:
                    fps = self.fps_counter / (time.time() - self.fps_start_time)
                    self.fps_update.emit(fps)
                    self.fps_counter = 0
                    self.fps_start_time = time.time()

                time.sleep(0.01)

        except Exception as e:
            error_msg = f"Camera {self.camera_id} error: {str(e)}"
            self.error_occurred.emit(error_msg)
            print(f"[CAM{self.camera_id}] ❌ {error_msg}")
            self._show_placeholder()

        finally:
            if self.cap:
                self.cap.release()
            print(f"[CAM{self.camera_id}] Stream closed")

    def _show_placeholder(self):
        """Show placeholder image when camera is unavailable."""
        placeholder = np.zeros((1080, 1920, 3), dtype=np.uint8)

        text = f"Camera {self.camera_id + 1} Unavailable"
        cv2.putText(
            placeholder,
            text,
            (100, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (100, 100, 100),
            2,
        )

        cv2.putText(
            placeholder,
            "Check network connection",
            (140, 280),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (80, 80, 80),
            1,
        )

        pixmap = self._frame_to_pixmap(placeholder)
        self.frame_ready.emit(pixmap)

    def _apply_flip(self, frame):
        """Apply camera flip transformations."""
        if self.flip_horizontal and self.flip_vertical:
            # Flip both horizontally and vertically (180 degree rotation)
            frame = cv2.flip(frame, -1)
        elif self.flip_horizontal:
            # Flip horizontally (mirror)
            frame = cv2.flip(frame, 1)
        elif self.flip_vertical:
            # Flip vertically
            frame = cv2.flip(frame, 0)
        return frame

    def _add_camera_overlay(self, frame):
        """Add simple camera ID overlay."""
        # Camera ID badge
        cv2.rectangle(frame, (5, 5), (120, 35), (0, 0, 0), -1)
        cv2.rectangle(frame, (5, 5), (120, 35), (255, 136, 0), 2)
        cv2.putText(
            frame,
            f"CAM {self.camera_id + 1}",
            (15, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 136, 0),
            2,
        )
        return frame

    def _frame_to_pixmap(self, frame):
        """Convert OpenCV frame to QPixmap."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w

        q_image = QImage(
            rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )

        return QPixmap.fromImage(q_image)

    def get_frame(self):
        """Get current frame for capture"""
        if self.current_frame is not None:
            return self.current_frame.copy()
        return None

    def set_flip(self, horizontal=None, vertical=None):
        """
        Set camera flip settings
        Args:
            horizontal: True to flip horizontally, False to disable, None to keep current
            vertical: True to flip vertically, False to disable, None to keep current
        """
        if horizontal is not None:
            self.flip_horizontal = horizontal
        if vertical is not None:
            self.flip_vertical = vertical

    def set_detector(self, detector):
        """Set object detector for this camera"""
        self.detector = detector
        print(f"[CAM{self.camera_id}] Detector attached")

    def enable_detection(self):
        """Enable object detection"""
        if self.detector:
            self.detection_enabled = True
            self.detector.enable()
            print(f"[CAM{self.camera_id}] Detection enabled")

    def disable_detection(self):
        """Disable object detection"""
        if self.detector:
            self.detection_enabled = False
            self.detector.disable()
            print(f"[CAM{self.camera_id}] Detection disabled")

    def zoom_in(self):
        """Increase zoom level"""
        if self.zoom_level < self.zoom_max:
            self.zoom_level = min(self.zoom_level + self.zoom_step, self.zoom_max)
            print(f"[CAM{self.camera_id}] Zoom: {self.zoom_level:.2f}x")
            return self.zoom_level
        return self.zoom_level

    def zoom_out(self):
        """Decrease zoom level"""
        if self.zoom_level > self.zoom_min:
            self.zoom_level = max(self.zoom_level - self.zoom_step, self.zoom_min)
            print(f"[CAM{self.camera_id}] Zoom: {self.zoom_level:.2f}x")
            return self.zoom_level
        return self.zoom_level

    def reset_zoom(self):
        """Reset zoom to default (1.0x)"""
        self.zoom_level = 1.0
        print(f"[CAM{self.camera_id}] Zoom reset to 1.0x")
        return self.zoom_level

    def _apply_zoom(self, frame):
        """Apply digital zoom to frame by cropping and resizing"""
        if self.zoom_level <= 1.0:
            return frame

        height, width = frame.shape[:2]

        # Calculate crop dimensions (smaller region = more zoom)
        crop_width = int(width / self.zoom_level)
        crop_height = int(height / self.zoom_level)

        # Calculate crop center (center of frame)
        start_x = (width - crop_width) // 2
        start_y = (height - crop_height) // 2

        # Crop the center region
        cropped = frame[start_y : start_y + crop_height, start_x : start_x + crop_width]

        # Resize back to original dimensions
        zoomed = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)

        return zoomed

    def stop(self):
        """Stop the camera thread."""
        self.running = False
        self.wait()


class DualCameraManager:
    """
    Manages two camera workers for dual camera setup with MJPEG streams.
    """

    def __init__(
        self, stream_url0, stream_url1, flip_horizontal=True, flip_vertical=False
    ):
        self.camera0 = CameraWorker(
            stream_url0,
            camera_id=0,
            flip_horizontal=flip_horizontal,
            flip_vertical=flip_vertical,
        )
        self.camera1 = CameraWorker(
            stream_url1,
            camera_id=1,
            flip_horizontal=flip_horizontal,
            flip_vertical=flip_vertical,
        )

        self.cameras = [self.camera0, self.camera1]

    def start_all(self):
        """Start both camera streams."""
        for cam in self.cameras:
            cam.start()

    def stop_all(self):
        """Stop both camera streams."""
        for cam in self.cameras:
            cam.stop()

    def set_flip_all(self, horizontal=None, vertical=None):
        """Set flip settings for all cameras"""
        for cam in self.cameras:
            cam.set_flip(horizontal, vertical)

    def set_flip_camera(self, camera_id, horizontal=None, vertical=None):
        """Set flip settings for specific camera"""
        if 0 <= camera_id < len(self.cameras):
            self.cameras[camera_id].set_flip(horizontal, vertical)

    def zoom_in_camera(self, camera_id):
        """Zoom in on specific camera"""
        if 0 <= camera_id < len(self.cameras):
            return self.cameras[camera_id].zoom_in()
        return 1.0

    def zoom_out_camera(self, camera_id):
        """Zoom out on specific camera"""
        if 0 <= camera_id < len(self.cameras):
            return self.cameras[camera_id].zoom_out()
        return 1.0

    def reset_zoom_camera(self, camera_id):
        """Reset zoom on specific camera"""
        if 0 <= camera_id < len(self.cameras):
            return self.cameras[camera_id].reset_zoom()
        return 1.0

    def zoom_in_all(self):
        """Zoom in on all cameras"""
        for cam in self.cameras:
            cam.zoom_in()

    def zoom_out_all(self):
        """Zoom out on all cameras"""
        for cam in self.cameras:
            cam.zoom_out()

    def reset_zoom_all(self):
        """Reset zoom on all cameras"""
        for cam in self.cameras:
            cam.reset_zoom()
