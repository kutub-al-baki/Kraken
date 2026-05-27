#!/usr/bin/env python3
"""
Auto-detect Ground Station IP Address
Finds the IP of the connected Ground Station PC via Ethernet
"""

import socket
import subprocess
import sys
import re


def get_default_gateway():
    """Get the default gateway IP (likely the Ground Station)."""
    try:
        # Get default route
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Parse output: "default via 192.168.1.100 dev eth0"
            match = re.search(r"default via ([\d.]+)", result.stdout)
            if match:
                gateway = match.group(1)
                print(f"[NETWORK] Default gateway: {gateway}")
                return gateway
    except Exception as e:
        print(f"[NETWORK] Error getting gateway: {e}")

    return None


def get_ethernet_peer_ip():
    """
    Get IP of device on direct Ethernet connection.
    Looks for IPs on eth0 interface that aren't our own.
    """
    try:
        # Get our own IP on eth0
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "eth0"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Parse: "inet 192.168.21.126/24"
            match = re.search(r"inet ([\d.]+)/(\d+)", result.stdout)
            if match:
                our_ip = match.group(1)
                prefix_len = int(match.group(2))
                print(f"[NETWORK] Our IP: {our_ip}/{prefix_len}")

                # Calculate network range and find other devices
                # For /24 network, just scan the subnet
                network_base = ".".join(our_ip.split(".")[:-1])

                # Try common Ground Station IPs in the same subnet
                for last_octet in range(1, 255):
                    if last_octet == int(our_ip.split(".")[-1]):
                        continue  # Skip our own IP

                    test_ip = f"{network_base}.{last_octet}"

                    # Quick ping test (timeout 0.2s)
                    result = subprocess.run(
                        ["ping", "-c", "1", "-W", "1", test_ip],
                        capture_output=True,
                        timeout=2,
                    )

                    if result.returncode == 0:
                        print(f"[NETWORK] Found responding host: {test_ip}")
                        return test_ip

    except Exception as e:
        print(f"[NETWORK] Error scanning network: {e}")

    return None


def get_arp_cache():
    """Check ARP cache for recently communicated IPs."""
    try:
        result = subprocess.run(
            ["ip", "neigh", "show", "dev", "eth0"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Parse ARP entries
            ips = re.findall(r"([\d.]+)", result.stdout)
            if ips:
                print(f"[NETWORK] ARP cache IPs: {ips}")
                return ips[0]  # Return first IP found

    except Exception as e:
        print(f"[NETWORK] Error reading ARP: {e}")

    return None


def get_ssh_client_ip():
    """If connected via SSH, get the client's IP."""
    try:
        ssh_client = subprocess.run(
            ["echo", "$SSH_CLIENT"], capture_output=True, text=True, shell=True
        )

        if ssh_client.stdout:
            # SSH_CLIENT format: "client_ip client_port server_port"
            parts = ssh_client.stdout.strip().split()
            if parts and len(parts) >= 1:
                client_ip = parts[0]
                if client_ip and client_ip != "":
                    print(f"[NETWORK] SSH client IP: {client_ip}")
                    return client_ip
    except Exception as e:
        print(f"[NETWORK] Error getting SSH client: {e}")

    return None


def auto_detect_ground_station():
    """
    Auto-detect Ground Station IP using multiple methods.

    Priority:
    1. SSH client IP (if connected via SSH)
    2. Default gateway
    3. ARP cache
    4. Ethernet peer scan

    Returns:
        str: IP address of Ground Station, or None if not found
    """
    print("=" * 60)
    print("AUTO-DETECTING GROUND STATION IP")
    print("=" * 60)

    # Method 1: SSH client
    ip = get_ssh_client_ip()
    if ip and ip != "0.0.0.0":
        print(f"✅ Ground Station IP: {ip} (from SSH)")
        return ip

    # Method 2: Default gateway
    ip = get_default_gateway()
    if ip:
        print(f"✅ Ground Station IP: {ip} (from gateway)")
        return ip

    # Method 3: ARP cache
    ip = get_arp_cache()
    if ip:
        print(f"✅ Ground Station IP: {ip} (from ARP)")
        return ip

    # Method 4: Network scan (slower)
    print("[NETWORK] Scanning local network...")
    ip = get_ethernet_peer_ip()
    if ip:
        print(f"✅ Ground Station IP: {ip} (from scan)")
        return ip

    print("❌ Could not auto-detect Ground Station IP")
    return None


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-detect Ground Station IP address"
    )
    parser.add_argument(
        "--fallback",
        type=str,
        default="192.168.0.100",
        help="Fallback IP if auto-detection fails",
    )

    args = parser.parse_args()

    ip = auto_detect_ground_station()

    if not ip:
        print(f"⚠️  Using fallback IP: {args.fallback}")
        ip = args.fallback

    # Output the IP (for script usage)
    print(ip)
    return ip


if __name__ == "__main__":
    main()
