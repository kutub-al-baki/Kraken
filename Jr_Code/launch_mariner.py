#!/usr/bin/env python3
"""
UIU MARINER - Launch Script
Professional ROV Ground Station Control System

Main entry point. Handles environment checks and application startup.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def check_venv() -> bool:
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if not in_venv:
        logger.warning("Not running in virtual environment")
        return False

    logger.info("Virtual environment detected")
    return True


def check_dependencies() -> bool:
    """Check if required packages are installed"""
    required = {
        "PyQt6": "PyQt6",
        "pymavlink": "pymavlink",
        "pygame": "pygame",
        "cv2": "opencv-python",
        "numpy": "numpy",
    }

    missing = []

    for import_name, package_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        return False

    logger.info("All dependencies installed")
    return True


def main():
    """Main application launcher"""
    logger.info("=" * 60)
    logger.info("UIU MARINER - Ground Station Control System")
    logger.info("=" * 60)

    # Check dependencies
    if not check_dependencies():
        logger.error("Please run: pip install -r requirements.txt")
        sys.exit(1)

    # Set up path for imports
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    try:
        logger.info("Initializing application...")
        from src.views.mainWindow import MarinerROVControl
        from PyQt6.QtWidgets import QApplication

        # Create Qt application
        app = QApplication(sys.argv)

        # Create and show main window
        window = MarinerROVControl()
        window.show()

        logger.info("Application started successfully")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
