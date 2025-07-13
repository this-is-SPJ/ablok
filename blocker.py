
#blocker.py
"""This module contains all logic for interacting with the `/etc/hosts` file. It acts as the "enforcement arm," translating a list of domains into actual system-level blocks. It requires elevated (`sudo`) privileges to function.    
"""

import os
import subprocess
import logging
import shutil

HOSTS_PATH = "/etc/hosts"#os specific
BLOCK_TAG = "# managed by ablok" #testing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [blocker.py] - %(message)s')

def get_current_blocks():
    blocked_domains = set() 
    try:
        with open(HOSTS_PATH, 'r') as f:
            for line in f:
                if BLOCK_TAG in line:
                    parts = line.split()
                    if len(parts) > 1:
                        blocked_domains.add(parts[1]) #bc of the str of hosts file
    except FileNotFoundError:
        logging.error(f"Hosts file not found at {HOSTS_PATH}")
    return blocked_domains

def update_hosts_file(domains_to_block: set):
    try:
        with open(HOSTS_PATH, 'r') as f:
            lines = f.readlines()

        # Filter out old ablok entries
        new_lines = [line for line in lines if BLOCK_TAG not in line]
        
        # Add new entries for domains to block
        for domain in domains_to_block:
            new_lines.append(f"127.0.0.1 {domain} {BLOCK_TAG}\n")
            logging.info(f"Blocking domain: {domain} ")

        with open(HOSTS_PATH, 'w') as f: # could have used 'a' but we cant delete old entries that way
            f.writelines(new_lines)
            
        logging.info(f"Hosts file updated. Total domains blocked: {len(domains_to_block)}")
        return True
    
    except PermissionError:
        logging.error("Permission denied to write to hosts file. Run as root with 'sudo'.")
        return False
    except Exception as e:
        logging.error(f"Failed to update hosts file: {e}")
        return False


def flush_dns_cache():
    """
    Flushes the system's DNS cache intelligently. Checks for systemd-resolve first.
    """
    if shutil.which("systemd-resolve"):#works in wsl(works after giving a warning if not found), otherwise systemd-resolve is alr found
        # to enable systemd-resolve in wsl, see "https://g.co/gemini/share/e04a3a65b91e"
        try:
            subprocess.run(["systemd-resolve", "--flush-caches"], check=True, capture_output=True)
            logging.info("DNS cache flushed successfully via systemd-resolve.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.warning(f"Failed to flush DNS cache via systemd-resolve. Error: {e}")
    else:
        logging.warning("`systemd-resolve` not found. Skipping DNS cache flush.")
        logging.warning("New blocks may require a browser restart to take effect.")