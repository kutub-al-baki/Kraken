"""
Simple Camera Integration with Object Detection
Directly integrates object detection into camera worker
"""

import os
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


class CameraDetector(QObject):
    """
    Simple detector that processes camera frames
    Shows detection results directly in the UI
    """

    detection_stats = pyqtSignal(dict)  # Emits detection statistics

    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.enabled = False
        self.mode = "color"  # color, motion, edge, face

        # Color detection (default: blue)
        self.color_lower = np.array([100, 150, 0])  # Blue in HSV
        self.color_upper = np.array([140, 255, 255])

        # Motion detection
        self.prev_frame = None
        self.motion_threshold = 30

        # Face/Eye/Smile detection - Load Haar Cascades
        try:
            import os

            self.cascade_dir = os.path.dirname(__file__)
            self.cascades = {}

            # Define cascade models to load
            # Add more models here as needed!
            self.cascade_models = {
                "face": "haarcascade_frontalface_default.xml",
                "eye": "haarcascade_eye.xml",
                "smile": "haarcascade_smile.xml",
                # Add more cascades here:
                # 'cat_face': 'haarcascade_frontalcatface.xml',
                # 'fullbody': 'haarcascade_fullbody.xml',
                # 'profile_face': 'haarcascade_profileface.xml',
            }

            # Load all cascades
            self._load_cascades()

        except Exception as e:
            print(f"[CV] Error initializing Haar Cascades: {e}")
            self.cascades = {}

        print(f"[CV] Camera {camera_id} detector initialized")

    def _load_cascades(self):
        """Load all configured cascade models"""
        loaded_count = 0

        for name, filename in self.cascade_models.items():
            if self.add_cascade(name, filename):
                loaded_count += 1

        if loaded_count > 0:
            print(
                f"[CV] Loaded {loaded_count}/{len(self.cascade_models)} cascade models"
            )
        else:
            print("[CV] Warning: No cascade models loaded")

    def add_cascade(self, name, filename):
        """
        Add a new Haar Cascade model for detection

        Args:
            name: Identifier for the cascade (e.g., 'face', 'eye', 'cat')
            filename: XML filename in cascade directory

        Returns:
            True if loaded successfully, False otherwise

        Example:
            detector.add_cascade('cat_face', 'haarcascade_frontalcatface.xml')
        """
        filepath = os.path.join(self.cascade_dir, filename)

        if not os.path.exists(filepath):
            print(f"[CV] ⚠️  {filename} not found, skipping {name} detection")
            return False

        cascade = cv2.CascadeClassifier(filepath)

        if cascade.empty():
            print(f"[CV] ❌ Failed to load {filename}")
            return False

        self.cascades[name] = cascade
        print(f"[CV] ✅ {name} cascade loaded from {filename}")
        return True

    def process_frame(self, frame):
        """
        Process frame with detection
        Returns annotated frame
        """
        if frame is None or not self.enabled:
            return frame

        try:
            if self.mode == "color":
                return self._detect_color(frame)
            elif self.mode == "motion":
                return self._detect_motion(frame)
            elif self.mode == "edge":
                return self._detect_edges(frame)
            elif self.mode == "face":
                return self._detect_face(frame)
            else:
                return frame
        except Exception as e:
            print(f"[CV] Error: {e}")
            return frame

    def _detect_color(self, frame):
        """Detect colored objects"""
        output = frame.copy()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.color_lower, self.color_upper)

        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:
                x, y, w, h = cv2.boundingRect(contour)
                # Draw thick green rectangle
                cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 3)
                # Add label with background
                label = f"Object {count + 1} ({int(area)}px)"
                cv2.putText(
                    output,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                count += 1

        # Add detection status overlay at top
        status = f"COLOR DETECTION: {count} objects"
        cv2.putText(
            output, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )

        self.detection_stats.emit({"mode": "color", "count": count})
        return output

    def _detect_motion(self, frame):
        """Detect motion"""
        output = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_frame is None:
            self.prev_frame = gray
            return output

        frame_diff = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(
            frame_diff, self.motion_threshold, 255, cv2.THRESH_BINARY
        )[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        count = 0
        for contour in contours:
            if cv2.contourArea(contour) > 1000:
                x, y, w, h = cv2.boundingRect(contour)
                # Draw yellow rectangle for motion
                cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 255), 3)
                label = f"Motion {count + 1}"
                cv2.putText(
                    output,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )
                count += 1

        self.prev_frame = gray

        cv2.putText(
            output,
            f"MOTION DETECTION: {count} areas",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )

        self.detection_stats.emit({"mode": "motion", "count": count})
        return output

    def _detect_edges(self, frame):
        """Edge detection"""
        output = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Make edges more visible by coloring them cyan
        edges_colored = np.zeros_like(frame)
        edges_colored[:, :, 0] = edges  # Blue channel
        edges_colored[:, :, 1] = edges  # Green channel
        output = cv2.addWeighted(output, 0.6, edges_colored, 0.4, 0)

        edge_pixels = np.count_nonzero(edges)
        cv2.putText(
            output,
            f"EDGE DETECTION: {edge_pixels} edge pixels",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )

        self.detection_stats.emit({"mode": "edge", "count": edge_pixels})
        return output

    def _detect_face(self, frame):
        """Detect faces, eyes, and smiles"""
        output = frame.copy()

        if "face" not in self.cascades:
            cv2.putText(
                output,
                "FACE DETECTION: Face cascade not loaded",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )
            return output

        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = self.cascades["face"].detectMultiScale(gray, 1.1, 5)

        face_count = 0
        eye_count = 0
        smile_count = 0

        for x, y, w, h in faces:
            face_count += 1

            # Draw green rectangle around face
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(
                output,
                f"Face {face_count}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            # Region of interest for eyes and smile detection
            roi_gray = gray[y : y + h, x : x + w]
            roi_color = output[y : y + h, x : x + w]

            # Detect eyes in face region
            if "eye" in self.cascades:
                eyes = self.cascades["eye"].detectMultiScale(roi_gray, 1.1, 10)
                if len(eyes) > 0:
                    eye_count += len(eyes)
                    cv2.putText(
                        output,
                        "Eyes Detected",
                        (x, y - 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 255),
                        2,
                    )
                    # Draw circles around eyes
                    for ex, ey, ew, eh in eyes:
                        cv2.circle(
                            roi_color,
                            (ex + ew // 2, ey + eh // 2),
                            ew // 2,
                            (255, 0, 255),
                            2,
                        )

            # Detect smile in face region
            if "smile" in self.cascades:
                smiles = self.cascades["smile"].detectMultiScale(roi_gray, 1.7, 10)
                if len(smiles) > 0:
                    smile_count += 1
                    cv2.putText(
                        output,
                        "Smiling :)",
                        (x, y - 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

        # Add detection status overlay
        status = f"FACE DETECTION: {face_count} faces"
        if eye_count > 0:
            status += f" | {eye_count} eyes"
        if smile_count > 0:
            status += f" | {smile_count} smiling"

        cv2.putText(
            output, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )

        self.detection_stats.emit(
            {
                "mode": "face",
                "faces": face_count,
                "eyes": eye_count,
                "smiles": smile_count,
            }
        )
        return output

    def set_mode(self, mode):
        """Set detection mode: color, motion, edge, face"""
        if mode in ["color", "motion", "edge", "face"]:
            self.mode = mode
            self.prev_frame = None
            print(f"[CV] Mode: {mode}")

    def set_color_target(self, color_name):
        """Set target color: red, green, blue, yellow"""
        colors = {
            "red": ([0, 120, 70], [10, 255, 255]),
            "green": ([40, 40, 40], [80, 255, 255]),
            "blue": ([100, 150, 0], [140, 255, 255]),
            "yellow": ([20, 100, 100], [30, 255, 255]),
        }
        if color_name in colors:
            self.color_lower = np.array(colors[color_name][0])
            self.color_upper = np.array(colors[color_name][1])
            print(f"[CV] Target color: {color_name}")

    def enable(self):
        """Enable detection"""
        self.enabled = True
        print("[CV] Detection enabled")

    def disable(self):
        """Disable detection"""
        self.enabled = False
        print("[CV] Detection disabled")
