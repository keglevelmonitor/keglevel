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

# Function containing the core file update steps (Clones, copies files, sets permissions)
# NOTE: This function is called without 'sudo' privileges.
core_update_process() {
    
    # We must install git if it is not present because we need to clone the repo.
    # Since this script runs WITHOUT sudo, we can only check, not install.
    if ! command -v git &> /dev/null
    then
        echo "ERROR: Git is not installed. Please run the full install script or install git manually."
        return 1
    fi
    
    # 1. DOWNLOAD THE CODE
    echo "1. Cloning code from ${REPO_URL} into temporary directory..."
    # Use the full URL for the clone
    git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}" || { echo "ERROR: Git clone failed. Check REPO_URL."; rm -rf "$TEMP_DIR"; return 1; }
    
    # --- DYNAMIC EXECUTABLE DISCOVERY ---
    EXECUTABLE_NAME_FOUND=$(find "${TEMP_DIR}/${PROGRAM_FOLDER}" -maxdepth 1 -type f -name "KegLevel_Monitor_*" -print -quit)
    
    if [ -z "$EXECUTABLE_NAME_FOUND" ]; then
        echo "ERROR: No executable file matching 'KegLevel_Monitor_*' found in the repository. Aborting."
        rm -rf "$TEMP_DIR"
        return 1
    fi
    EXECUTABLE_BASE_NAME=$(basename "$EXECUTABLE_NAME_FOUND")
    echo "    Dynamically found executable: $EXECUTABLE_BASE_NAME"
    
    # 2. INSTALL APPLICATION FILES
    echo "2. Installing updated application files..."
    
    # 2a. Copy the Executable (overwrites the old one, but preserves user settings)
    EXECUTABLE_SOURCE="$EXECUTABLE_NAME_FOUND"
    EXECUTABLE_DESTINATION="${APP_INSTALL_PATH}/${EXECUTABLE_BASE_NAME}"

    cp "$EXECUTABLE_SOURCE" "$EXECUTABLE_DESTINATION"
    
    # 2b. Copy all required support files and core assets from the repository
    # These files WILL overwrite existing files if the names are the same.
    for file in $SUPPORT_FILES $CORE_ASSETS $USER_SETTINGS; do
        SOURCE_FILE="${TEMP_DIR}/${PROGRAM_FOLDER}/${file}"
        if [ -f "$SOURCE_FILE" ]; then
            cp "$SOURCE_FILE" "$APP_INSTALL_PATH/"
        # No warning here; assume core files are being maintained in the repo.
        fi
    done

    # 3. SET PERMISSIONS
    echo "3. Setting executable permissions on $EXECUTABLE_BASE_NAME..."
    chmod +x "$EXECUTABLE_DESTINATION"

    # 4. FINAL CLEANUP
    echo "4. Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
    echo "--- Update Complete! ---"
    
    return 0
}

# Function to handle the update process (Backup, then Call Core Update)
update_action() {
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
    # Exclusions: JSON files, cache, beer-keg.png, and any folder/file starting with 'backup_'
    EXCLUSIONS="-not -name "*.json" -not -name "__pycache__" -not -name "beer-keg.png" -not -name "backup_*" -not -path "$BACKUP_FOLDER""
    
    # Move EVERYTHING out of the project folder into the backup, *EXCLUDING* the retained files/folders
    find "$APP_INSTALL_PATH" -maxdepth 1 -mindepth 1 $EXCLUSIONS -exec mv -t "$BACKUP_FOLDER" {} +
    
    echo "-> Existing project files moved to backup folder: ${BACKUP_FOLDER}"
    echo "-> User settings (*.json), cache, and static assets (beer-keg.png, old backups) retained in main directory."

    # Run the core update (installs fresh copies over the now-empty APP_INSTALL_PATH)
    core_update_process
    
    if [ $? -eq 0 ]; then
        echo "Update successful! Backup saved to ${BACKUP_FOLDER}"
        exit 0
    else
        echo "Update failed. Check log."
        exit 1
    fi
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
            update_action
            ;;
        
        *)
            echo "Invalid selection. Please type E or U."
            ;;
    
    esac
done
