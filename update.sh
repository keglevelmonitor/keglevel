#!/bin/bash
# Dedicated update script for KegLevel Monitor
# This script is designed to be run as the user (WITHOUT sudo) via:
# curl -sL <RAW_GITHUB_LINK>/update.sh | bash

# --- CONFIGURATION (Must match install.sh repo source) ---
REPO_URL="https://github.com/keglevelmonitor/keglevel.git" 
PROGRAM_FOLDER="KegLevel_Monitor"
SHORTCUT_FILE="KegLevel.desktop"
TEMP_DIR=$(mktemp -d)

# Files that are code components/support scripts
SUPPORT_FILES="notification_service.py sensor_logic.py settings_manager.py temperature_logic.py"

# Files that should be present in the repository and MUST be copied
CORE_ASSETS="bjcp_2015_library.json bjcp_2021_library.json beer-keg.png"

# Files that are RETAINED by the user and *may not* exist in the repo, but if they do, should be copied/overwritten
USER_SETTINGS="config.json settings.json"


# --- EXECUTION ENVIRONMENT SETUP ---
# NOTE: This script does NOT require sudo, so TARGET_USER is usually the running user.
TARGET_USER=$(logname)
if [ -z "$TARGET_USER" ]; then
    echo "ERROR: Could not determine the user. Run this script from your user terminal."
    rm -rf "$TEMP_DIR"
    exit 1
fi

DESKTOP_PATH="/home/${TARGET_USER}/Desktop"
APP_INSTALL_PATH="${DESKTOP_PATH}/${PROGRAM_FOLDER}"


echo "--- Starting version update for KegLevel Monitor for user: ${TARGET_USER} ---"


# --- FUNCTIONS ---

# Function to handle the version comparison logic
local_version_check() {
    local REPO_EXECUTABLE_NAME="$1"
    
    # Extract the timestamp (YYYYMMDDHHMM) from the repository executable name
    # We use grep -oE '[0-9]{12}' to robustly extract the 12-digit datecode
    REPO_TIMESTAMP=$(echo "$REPO_EXECUTABLE_NAME" | grep -oE '[0-9]{12}')

    # Find the newest local executable timestamp
    LATEST_LOCAL_EXE=$(find "$APP_INSTALL_PATH" -maxdepth 1 -type f -name "KegLevel_Monitor_*" | sort -r | head -n 1)
    
    if [ -z "$LATEST_LOCAL_EXE" ]; then
        echo "WARNING: Could not find any local executable to compare. Proceeding with update."
        return 0
    fi
    
    # Extract the timestamp from the latest local executable name
    LATEST_LOCAL_TIMESTAMP=$(basename "$LATEST_LOCAL_EXE" | grep -oE '[0-9]{12}')

    echo "    Local Version Timestamp: $LATEST_LOCAL_TIMESTAMP"
    echo "    Repo Version Timestamp:  $REPO_TIMESTAMP"
    
    # Compare timestamps numerically
    if [ -n "$REPO_TIMESTAMP" ] && [ -n "$LATEST_LOCAL_TIMESTAMP" ] && [ "$LATEST_LOCAL_TIMESTAMP" -ge "$REPO_TIMESTAMP" ]; then
        
        if [ "$LATEST_LOCAL_TIMESTAMP" -eq "$REPO_TIMESTAMP" ]; then
            VERSION_MESSAGE="Local installation is current (Version $LATEST_LOCAL_TIMESTAMP)."
        else
            VERSION_MESSAGE="Local installation is newer than the repository version (Local $LATEST_LOCAL_TIMESTAMP vs Repo $REPO_TIMESTAMP)."
        fi
        
        echo ""
        echo "========================================================================="
        echo "Update not required: $VERSION_MESSAGE"
        echo "Press any key to exit the update."
        echo "========================================================================="
        
        # Read a single character from the terminal without waiting for Enter
        read -n 1 -s -r < /dev/tty # Force read from TTY
        echo "" # Add newline after keypress for clean exit
        
        return 1 # Signal that the update process should stop
    fi
    
    # If we reach here, the local version is older, so return 0 to proceed with the update
    return 0
}


# Function to handle the update process (Backup, then Call Core Update)
update_action_revised() {
    # We must install git if it is not present because we need to clone the repo.
    if ! command -v git &> /dev/null; then
        echo "ERROR: Git is not installed. Please run the full install script or install git manually."
        return 1
    fi

    echo "1. Cloning code from ${REPO_URL} into temporary directory..."
    git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}" || { echo "ERROR: Git clone failed. Check REPO_URL."; rm -rf "$TEMP_DIR"; return 1; }

    # --- DYNAMIC EXECUTABLE DISCOVERY (Repo) ---
    EXECUTABLE_NAME_FOUND=$(find "${TEMP_DIR}/${PROGRAM_FOLDER}" -maxdepth 1 -type f -name "KegLevel_Monitor_*" -print -quit)
    if [ -z "$EXECUTABLE_NAME_FOUND" ]; then
        echo "ERROR: No executable file matching 'KegLevel_Monitor_*' found in the repository. Aborting."
        rm -rf "$TEMP_DIR"
        return 1
    fi
    REPO_EXECUTABLE_NAME=$(basename "$EXECUTABLE_NAME_FOUND")
    
    # --- VERSION CHECK ---
    local_version_check "$REPO_EXECUTABLE_NAME"
    if [ $? -eq 1 ]; then
        # Version check determined no update is needed (exit was handled in the function)
        rm -rf "$TEMP_DIR"
        exit 0
    fi
    
    # --- PROCEED WITH UPDATE (Local is OLDER than Repo) ---

    echo ""
    echo "Creating backup of project folder and leaving all settings files intact"
    
    TIMESTAMP=$(date +%Y%m%d%H%M)
    BACKUP_FOLDER="${APP_INSTALL_PATH}/backup_${TIMESTAMP}"
    
    echo ""
    echo "Starting Update Process..."
    echo "-> Creating backup folder: ${BACKUP_FOLDER}"
    
    # Create backup folder *before* listing contents
    mkdir -p "$BACKUP_FOLDER"
    
    # --- EXCLUSIONS ---
    EXCLUSIONS="-not -name "*.json" -not -name "__pycache__" -not -name "beer-keg.png" -not -name "backup_*" -not -path "$BACKUP_FOLDER""
    
    # Move EVERYTHING out of the project folder into the backup, *EXCLUDING* the retained files/folders
    find "$APP_INSTALL_PATH" -maxdepth 1 -mindepth 1 $EXCLUSIONS -exec mv -t "$BACKUP_FOLDER" {} +
    
    echo "-> Existing project files moved to backup folder: ${BACKUP_FOLDER}"
    echo "-> User settings (*.json), cache, and static assets (beer-keg.png, old backups) retained in main directory."

    # --- COPY NEW FILES FROM TEMP CLONE ---
    echo "2. Installing updated application files..."
    
    # 2a. Copy the Executable
    EXECUTABLE_SOURCE="$EXECUTABLE_NAME_FOUND"
    EXECUTABLE_DESTINATION="${APP_INSTALL_PATH}/${REPO_EXECUTABLE_NAME}"
    cp "$EXECUTABLE_SOURCE" "$EXECUTABLE_DESTINATION"
    
    # 2b. Copy all required support files and core assets from the repository
    for file in $SUPPORT_FILES $CORE_ASSETS $USER_SETTINGS; do
        SOURCE_FILE="${TEMP_DIR}/${PROGRAM_FOLDER}/${file}"
        if [ -f "$SOURCE_FILE" ]; then
            cp "$SOURCE_FILE" "$APP_INSTALL_PATH/"
        fi
    done

    # 3. SET PERMISSIONS
    echo "3. Setting executable permissions on $REPO_EXECUTABLE_NAME..."
    chmod +x "$EXECUTABLE_DESTINATION"

    # 4. FINAL CLEANUP
    echo "4. Cleaning up temporary files."
    rm -rf "$TEMP_DIR"

    echo "Update successful! Backup saved to ${BACKUP_FOLDER}"
    
    # === MODIFIED SECTION: ADDING THE EXIT PROMPT AFTER SUCCESSFUL UPDATE ===
    echo ""
    echo "========================================================================="
    echo "Update complete. Press any key to exit the update."
    echo "========================================================================="

    # Read a single character from the terminal without waiting for Enter
    read -n 1 -s -r < /dev/tty # Force read from TTY
    echo "" # Add newline after keypress for clean exit
    
    exit 0
    # ========================================================================
}


# --- MAIN LOGIC FLOW ---

# 1. Check for Existing Installation (Requirement 1)
if [ ! -d "$APP_INSTALL_PATH" ]; then
    echo "========================================================================="
    echo "ERROR: KegLevel Monitor is NOT installed on this system."
    echo "Please run the installation script first:"
    echo "curl -sL <RAW_GITHUB_LINK>/install.sh | sudo bash"
    echo "========================================================================="
    exit 1
fi


# 2. Show Menu (Requirement 2)
while true; do
    echo ""
    echo "========================================================================="
    echo "KegLevel Monitor is ready to be updated. Please type the letter of the action you want taken:"
    echo ""
    echo "E - Exit this installation without making any changes."
    echo "U - Update the current installation to the most recent version of KegLevel Monitor. All files currently in the KegLevel_Monitor project folder will be saved in a date stamped backup folder. All files with custom data that has been saved (system settings, keg settings, beverage library, notification settings, calibration settings, workflow settings) will be preserved."
    echo "========================================================================="

    # Read input specifically from the terminal (keyboard)
    read -r -p "Selection (E/U): " CHOICE < /dev/tty
    CHOICE=$(echo "$CHOICE" | tr '[:lower:]' '[:upper:]')
    
    case "$CHOICE" in
        E)
            # --- Action E: Exit ---
            echo ""
            echo "Exiting without making any changes"
            echo "Update canceled by user. No changes were made."
            exit 0
            ;;
        
        U)
            # --- Action U: Update ---
            update_action_revised
            ;;
        
        *)
            echo "Invalid selection. Please type E or U."
            ;;
    
    esac
done