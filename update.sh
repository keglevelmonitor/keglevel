#!/bin/bash
# Dedicated update script for KegLevel Monitor (Preserves old versions)

# --- CONFIGURATION ---
REPO_URL="https://github.com/keglevelmonitor/keglevel.git" # IMPORTANT: Your full Git clone URL
PROGRAM_FOLDER="KegLevel_Monitor"
SHORTCUT_FILE="KegLevel.desktop"
TEMP_DIR=$(mktemp -d)

# --- EXECUTION ENVIRONMENT SETUP ---
# Determine the target user (finds the user who invoked the script)
TARGET_USER=$(logname)
if [ -z "$TARGET_USER" ]; then
    echo "ERROR: Could not determine the user. Run this script from your user terminal."
    exit 1
fi

DESKTOP_PATH="/home/${TARGET_USER}/Desktop"
APP_INSTALL_PATH="${DESKTOP_PATH}/${PROGRAM_FOLDER}"
SHORTCUT_PATH="${DESKTOP_PATH}/${SHORTCUT_FILE}"

echo "--- Starting version update for KegLevel Monitor ---"

# 1. VALIDATION CHECKS
if [ ! -d "$APP_INSTALL_PATH" ]; then
    echo "ERROR: Installation directory not found at ${APP_INSTALL_PATH}"
    echo "Please run the full installation command first."
    rm -rf "$TEMP_DIR"
    exit 1
fi

if [ ! -f "$SHORTCUT_PATH" ]; then
    echo "ERROR: Desktop shortcut file not found at ${SHORTCUT_PATH}"
    echo "Please ensure the initial installation was successful."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 2. CLONE REPO TO DISCOVER NEW FILE
echo "2. Cloning latest code to temporary directory..."
git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}" || { echo "ERROR: Git clone failed. Check REPO_URL."; rm -rf "$TEMP_DIR"; exit 1; }

# Find the unique executable file name in the cloned repo folder.
# We look for ANY file starting with the program name pattern in the repo's folder.
NEW_EXE_NAME=$(find "${TEMP_DIR}/${PROGRAM_FOLDER}" -type f -name 'KegLevel_Monitor_*' -exec basename {} \;)

if [ -z "$NEW_EXE_NAME" ]; then
    echo "ERROR: Could not find the new executable (KegLevel_Monitor_*) in the repository."
    rm -rf "$TEMP_DIR"
    exit 1
fi

NEW_EXE_PATH="${APP_INSTALL_PATH}/${NEW_EXE_NAME}"

# 3. COPY NEW EXECUTABLE (PRESERVING THE OLD VERSION)
# This meets the requirement of not deleting or overwriting the old executable.
echo "3. Copying new executable: ${NEW_EXE_NAME}"
cp "${TEMP_DIR}/${PROGRAM_FOLDER}/${NEW_EXE_NAME}" "$NEW_EXE_PATH"

# 4. SET PERMISSIONS
echo "4. Setting executable permissions on the new file."
chmod +x "$NEW_EXE_PATH"

# NOTE: Step 5 (Updating the desktop shortcut) has been removed as per user request.
# The user's existing desktop shortcut is assumed to handle the launching of the latest file dynamically.

# 5. CLEANUP
echo "5. Cleaning up temporary files."
rm -rf "$TEMP_DIR"

echo "--- Update Complete! ---"
echo "New executable '${NEW_EXE_NAME}' is installed. The desktop shortcut was not modified."

exit 0
