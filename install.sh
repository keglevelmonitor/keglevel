#!/bin/bash
# Desktop Installer script for KegLevel Monitor
# This script is designed to be run as root (or with sudo) via:
# curl -sL <RAW_GITHUB_LINK>/install.sh | sudo bash

# --- CONFIGURATION ---
# IMPORTANT: Update this URL to the raw content link for your repository
# Example: https://raw.githubusercontent.com/keglevelmonitor/keglevel/main/install.sh
REPO_URL="https://github.com/keglevelmonitor/keglevel.git" 
PROGRAM_FOLDER="KegLevel_Monitor"
SHORTCUT_FILE="KegLevel.desktop"
EXECUTABLE_NAME="KegLevel_Monitor_202510121125" # Update this if your executable name changes!
TEMP_DIR=$(mktemp -d)

# --- CHECK FOR ROOT PRIVILEGES ---
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with 'sudo'."
    echo "Please run the full install command starting with 'curl' and ending with 'sudo bash'."
    exit 1
fi

# --- IDENTIFY THE TARGET USER ---
# Finds the user who invoked 'sudo' so we can install to their desktop, not root's desktop.
TARGET_USER=$(logname)
if [ -z "$TARGET_USER" ]; then
    echo "ERROR: Could not determine the user who invoked sudo."
    echo "Please ensure you run this script from a graphical user's terminal session."
    rm -rf "$TEMP_DIR"
    exit 1
fi

DESKTOP_PATH="/home/${TARGET_USER}/Desktop"
APP_INSTALL_PATH="${DESKTOP_PATH}/${PROGRAM_FOLDER}"

echo "--- Starting installation of KegLevel Monitor for user: ${TARGET_USER} ---"

# 1. INSTALL GIT DEPENDENCY (Required for cloning the repo)
echo "1. Ensuring git is installed..."
apt update -y 
apt install -y git || { echo "ERROR: Git installation failed."; rm -rf "$TEMP_DIR"; exit 1; }

# 2. DOWNLOAD THE CODE
echo "2. Cloning code from ${REPO_URL} into temporary directory..."
# Use --depth 1 for a faster, shallower clone since we only need the latest files
git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}" || { echo "ERROR: Git clone failed. Check REPO_URL."; rm -rf "$TEMP_DIR"; exit 1; }

# 3. INSTALL PROGRAM FOLDER AND SET PERMISSIONS
echo "3. Installing application folder to Desktop..."

if [ -d "$APP_INSTALL_PATH" ]; then
    echo "    Warning: Removing existing installation folder: ${PROGRAM_FOLDER}"
    rm -rf "$APP_INSTALL_PATH"
fi

if [ ! -d "${TEMP_DIR}/${PROGRAM_FOLDER}" ]; then
    echo "ERROR: Application folder '${PROGRAM_FOLDER}' not found in the repository. Installation aborted."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Move the application folder to the user's Desktop
mv "${TEMP_DIR}/${PROGRAM_FOLDER}" "${DESKTOP_PATH}/"

# Set correct ownership (crucial for the user to be able to access and run files)
echo "    Setting ownership to ${TARGET_USER}..."
chown -R ${TARGET_USER}:${TARGET_USER} "$APP_INSTALL_PATH"

# Ensure the executable inside the folder is executable
EXECUTABLE_PATH="${APP_INSTALL_PATH}/${EXECUTABLE_NAME}"
if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "ERROR: Executable '${EXECUTABLE_NAME}' not found inside the folder. Check your repository contents."
    rm -rf "$TEMP_DIR"
    exit 1
fi
echo "    Setting executable permissions on $EXECUTABLE_PATH..."
chmod +x "$EXECUTABLE_PATH"

# 4. INSTALL DESKTOP SHORTCUT
echo "4. Installing desktop shortcut file..."
SHORTCUT_SOURCE="${TEMP_DIR}/${SHORTCUT_FILE}"
SHORTCUT_DESTINATION="${DESKTOP_PATH}/${SHORTCUT_FILE}"

if [ ! -f "$SHORTCUT_SOURCE" ]; then
    echo "WARNING: Shortcut file '${SHORTCUT_FILE}' not found. Skipping shortcut installation."
else
    # Move the desktop shortcut to the user's Desktop
    mv "$SHORTCUT_SOURCE" "$SHORTCUT_DESTINATION"

    # Set correct ownership
    chown ${TARGET_USER}:${TARGET_USER} "$SHORTCUT_DESTINATION"

    # Make the shortcut executable and "trusted" by the desktop environment
    chmod +x "$SHORTCUT_DESTINATION"
    
    # Use 'su' to run 'gio set' as the target user to mark the shortcut as trusted
    # so the desktop environment allows immediate double-clicking.
    echo "    Setting trusted attribute on shortcut..."
    su -c "gio set \"$SHORTCUT_DESTINATION\" \"metadata::trusted\" true" ${TARGET_USER} 2>/dev/null
fi

# 5. CLEANUP
echo "5. Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "--- Installation Complete! ---"
echo "The KegLevel Monitor application is now installed on your desktop."

exit 0
