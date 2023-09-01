#!/bin/bash
set -euo pipefail

####################################################################################
# Automates BORIS startup on macOS                                                 #
#                                                                                  #
# 1. Install Docker Desktop (https://docs.docker.com/desktop/install/mac-install/) #
# 2. Install XQuartx (https://www.xquartz.org) *and* reboot                        #
# 3. Save this script using "Raw" button                                           #
# 4. In Terminal app type "chmod +x start_macOS.command"                           #
# 5. Double-click the script to start BORIS                                        #
#                                                                                  #
####################################################################################

# You can but shouldn't need to modify these locations
XAUTH=/tmp/.docker.xauth
BORIS_HOME="${HOME}/Boris"


###
### Do NOT modify anything below this line
###
ret=0
docker info >/dev/null 2>&1 || ret=$?
if [[ $ret -eq 0 ]]; then
    echo "[+] Docker Engine is running"
else
    echo "[-] Docker Engine is not running or is not responding!"
    exit 1
fi

# We need to check for that specific binary; there are mutliple "xquartz" hits during startup
# If checked for just "xquartz" it will match before the TCP is fully initialized and fail later
isXQuartzRunning () {
    local xqProcesses
    xqProcesses=$(ps aux | grep -v grep | grep -c -i '/opt/X11/bin/Xquartz')
    if [[ $xqProcesses -gt 0 ]]; then
        return 0
    fi

    return 1
}

if ! isXQuartzRunning; then
    echo "[*] XQuartz not running, starting..."
    echo "[*] You CAN close the new WHITE terminal window once it opens"

    # There's no way to await until XQ *starts* with "open"
    # We can however wait for the main XQ process to start
    open -j -g /Applications/Utilities/XQuartz.app   
    xqStarted=0
    echo -n "[*] Awaiting XQuartz..."
    for i in {0..60}; do
        if isXQuartzRunning; then
            echo " [OK]"
            xqStarted=1
            break
        fi

        echo -n "."
        sleep 1
    done
    if [[ $xqStarted -ne 1 ]]; then
      echo " [TIMEOUT]"
      echo "[!] XQuartz failed to start after 60s. Make sure it is installed properly and you restarted your computer after installation!"
      exit 1
    fi

    # Sometimes the TCP socket isn't active right away - there's no easy way to wait for that
    sleep 2
fi

# XQuartz (for security reasons) does NOT listen on TCP by default
# It needs to be enabled manually by the user in XQ preferences; sometimes it resets after update
netstat -an | grep LISTEN | grep '*.6000' >/dev/null 2>&1 || ret=$?
if [[ $ret -eq 0 ]]; then
    echo "[+] XQuartz TCP is enabled"
else
    echo '[-] XQuartz is running but it is NOT configured properly! You need to enable "Allow connections from network clients" in XQuartz preferences'
    exit 1
fi

# On first run the home may not exist
mkdir -p "${BORIS_HOME}"
echo "This folder contains hidden files. Deleting it will remove all settings and other BORIS data!" > "${BORIS_HOME}/_DO_NOT_DELETE_THIS_FOLDER_.txt"

# The XAUTHORITY file content will change for security reasons every time the XQuartz is restarte
# We're using "magic cookie" instead of host auth as internal container IP is ephemeral and "random"
# Using "host" network is discouraged for security reasons
echo "[*] Preparing X11 authorization..."
rm $XAUTH >/dev/null 2>&1 || true
touch "${XAUTH}"
xauth nlist "$(hostname):0" | sed -e 's/^..../ffff/' | xauth -f $XAUTH nmerge -

echo
echo
echo "==========================================================="
echo "[*] Starting BORIS..."
echo "[*] DO NOT CLOSE THIS TERMINAL WINDOW BEFORE CLOSING BORIS!"
echo "==========================================================="
echo 
echo
docker run \
  -e "DISPLAY=host.docker.internal:0" \
  -v "$XAUTH:$XAUTH" \
  -e "XAUTHORITY=$XAUTH" \
  -v "${BORIS_HOME}:/root:rw" \
 olivierfriard/boris

echo "[*] Cleaning-up..."
rm $XAUTH

echo
echo
echo "[+] YOU CAN CLOSE THIS WINDOW NOW"
