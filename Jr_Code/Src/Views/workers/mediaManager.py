"""
Media Manager Module
Handles camera capture and video recording functionality
"""

import cv2
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal


class MediaManager(QObject):
    """
    Manages image capture and video recording from camera frames
    """

    recording_status = pyqtSignal(bool)
    capture_complete = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_path = Path(__file__).parent.parent.parent.parent
        self.media_dir = self.root_path / "media"
        self.images_dir = self.media_dir / "images"
        self.videos_dir = self.media_dir / "videos"

        self.recording = False
        self.video_writer = None
        self.current_video_path = None

        self._setup_directories()

    def _setup_directories(self):
        """Create media directory structure if it doesn't exist"""
        try:
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.videos_dir.mkdir(parents=True, exist_ok=True)
            print(f"[MEDIA] Media directories initialized: {self.media_dir}")
        except Exception as e:
            print(f"[MEDIA] ERROR: Failed to create directories: {e}")

    def capture_image(self, frame, camera_id=0):
        """
        Capture and save a single frame as image
        Args:
            frame: OpenCV frame (BGR format)
            camera_id: Camera identifier (0 or 1)
        Returns:
            Path to saved image or None if failed
        """
        if frame is None:
            print("[MEDIA] ERROR: Invalid frame for capture")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"cam{camera_id}_{timestamp}.png"
            filepath = self.images_dir / filename

            cv2.imwrite(str(filepath), frame)
            print(f"[MEDIA] Image captured: {filename}")
            self.capture_complete.emit(str(filepath))
            return str(filepath)

        except Exception as e:
            print(f"[MEDIA] ERROR: Failed to capture image: {e}")
            return None

    def start_recording(self, frame_width=1920, frame_height=1080, fps=30, camera_id=0):
        """
        Start video recording
        Args:
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            fps: Frames per second
            camera_id: Camera identifier
        Returns:
            True if recording started, False otherwise
        """
        if self.recording:
            print("[MEDIA] Recording already in progress")
            return False

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cam{camera_id}_{timestamp}.mp4"
            self.current_video_path = self.videos_dir / filename

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(
                str(self.current_video_path), fourcc, fps, (frame_width, frame_height)
            )

            if not self.video_writer.isOpened():
                print("[MEDIA] ERROR: Failed to open video writer")
                self.video_writer = None
                return False

            self.recording = True
            self.recording_status.emit(True)
            print(f"[MEDIA] Recording started: {filename}")
            return True

        except Exception as e:
            print(f"[MEDIA] ERROR: Failed to start recording: {e}")
            self.recording = False
            self.recording_status.emit(False)
            return False

    def write_frame(self, frame):
        """
        Write frame to video file during recording
        Args:
            frame: OpenCV frame (BGR format)
        Returns:
            True if frame written successfully
        """
        if not self.recording or self.video_writer is None:
            return False

        try:
            self.video_writer.write(frame)
            return True
        except Exception as e:
            print(f"[MEDIA] ERROR: Failed to write frame: {e}")
            return False

    def stop_recording(self):
        """
        Stop video recording and save file
        Returns:
            Path to saved video or None if failed
        """
        if not self.recording or self.video_writer is None:
            print("[MEDIA] No recording in progress")
            return None

        try:
            self.video_writer.release()
            self.video_writer = None
            self.recording = False
            self.recording_status.emit(False)

            if self.current_video_path and self.current_video_path.exists():
                file_size = self.current_video_path.stat().st_size / (1024 * 1024)
                print(
                    f"[MEDIA] Recording stopped: {self.current_video_path.name} ({file_size:.2f} MB)"
                )
                self.capture_complete.emit(str(self.current_video_path))
                path = str(self.current_video_path)
                self.current_video_path = None
                return path
            else:
                print("[MEDIA] ERROR: Video file not found after recording")
                return None

        except Exception as e:
            print(f"[MEDIA] ERROR: Failed to stop recording: {e}")
            self.recording = False
            self.recording_status.emit(False)
            return None

    def is_recording(self):
        """Check if currently recording"""
        return self.recording

    def get_media_path(self):
        """Get the root media directory path"""
        return str(self.media_dir)

    def cleanup(self):
        """Cleanup on shutdown"""
        if self.recording:
            self.stop_recording()
