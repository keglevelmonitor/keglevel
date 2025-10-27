#!/bin/bash
# Desktop Installer script for KegLevel Monitor
# This script is designed to be run as root (or with sudo) via:
# curl -sL <RAW_GITHUB_LINK>/install.sh | sudo bash

# --- CONFIGURATION ---
REPO_URL="https://github.com/keglevelmonitor/keglevel.git" 
PROGRAM_FOLDER="KegLevel_Monitor"
SHORTCUT_FILES="KegLevel.desktop KegLevelUpdater.desktop" # <--- EDITED: Added new shortcut
# NOTE: EXECUTABLE_NAME has been removed. The script now dynamically finds the newest executable.
TEMP_DIR=$(mktemp -d)

# Files that are code components/support scripts
SUPPORT_FILES="notification_service.py sensor_logic.py settings_manager.py temperature_logic.py"

# Files that should be present in the repository and MUST be copied
# Includes library files and static assets needed for installation.
CORE_ASSETS="bjcp_2015_library.json bjcp_2021_library.json beer-keg.png arrow.png" 

# Files that are RETAINED by the user and *may not* exist in the repo, but if they do, should be copied/overwritten
USER_SETTINGS="config.json settings.json"


# --- CHECK FOR ROOT PRIVILEGES ---
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with 'sudo'."
    echo "Please run the full install command starting with 'curl' and ending with 'sudo bash'."
    exit 1
fi

# --- IDENTIFY THE TARGET USER ---
TARGET_USER=$(logname)
if [ -z "$TARGET_USER" ]; then
    echo "ERROR: Could not determine the user who invoked sudo."
    echo "Please ensure you run this script from a graphical user's terminal session."
    rm -rf "$TEMP_DIR"
    exit 1
fi

DESKTOP_PATH="/home/${TARGET_USER}/Desktop"
APP_INSTALL_PATH="${DESKTOP_PATH}/${PROGRAM_FOLDER}"
# SHORTCUT_PATH removed as we now iterate over SHORTCUT_FILES

echo "--- Starting installation of KegLevel Monitor for user: ${TARGET_USER} ---"


# --- FUNCTIONS ---

# Function containing the core installation steps (Clones, copies files, sets permissions)
initial_install_and_cleanup() {
    
    # 1. INSTALL GIT DEPENDENCY
    echo "1. Ensuring git is installed..."
    apt update -y
    apt install -y git || { echo "ERROR: Git installation failed."; rm -rf "$TEMP_DIR"; exit 1; }

    # 2. DOWNLOAD THE CODE
    echo "2. Cloning code from ${REPO_URL} into temporary directory..."
    local TEMP_DIR=$(mktemp -d) 
    git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}" || { echo "ERROR: Git clone failed. Check REPO_URL."; rm -rf "$TEMP_DIR"; exit 1; }
    
    # --- DYNAMIC EXECUTABLE DISCOVERY ---
    # Finds the single file in the cloned repo matching the KegLevel_Monitor_* pattern.
    EXECUTABLE_NAME_FOUND=$(find "${TEMP_DIR}/${PROGRAM_FOLDER}" -maxdepth 1 -type f -name "KegLevel_Monitor_*" -print -quit)
    
    if [ -z "$EXECUTABLE_NAME_FOUND" ]; then
        echo "ERROR: No executable file matching 'KegLevel_Monitor_*' found in the repository. Aborting."
        rm -rf "$TEMP_DIR"
        return 1
    fi
    # Extracts only the filename
    EXECUTABLE_BASE_NAME=$(basename "$EXECUTABLE_NAME_FOUND")
    echo "    Dynamically found executable: $EXECUTABLE_BASE_NAME"
    
    # 3. INSTALL PROGRAM FOLDER AND SET PERMISSIONS
    echo "3. Installing application files to Desktop..."
    
    # Create the final directory structure if it doesn't exist (needed for D and U actions)
    mkdir -p "$APP_INSTALL_PATH" 
    
    # 3a. Copy the Executable
    EXECUTABLE_SOURCE="$EXECUTABLE_NAME_FOUND"
    EXECUTABLE_DESTINATION="${APP_INSTALL_PATH}/${EXECUTABLE_BASE_NAME}"

    cp "$EXECUTABLE_SOURCE" "$EXECUTABLE_DESTINATION"
    
    # 3b. Copy all required support files and core assets from the repository
    for file in $SUPPORT_FILES $CORE_ASSETS; do
        SOURCE_FILE="${TEMP_DIR}/${PROGRAM_FOLDER}/${file}"
        if [ -f "$SOURCE_FILE" ]; then
            cp "$SOURCE_FILE" "$APP_INSTALL_PATH/"
        else
            echo "    WARNING: Core file '$file' not found in the repository. This may cause runtime errors."
        fi
    done

    # 3c. Copy user settings files (no warning, they might be missing if repo is clean)
    for file in $USER_SETTINGS; do
        SOURCE_FILE="${TEMP_DIR}/${PROGRAM_FOLDER}/${file}"
        if [ -f "$SOURCE_FILE" ]; then
            cp "$SOURCE_FILE" "$APP_INSTALL_PATH/"
        fi
    done
    
    # Set correct ownership (crucial for the user to be able to access and run files)
    echo "    Setting ownership to ${TARGET_USER}..."
    chown -R ${TARGET_USER}:${TARGET_USER} "$APP_INSTALL_PATH"

    # Ensure the executable inside the folder is executable
    echo "    Setting executable permissions on $EXECUTABLE_BASE_NAME..."
    chmod +x "$EXECUTABLE_DESTINATION"

    # 4. INSTALL DESKTOP SHORTCUTS # <--- EDITED: Pluralized header
    echo "4. Installing desktop shortcut files..."
    
    # Loop over the SHORTCUT_FILES variable
    for shortcut in $SHORTCUT_FILES; do # <--- EDITED: Loop added
        SHORTCUT_SOURCE="${TEMP_DIR}/${shortcut}"
        SHORTCUT_DESTINATION="${DESKTOP_PATH}/${shortcut}"
        
        if [ ! -f "$SHORTCUT_SOURCE" ]; then
            echo "WARNING: Shortcut file '${shortcut}' not found. Skipping shortcut installation."
        else
            echo "    Installing shortcut: ${shortcut}" # <--- EDITED: Added file name to echo
            cp "$SHORTCUT_SOURCE" "$SHORTCUT_DESTINATION"
            chown ${TARGET_USER}:${TARGET_USER} "$SHORTCUT_DESTINATION"
            chmod +x "$SHORTCUT_DESTINATION"
            
            # Mark the shortcut as trusted 
            echo "    Setting trusted attribute on shortcut..."
            su -c "gio set \"$SHORTCUT_DESTINATION\" \"metadata::trusted\" true" ${TARGET_USER} 2>/dev/null
        fi
    done # <--- EDITED: End of loop
    
    # 5. FINAL CLEANUP
    echo "5. Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
    echo "--- Installation Complete! ---"
    
    return 0
}


# Function to handle the version comparison logic
local_version_check() {
    local REPO_EXECUTABLE_NAME="$1"
    
    # Extract the timestamp (YYYYMMDDHHMM) from the repository executable name
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


# Function to display the menu and handle user choice
management_menu() {
    
    # --- Menu Loop ---
    while true; do
        echo ""
        echo "========================================================================="
        echo "KegLevel Monitor is already installed. Please type the letter of the action you want taken:"
        echo ""
        echo "E - Exit this installation without making any changes."
        echo "U - Update the current installation to the most recent version of KegLevel Monitor. All files currently in the KegLevel_Monitor project folder will be saved in a date stamped backup folder. All files with custom data that has been saved (system settings, keg settings, beverage library, notification settings, calibration settings, workflow settings) will be preserved."
        echo "D - Delete the current installation and reinstall from scratch. DANGER! Any custom data or settings will be deleted and cannot be recovered."
        echo "========================================================================="

        # Read input specifically from the terminal (keyboard)
        read -r -p "Selection (E/U/D): " CHOICE < /dev/tty
        CHOICE=$(echo "$CHOICE" | tr '[:lower:]' '[:upper:]')
        
        case "$CHOICE" in
            E)
                # --- Action E: Exit ---
                echo ""
                echo "Exiting without making any changes"
                echo "Installer exited by user. No changes were made."
                exit 0
                ;;
            
            U)
                # --- Action U: Update (Version Check, then Backup/Reinstall) ---
                echo ""
                
                # Check 1: Clone repo to get latest version info
                echo "1. Cloning code from ${REPO_URL} into temporary directory for version check..."
                local TEMP_DIR_CHECK=$(mktemp -d)
                if ! command -v git &> /dev/null; then
                    echo "ERROR: Git is not installed. Cannot perform version check. Aborting update."
                    rm -rf "$TEMP_DIR_CHECK"
                    break
                fi
                git clone --depth 1 "${REPO_URL}" "${TEMP_DIR_CHECK}" || { echo "ERROR: Git clone failed. Check REPO_URL. Aborting update."; rm -rf "$TEMP_DIR_CHECK"; break; }

                local EXECUTABLE_NAME_CHECK=$(find "${TEMP_DIR_CHECK}/${PROGRAM_FOLDER}" -maxdepth 1 -type f -name "KegLevel_Monitor_*" -print -quit)
                if [ -z "$EXECUTABLE_NAME_CHECK" ]; then
                    echo "ERROR: No executable file matching 'KegLevel_Monitor_*' found in the repository. Aborting."
                    rm -rf "$TEMP_DIR_CHECK"
                    break
                fi
                local REPO_EXECUTABLE_NAME=$(basename "$EXECUTABLE_NAME_CHECK")
                
                # Check 2: Compare versions
                local_version_check "$REPO_EXECUTABLE_NAME"
                local CHECK_RESULT=$?
                
                # Clean up the check clone directory immediately
                rm -rf "$TEMP_DIR_CHECK"

                if [ $CHECK_RESULT -eq 1 ]; then
                    # Version check determined no update is needed (exit was handled in the function)
                    exit 0
                fi
                
                # If we reach here, an update IS REQUIRED. Proceed with Backup and Reinstall.
                
                echo ""
                echo "Local version is older. Proceeding with update."
                echo "Creating backup of project folder and leaving all settings files intact"
                
                TIMESTAMP=$(date +%Y%m%d%H%M)
                BACKUP_FOLDER="${APP_INSTALL_PATH}/backup_${TIMESTAMP}"
                
                echo ""
                echo "Starting Update Process..."
                echo "-> Creating backup folder: ${BACKUP_FOLDER}"
                
                # Create backup folder *before* listing contents to avoid self-reference error
                mkdir -p "$BACKUP_FOLDER"
                
                # --- EXCLUSIONS ---
                # Exclusions: JSON files, cache, beer-keg.png, arrow.png and any folder/file starting with 'backup_'
                EXCLUSIONS="-not -name "*.json" -not -name "__pycache__" -not -name "beer-keg.png" -not -name "arrow.png" -not -name "backup_*" -not -path "$BACKUP_FOLDER""
                
                # Move EVERYTHING out of the project folder into the backup, *EXCLUDING* the retained files/folders
                find "$APP_INSTALL_PATH" -maxdepth 1 -mindepth 1 $EXCLUSIONS -exec mv -t "$BACKUP_FOLDER" {} +
                
                echo "-> Existing project files moved to backup folder: ${BACKUP_FOLDER}"
                echo "-> User settings (*.json), cache, and static assets (beer-keg.png, arrow.png, old backups) retained in main directory."

                # Reinstall the application (installs fresh copies over the now-empty APP_INSTALL_PATH)
                initial_install_and_cleanup
                
                if [ $? -eq 0 ]; then
                    echo "Update complete! Backup saved to ${BACKUP_FOLDER}"
                    exit 0
                else
                    echo "Update failed during reinstallation. Check log."
                    exit 1
                fi
                ;;
            
            D)
                # --- Action D: Delete and Reinstall with Confirmation ---
                DANGER_MSG="Delete the current installation and reinstall from scratch is DESTRUCTIVE! Any custom data or settings will be deleted and cannot be recovered."
                
                echo ""
                echo "$DANGER_MSG"
                
                read -r -p "Enter Y to proceed or N to exit without changes: " CONFIRM_CHOICE < /dev/tty
                CONFIRM_CHOICE=$(echo "$CONFIRM_CHOICE" | tr '[:lower:]' '[:upper:]')

                if [ "$CONFIRM_CHOICE" == "Y" ]; then
                    echo ""
                    echo "Starting Delete and Reinstall Process..."
                    
                    # 1. Delete the application folder
                    echo "-> Deleting application folder: ${APP_INSTALL_PATH}"
                    rm -rf "$APP_INSTALL_PATH"
                    
                    # 2. Delete the desktop shortcuts # <--- EDITED: Pluralized header
                    echo "-> Deleting desktop shortcut files..."
                    for shortcut in $SHORTCUT_FILES; do # <--- EDITED: Loop added
                        SHORTCUT_PATH="${DESKTOP_PATH}/${shortcut}"
                        echo "    Deleting shortcut: ${shortcut}"
                        rm -f "$SHORTCUT_PATH"
                    done # <--- EDITED: End of loop
                    
                    # 3. Reinstall from scratch
                    initial_install_and_cleanup
                    
                    if [ $? -eq 0 ]; then
                        echo "Reinstallation complete! Old data permanently deleted."
                        exit 0
                    else
                        echo "Reinstallation failed. Check log."
                        exit 1
                    fi
                elif [ "$CONFIRM_CHOICE" == "N" ]; then
                    echo ""
                    echo "Deletion canceled by user. Exiting without making any changes."
                    exit 0
                else
                    echo "Invalid confirmation entered. Exiting without making any changes."
                    exit 0
                fi
                ;;

            *)
                echo "Invalid selection. Please type E, U, or D."
                ;;
            
        esac
    done
}


# --- MAIN LOGIC FLOW ---

if [ -d "$APP_INSTALL_PATH" ]; then
    # Installation directory found, show the management menu
    management_menu
else
    # No installation found, proceed with initial installation
    initial_install_and_cleanup
    exit $?
fi