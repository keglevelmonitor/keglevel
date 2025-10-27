#!/bin/bash
# Desktop Installer script for KegLevel Monitor
# This script is designed to be run as root (or with sudo) via:
# curl -sL <RAW_GITHUB_LINK>/install.sh | sudo bash

# --- CONFIGURATION ---
REPO_URL="https://github.com/keglevelmonitor/keglevel.git" 
PROGRAM_FOLDER="KegLevel_Monitor"
SHORTCUT_FILE="KegLevel.desktop"
# NOTE: EXECUTABLE_NAME has been removed. The script now dynamically finds the newest executable.
TEMP_DIR=$(mktemp -d)

# New list of support files to copy alongside the executable
SUPPORT_FILES="notification_service.py sensor_logic.py settings_manager.py temperature_logic.py"

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
SHORTCUT_PATH="${DESKTOP_PATH}/${SHORTCUT_FILE}" # Defined here for use in 'D' action

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
    git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}" || { echo "ERROR: Git clone failed. Check REPO_URL."; rm -rf "$TEMP_DIR"; exit 1; }
    
    # --- DYNAMIC EXECUTABLE DISCOVERY ---
    # Finds the single file in the cloned repo matching the KegLevel_Monitor_* pattern.
    # This ensures the script always uses the newest, correct executable name.
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
    
    # 3b. Copy the four new support files and any existing config/library files (e.g., JSON)
    for file in $SUPPORT_FILES config.json settings.json bjcp_2015_library.json bjcp_2021_library.json wiring.gif; do
        SOURCE_FILE="${TEMP_DIR}/${PROGRAM_FOLDER}/${file}"
        if [ -f "$SOURCE_FILE" ]; then
            cp "$SOURCE_FILE" "$APP_INSTALL_PATH/"
        else
            echo "    WARNING: Support file '$file' not found in the repository."
        fi
    done
    
    # Set correct ownership (crucial for the user to be able to access and run files)
    echo "    Setting ownership to ${TARGET_USER}..."
    chown -R ${TARGET_USER}:${TARGET_USER} "$APP_INSTALL_PATH"

    # Ensure the executable inside the folder is executable
    echo "    Setting executable permissions on $EXECUTABLE_BASE_NAME..."
    chmod +x "$EXECUTABLE_DESTINATION"

    # 4. INSTALL DESKTOP SHORTCUT
    echo "4. Installing desktop shortcut file..."
    SHORTCUT_SOURCE="${TEMP_DIR}/${SHORTCUT_FILE}"
    SHORTCUT_DESTINATION="${DESKTOP_PATH}/${SHORTCUT_FILE}"

    if [ ! -f "$SHORTCUT_SOURCE" ]; then
        echo "WARNING: Shortcut file '${SHORTCUT_FILE}' not found. Skipping shortcut installation."
    else
        # Use 'cp' here since 'mv' in the old version sometimes causes issues if target exists.
        cp "$SHORTCUT_SOURCE" "$SHORTCUT_DESTINATION"
        chown ${TARGET_USER}:${TARGET_USER} "$SHORTCUT_DESTINATION"
        chmod +x "$SHORTCUT_DESTINATION"
        
        # Mark the shortcut as trusted (requires gio command, which may fail silently if not found/logged in)
        echo "    Setting trusted attribute on shortcut..."
        su -c "gio set \"$SHORTCUT_DESTINATION\" \"metadata::trusted\" true" ${TARGET_USER} 2>/dev/null
    fi
    
    # 5. FINAL CLEANUP
    echo "5. Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
    echo "--- Installation Complete! ---"
    
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
                # --- Action U: Update (Backup, then Reinstall) ---
                echo ""
                echo "Creating backup of project folder and leaving all settings files intact"
                
                TIMESTAMP=$(date +%Y%m%d%H%M)
                BACKUP_FOLDER="${APP_INSTALL_PATH}/backup_${TIMESTAMP}"
                
                echo ""
                echo "Starting Update Process..."
                echo "-> Creating backup folder: ${BACKUP_FOLDER}"
                
                # FIX 1: Create backup folder *before* listing contents to avoid self-reference error
                mkdir -p "$BACKUP_FOLDER"
                
                # --- FIX 2 & 3: EXCLUDE JSON, __pycache__, and beer-keg.png from being moved/backed up ---
                # beer-keg.png is now explicitly excluded along with JSON files and the cache directory.
                EXCLUSIONS="-not -name "*.json" -not -name "__pycache__" -not -name "beer-keg.png""
                
                # Move EVERYTHING out of the project folder into the backup, *EXCLUDING* the backup folder itself AND user data
                # Files not moved: backup folder itself, any file ending in .json, the __pycache__ directory, and beer-keg.png
                find "$APP_INSTALL_PATH" -maxdepth 1 -mindepth 1 -not -path "$BACKUP_FOLDER" $EXCLUSIONS -exec mv -t "$BACKUP_FOLDER" {} +
                
                echo "-> Existing project files moved to backup folder: ${BACKUP_FOLDER}"
                echo "-> User settings (*.json), cache (__pycache__), and static assets (beer-keg.png) retained in main directory."

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
                # --- Action D: Delete and Reinstall ---
                echo ""
                echo "Delete the current installation and reinstall KegLevel Monitor from scratch - DANGER! Any custom data or settings will be deleted and cannot be recovered"
                
                echo ""
                echo "Starting Delete and Reinstall Process..."
                
                # 1. Delete the application folder
                echo "-> Deleting application folder: ${APP_INSTALL_PATH}"
                rm -rf "$APP_INSTALL_PATH"
                
                # 2. Delete the desktop shortcut
                echo "-> Deleting desktop shortcut: ${SHORTCUT_PATH}"
                rm -f "$SHORTCUT_PATH"
                
                # 3. Reinstall from scratch
                initial_install_and_cleanup
                
                if [ $? -eq 0 ]; then
                    echo "Reinstallation complete! Old data permanently deleted."
                    exit 0
                else
                    echo "Reinstallation failed. Check log."
                    exit 1
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
