
#main.py
"""The central script that launches, coordinates, and shuts down all other components. It runs the main application loop and handles the overall lifecycle. 
"""


import os
import sys
import time
import subprocess
import logging
#py files
import blocker
import rules 

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [main.py] - %(message)s')

def main():
    # --- 1. Privilege Check ---
    if os.geteuid() != 0:
        logging.error("This script requires root privileges to modify the hosts file.")
        sys.exit("Please run with 'sudo'.")

    # --- 2. Load Configuration ---
    config = rules.load_config()
    evaluation_interval = config.get('evaluation_interval_seconds', 60)
    
    # Define paths using the venv
    venv_python = "venv/bin/python3"
    mitmdump_path = "venv/bin/mitmdump"

    proxy_proc = None
    browser_proc = None

    try:
        # --- 3. Launch Subprocesses ---
        logging.info("Starting mitmproxy listener...")
        proxy_proc = subprocess.Popen([
            mitmdump_path,
            "-s", "tracker.py",
            "-p", "8080",
            "--set", "block_global=false" # Prevents mitmproxy from blocking connections itself
        ])

        logging.info("Launching monitored Microsoft Edge browser...")
        # Give the proxy a moment to start up
        time.sleep(2) 
        browser_proc = subprocess.Popen([
            "microsoft-edge-stable",
            "--no-sandbox", #Running as root without --no-sandbox is not supported, error
            "--proxy-server=http://127.0.0.1:8080",
            "--no-first-run" 
        ])

        # --- 4. Main Monitoring Loop ---
        logging.info("Ablok is active. Close the Edge window or press Ctrl+C to stop.")
        while browser_proc.poll() is None:
            # Check rules and apply blocks
            current_blocks = blocker.get_current_blocks()
            desired_blocks = rules.get_domains_to_block(config)
            
            if current_blocks != desired_blocks:
                logging.info("Change in blocklist detected. Updating hosts file...")
                if blocker.update_hosts_file(desired_blocks):
                    blocker.flush_dns_cache()
            
            time.sleep(evaluation_interval)
            
    except KeyboardInterrupt:
        logging.info("Ctrl+C detected. Shutting down...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        # --- 5. Cleanup ---
        logging.info("Cleaning up processes...")
        if browser_proc and browser_proc.poll() is None:
            browser_proc.terminate()
            browser_proc.wait(timeout=5)
        if proxy_proc and proxy_proc.poll() is None:
            proxy_proc.terminate()
            proxy_proc.wait(timeout=5)
        
        # Clean the hosts file on exit
        logging.info("Removing all blocks from hosts file.")
        blocker.update_hosts_file(set())
        blocker.flush_dns_cache()
        
        logging.info("Ablok has been shut down.")


if __name__ == "__main__":
    main()