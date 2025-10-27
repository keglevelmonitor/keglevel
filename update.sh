#!/bin/bash
# Dedicated update script for KegLevel Monitor (Preserves old versions)

# --- CONFIGURATION ---
REPO_URL="https://github.com/keglevelmonitor/keglevel.git" # IMPORTANT: Your full Git clone URL
PROGRAM_FOLDER="KegLevel_Monitor"
TEMP_DIR=$(mktemp -d)

# --- CORE ASSETS (Files to copy from repo) ---
SUPPORT_FILES="notification_service.py sensor_logic.py settings_manager.py temperature_logic.py"
CORE_ASSETS="bjcp_2015_library.json bjcp_2021_library.json" # Files expected in the repo

# --- EXECUTION ENVIRONMENT SETUP ---
# Determine the target user (finds the user who invoked the script)
TARGET_USER=$(logname)
if [ -z "$TARGET_USER" ]; then
    echo "ERROR: Could not determine the user. Run this script from your user terminal."
    # We exit here with status 1 (error)
    exit 1
fi

DESKTOP_PATH="/home/${TARGET_USER}/Desktop"
APP_INSTALL_PATH="${DESKTOP_PATH}/${PROGRAM_FOLDER}"

# --- FUNCTIONS ---

# Function to pause the script, waiting for a single keypress (no Enter required)
pause_and_exit() {
    echo ""
    echo "--------------------------------------------------------"
    # Use read -n 1 to read a single character, -r for raw input, -p for prompt
    read -n 1 -r -p "Press any key to exit..." < /dev/tty
    echo ""
    # Clean up the temporary clone directory before exiting
    rm -rf "$TEMP_DIR"
    exit $1
}

# Function to extract the date code (YYYYMMDDHHMM) from an executable name
get_date_code() {
    # Extracts the date code (12 digits) from the filename
    basename "$1" | grep -oE '[0-9]{12}' | tail -n 1
}


# Function to handle the core update logic
run_update_process() {
    
    # 1. CLONE REPO TO DISCOVER NEW FILE
    echo "1. Cloning latest code to temporary directory..."
    # We clone first so we can run the version check
    git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}" || { echo "ERROR: Git clone failed. Check REPO_URL."; rm -rf "$TEMP_DIR"; return 1; }

    # --- DYNAMIC EXECUTABLE DISCOVERY (Repo) ---
    NEW_EXE_NAME=$(find "${TEMP_DIR}/${PROGRAM_FOLDER}" -type f -name 'KegLevel_Monitor_*' | sort -r | head -n 1)

    if [ -z "$NEW_EXE_NAME" ]; then
        echo "ERROR: Could not find any new executable (KegLevel_Monitor_*) in the repository."
        pause_and_exit 1
    fi
    NEW_EXE_NAME=$(basename "$NEW_EXE_NAME")
    
    # --- DYNAMIC EXECUTABLE DISCOVERY (Local) ---
    LOCAL_EXE=$(find "$APP_INSTALL_PATH" -maxdepth 1 -type f -name 'KegLevel_Monitor_*' | sort -r | head -n 1)

    # 2. VERSION CHECK AND EXIT
    # --- Local vs Repo Version Comparison ---
    if [ -n "$LOCAL_EXE" ]; then
        LOCAL_DATE=$(get_date_code "$LOCAL_EXE")
        REPO_DATE=$(get_date_code "$NEW_EXE_NAME")

        echo "Local Version: $LOCAL_DATE | Repository Version: $REPO_DATE"

        if [ "$REPO_DATE" -le "$LOCAL_DATE" ]; then
            
            VERSION_MESSAGE="STATUS: Your application is already up to date (or newer)."
            if [ "$REPO_DATE" -eq "$LOCAL_DATE" ]; then
                VERSION_MESSAGE="STATUS: Your application is current (Version $LOCAL_DATE)."
            fi

            echo ""
            echo "--------------------------------------------------------"
            echo "$VERSION_MESSAGE"
            pause_and_exit 0
        fi
        # If we reach here, the local version is OLDER, so proceed with backup.
    fi

    # --- 3. START BACKUP (The "U" Action Logic) ---
    TIMESTAMP=$(date +%Y%m%d%H%M)
    BACKUP_FOLDER="${APP_INSTALL_PATH}/backup_${TIMESTAMP}"
    
    echo ""
    echo "Starting Update Process..."
    echo "-> Creating backup folder: ${BACKUP_FOLDER}"
    
    # Files/patterns to exclude from the backup (i.e., files to KEEP in the main folder)
    # The -path checks use wildcards to match the full path inside the APP_INSTALL_PATH
    EXCLUSIONS="-not -path '*/__pycache__*' \
                -not -name '*.json' \
                -not -name 'beer-keg.png' \
                -not -name 'backup_*'" # Exclude existing backup folders
                
    # Create backup folder
    mkdir -p "$BACKUP_FOLDER"
    
    # Move all existing contents *except* exclusions into the backup folder
    echo "-> Existing project files moved to backup folder: ${BACKUP_FOLDER}"
    echo "-> User settings, cache, and static assets retained in main directory."
    
    # Using 'find' to select files/folders and move them to the backup directory
    find "$APP_INSTALL_PATH" -maxdepth 1 -mindepth 1 $EXCLUSIONS -exec mv -t "$BACKUP_FOLDER" {} +

    # --- 4. START COPY (Install New Files) ---
    NEW_EXE_PATH="${APP_INSTALL_PATH}/${NEW_EXE_NAME}"

    echo "2. Copying new executable: ${NEW_EXE_NAME}"
    cp "${TEMP_DIR}/${PROGRAM_FOLDER}/${NEW_EXE_NAME}" "$NEW_EXE_PATH"
    
    # Copy support files (they overwrite old versions)
    for file in $SUPPORT_FILES; do
        SOURCE_FILE="${TEMP_DIR}/${PROGRAM_FOLDER}/${file}"
        if [ -f "$SOURCE_FILE" ]; then
            cp "$SOURCE_FILE" "$APP_INSTALL_PATH/"
            echo "-> Copied support file: $file"
        fi
    done
    
    echo "3. Setting executable permissions on the new file."
    chmod +x "$NEW_EXE_PATH"

    # 4. FINAL CLEANUP
    echo "4. Cleaning up temporary files."
    # Temporary directory is cleaned in pause_and_exit

    echo "--- Update Complete! ---"
    echo "New executable '${NEW_EXE_NAME}' is installed. Backup saved to ${BACKUP_FOLDER}"
    
    pause_and_exit 0
}


# --- MENU FUNCTION ---
management_menu() {
    
    # --- Menu Loop ---
    while true; do
        echo ""
        echo "========================================================================="
        echo "KegLevel Monitor is ready to be updated. Please type the letter of the action you want taken:"
        echo ""
        echo "E - Exit this installation without making any changes."
        echo "U - Update the current installation to the most recent version of KegLevel Monitor. All files currently in the KegLevel_Monitor project folder will be saved in a date stamped backup folder. All files with custom data that has been saved (system settings, keg settings, beverage library, notification settings, calibration settings, workflow settings) will be preserved."
        echo "========================================================================="

        read -r -p "Selection (E/U): " CHOICE < /dev/tty
        CHOICE=$(echo "$CHOICE" | tr '[:lower:]' '[:upper:]')
        
        case "$CHOICE" in
            E)
                # --- Action E: Exit ---
                echo ""
                echo "Exiting without making any changes."
                # The exit message and pause is now handled by pause_and_exit
                pause_and_exit 0
                ;;
            
            U)
                # --- Action U: Update ---
                echo ""
                echo "Creating backup of project folder and leaving all settings files intact"
                run_update_process
                # This line is only reached if run_update_process fails unexpectedly before calling pause_and_exit
                return 0
                ;;

            *)
                echo "Invalid selection. Please type E or U."
                ;;
        esac
    done
}


# --- MAIN LOGIC FLOW ---

# 1. VALIDATION CHECK (If no install, abort and inform user)
if [ ! -d "$APP_INSTALL_PATH" ]; then
    echo "ERROR: Installation directory not found at ${APP_INSTALL_PATH}"
    echo "Please run the full installation command first: curl -sL <RAW_GITHUB_LINK>/install.sh | sudo bash"
    pause_and_exit 1
fi


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
