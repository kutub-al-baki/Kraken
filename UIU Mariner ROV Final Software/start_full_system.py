#!/usr/bin/env python3
"""
UIU MARINER - Full System Startup Script
Automates the process of:
1. Connecting to Raspberry Pi via SSH
2. Starting backend services (Sensors, Mavlink, Cameras)
3. Waiting for services to be ready
4. Launching local web ground station
"""

import sys
import time
import subprocess
import logging
import socket
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SystemLauncher")

# Configuration
PI_HOST = "192.168.1.100"
PI_USER = "pi"
PI_PASS = "1234"
PI_SCRIPT_DIR = "mariner/pi_scripts"
PI_START_SCRIPT = "bash start_all_services.sh"

def check_dependencies():
    """Check if paramiko is installed"""
    try:
        import paramiko
        return True
    except ImportError:
        logger.error("Missing dependency: paramiko")
        logger.info("Please run: pip install paramiko")
        return False

def get_local_ip(target_ip):
    """Detect the local IP used to connect to the Pi"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # target_ip is the Pi's IP. doesn't even have to be reachable for this to work
        s.connect((target_ip, 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def start_pi_services(gs_ip):
    """Connect to Pi and start services with Ground Station IP"""
    import paramiko
    import socket

    MAX_RETRIES = 3
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        logger.info(f"Connecting to Raspberry Pi ({PI_HOST})... (Attempt {retry_count + 1}/{MAX_RETRIES})")
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(PI_HOST, username=PI_USER, password=PI_PASS, timeout=10)
            
            logger.info("✅ Connected to Pi")
            
            # Sync scripts over SFTP so Pi is always up-to-date
            try:
                logger.info("Synchronizing pi_scripts to Raspberry Pi...")
                import stat
                sftp = client.open_sftp()
                try:
                    sftp.mkdir(PI_SCRIPT_DIR)
                except IOError:
                    pass # Already exists
                
                local_dir = Path("pi_scripts")
                # Sync .py and .sh files
                for local_file in list(local_dir.glob("*.py")) + list(local_dir.glob("*.sh")):
                    remote_path = f"{PI_SCRIPT_DIR}/{local_file.name}"
                    if local_file.suffix == '.sh':
                        # Strip Windows CRLF so Pi shebang works (avoids "required file not found")
                        content = local_file.read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                        with sftp.file(remote_path, 'wb') as remote_f:
                            remote_f.write(content)
                        sftp.chmod(remote_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    else:
                        sftp.put(str(local_file), remote_path)

                # Sync crab_detection (YOLO weights + module) for CV mode: crab
                crab_src = Path("src/computer_vision/crab_detection/best.pt")
                crab_local = local_dir / "crab_detection"
                crab_local.mkdir(parents=True, exist_ok=True)
                if crab_src.is_file() and not (crab_local / "best.pt").is_file():
                    import shutil
                    shutil.copy2(crab_src, crab_local / "best.pt")
                try:
                    sftp.mkdir(f"{PI_SCRIPT_DIR}/crab_detection")
                except IOError:
                    pass
                for local_file in crab_local.glob("*"):
                    if local_file.is_file():
                        sftp.put(str(local_file), f"{PI_SCRIPT_DIR}/crab_detection/{local_file.name}")

                sftp.close()
                logger.info("✅ Scripts synchronized")
            except Exception as e:
                logger.warning(f"Failed to sync scripts (assuming they are already deployed): {e}")

            command = f"cd {PI_SCRIPT_DIR} && {PI_START_SCRIPT} {gs_ip}"
            logger.info(f"Running: {command}")
            
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)
            
            # Stream output
            output_buffer = ""
            while True:
                # Check if channel is ready for reading
                if stdout.channel.recv_ready():
                    # Read raw bytes to catch prompts that don't have newlines (like sudo)
                    data = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
                    if not data: break
                    
                    output_buffer += data
                    
                    # Check for sudo password prompt in the buffer
                    if "[sudo] password for" in output_buffer:
                        print(f"    [Pi] {output_buffer.strip()}")
                        stdin.write(PI_PASS + '\n')
                        stdin.flush()
                        logger.info("    [System] Sent sudo password to Pi")
                        output_buffer = "" # Clear buffer after responding
                    
                    # If we have complete lines, print them
                    if '\n' in output_buffer:
                        lines = output_buffer.split('\n')
                        # Keep the last partial line in the buffer
                        output_buffer = lines.pop()
                        for line in lines:
                            print(f"    [Pi] {line.strip()}")
                
                # Check if command finished
                if stdout.channel.exit_status_ready():
                    # Print anything remaining in buffer
                    if output_buffer:
                        print(f"    [Pi] {output_buffer.strip()}")
                    break
                
                time.sleep(0.05)
                
            exit_status = stdout.channel.recv_exit_status()
            
            client.close()
            
            if exit_status == 0:
                logger.info("✅ Pi services started successfully")
                return True
            else:
                logger.error(f"❌ Pi services failed with exit code {exit_status}")
                return False

        except paramiko.AuthenticationException:
            logger.error("❌ Authentication failed. Check password.")
            return False
        except (paramiko.SSHException, socket.error) as e:
            retry_count += 1
            logger.warning(f"⚠️ SSH connection attempt {retry_count} failed: {e}")
            if retry_count < MAX_RETRIES:
                time.sleep(2)
                continue
            else:
                logger.error("❌ Max retries reached. SSH connection failed.")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected Error: {e}")
            return False
    return False

def start_local_ground_station():
    """Launch the local python web interface"""
    logger.info("Starting Local Ground Station...")
    
    cmd = [sys.executable, "launch_mariner.py", "--web"]
    
    try:
        # We run this using subprocess.call to keep it interactive/in foreground
        subprocess.call(cmd)
    except KeyboardInterrupt:
        logger.info("Stopped.")
    except Exception as e:
        logger.error(f"Failed to start ground station: {e}")

def main():
    logger.info("="*50)
    logger.info("    UIU MARINER - AUTOMATED LAUNCH SYSTEM    ")
    logger.info("="*50)

    if not check_dependencies():
        input("Press Enter to exit...")
        sys.exit(1)

    # Detect local IP for the Pi to stream back to
    local_ip = get_local_ip(PI_HOST)
    logger.info(f"Detected Ground Station IP: {local_ip}")

    # Step 1: Start Pi Services
    if start_pi_services(local_ip):
        
        # Optional: Small delay to ensure sockets are bound
        logger.info("Waiting 3 seconds for network services to stabilize...")
        time.sleep(3)
        
        # Step 2: Launch Local Request
        start_local_ground_station()
    else:
        logger.error("Aborting launch due to Pi Error.")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
