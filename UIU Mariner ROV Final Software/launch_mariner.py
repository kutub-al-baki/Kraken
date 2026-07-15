#!/usr/bin/env python3
"""
UIU MARINER - Launch Script
Professional ROV Ground Station Control System

Main entry point. Handles environment checks and application startup.
Launches the modern Web Interface (React + FastAPI).
"""

import os
import sys
import logging
import argparse
import subprocess
import shutil
import time
from pathlib import Path

# ── Windows asyncio fix ───────────────────────────────────────────────────────
# The default ProactorEventLoop on Windows throws ConnectionResetError
# (WinError 10054) when any TCP/WebSocket client disconnects abruptly.
# WindowsSelectorEventLoopPolicy avoids this entirely at no cost for this app.
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ─────────────────────────────────────────────────────────────────────────────

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
        "pymavlink": "pymavlink",
        "pygame": "pygame",
        "cv2": "opencv-python",
        "numpy": "numpy",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
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


def launch_web_interface():
    """Launch the Web interface (FastAPI + Vite)"""
    logger.info("Launching Web interface...")
    
    if not shutil.which("node") or not shutil.which("npm"):
        logger.error("Node.js and npm are required for the web frontend.")
        return 1
    
    project_root = Path(__file__).parent.absolute()
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found at {frontend_dir}")
        return 1

    processes = []
    try:
        # 1. Start FastAPI Backend
        logger.info("Starting FastAPI backend server...")
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.web_server:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(project_root),
        )
        processes.append(backend_proc)
        
        # Give backend a moment to start
        time.sleep(2)
        
        # 2. Start Vite Frontend
        logger.info("Starting Vite frontend server...")
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            shell=True, # Required for npm on Windows
        )
        processes.append(frontend_proc)
        
        logger.info("=" * 60)
        logger.info("Ground Station Services Started!")
        logger.info("Backend: http://localhost:8000")
        logger.info("Frontend: http://localhost:5173")
        logger.info("Press Ctrl+C to stop all services")
        logger.info("=" * 60)
        
        # Wait for processes
        while True:
            time.sleep(1)
            for p in processes:
                if p.poll() is not None:
                    logger.warning(f"Process {p.pid} exited with code {p.returncode}")
                    return p.returncode
                    
    except KeyboardInterrupt:
        logger.info("\nShutting down services...")
        return 0
    finally:
        # Terminate all processes
        for p in processes:
            if p.poll() is None:
                logger.debug(f"Terminating process {p.pid}...")
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
        logger.info("All services shut down.")


def main():
    """Main application launcher"""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description="UIU MARINER - ROV Ground Station Control System"
        )
        # Keep web flag for backward compatibility but make it default
        parser.add_argument(
            "--web",
            action="store_true",
            default=True,
            help="Launch modern Web interface (FastAPI + Vite)",
        )
        args = parser.parse_args()

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

        # Launch Web interface
        exit_code = launch_web_interface()

        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
