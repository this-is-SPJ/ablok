#!/bin/bash
# set -o errexit

echo "--- [Ablok] Starting setup script ---"

# --- 1. Install System Dependencies ---
echo "[1/5] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv libnss3-tools wget

# --- 2. Install Microsoft Edge for Linux ---
# reason being its the easiest to set certificates for , if else change the step 4 and step 5
echo "[2/5] Installing Microsoft Edge (required for monitored browsing)..."
# Add Microsoft GPG key and repository if not already present
if ! dpkg -l | grep -q "microsoft-edge-stable"; then
    wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main"
    sudo apt-get update
    sudo apt-get install -y microsoft-edge-stable
else
    echo "Microsoft Edge is already installed. Skipping."
fi

# --- 3. Setup Python Virtual Environment ---
echo "[3/5] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing Python packages from requirements.txt"
pip install -r requirements.txt


#if this comes certutil: function failed: SEC_ERROR_BAD_DATABASE: security library: bad database., look into 4 and 5, mainly path, and for slower sys change the timeouts

echo "[4/5] Generating mitmproxy CA certificate(Intented for Microsoft Edge only )..."

timeout 7 venv/bin/mitmdump > /dev/null 2>&1 & #more timeout for slower systems

CERT_FILE="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
echo "Waiting for certificate file to be generated..."
for i in {1..5}; do
    if [ -f "$CERT_FILE" ]; then
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# --- 5. Trust the mitmproxy Certificate (edge specific)---
echo "[5/5] Installing mitmproxy certificate into the browser trust store..."

if [ -f "$CERT_FILE" ]; then
    
    NSS_DB_DIR="$HOME/.pki/nssdb"

    
    if [ ! -f "$NSS_DB_DIR/cert9.db" ]; then
        echo "NSS database not found. Creating a new one..."
        # The directory must exist before initializing
        mkdir -p "$NSS_DB_DIR"
        # Create a new, empty (passwordless) database
        certutil -N -d "sql:$NSS_DB_DIR" --empty-password
    fi

    certutil -d "sql:$NSS_DB_DIR" -A -t "C,," -n "mitmproxy" -i "$CERT_FILE"
    
    if [ $? -eq 0 ]; then
        echo "Certificate installed successfully."
    else
        echo "ERROR: certutil command failed. Please check for errors above."
        exit 1
    fi
else
    echo "ERROR: mitmproxy certificate not found. Setup failed (check step 4)"
    exit 1
fi

deactivate
echo "--- [Ablok] Setup complete! ---"