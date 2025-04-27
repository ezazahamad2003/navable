import os
import psutil
import audio  # For voice feedback
import pygetwindow as gw  # For working with windows

# List of user applications to close
TARGET_APPLICATIONS = [
    "chrome.exe", "firefox.exe", "msedge.exe", "whatsapp.exe", "spotify.exe",
    "notepad.exe", "word.exe", "excel.exe", "powerpnt.exe",
    "teams.exe", "zoom.exe", "outlook.exe", "calendar.exe", "Photos.exe", "explorer.exe"
]

EXCLUDED_APPLICATIONS = ["devenv.exe"]  # Visual Studio stays open

def get_running_target_apps():
    """
    Get a list of all running processes that match our TARGET_APPLICATIONS list.
    """
    running_apps = []
    for process in psutil.process_iter(attrs=['pid', 'name']):
        try:
            process_name = process.info['name'].lower()
            if process_name in TARGET_APPLICATIONS and process_name not in EXCLUDED_APPLICATIONS:
                running_apps.append((process.info['pid'], process_name))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return running_apps

def gracefully_close_window_by_title(process_name):
    """
    Attempt to close the application window by title using pygetwindow.
    """
    try:
        for window in gw.getWindowsWithTitle(process_name):
            if window and window.isVisible:
                window.close()
                print(f"Gracefully closed: {window.title}")
                return True
    except Exception as e:
        print(f"Error closing {process_name} by title: {e}")
    return False

def close_active_apps():
    """
    Gracefully closes user-opened applications or force closes them if needed.
    """
    running_apps = get_running_target_apps()

    if not running_apps:
        audio.speak("No active applications need to be closed.")
        return

    audio.speak(f"Closing {len(running_apps)} applications now.")
    for pid, process_name in running_apps:
        try:
            # First, attempt to close the application window gracefully by title
            if not gracefully_close_window_by_title(process_name):
                # Fallback: Forcefully terminate the process if graceful close fails
                os.system(f"taskkill /PID {pid} /F")
                print(f"Force closed: {process_name} (PID: {pid})")
            else:
                print(f"Gracefully closed: {process_name} (PID: {pid})")
        except Exception as e:
            print(f"Failed to close {process_name}: {e}")

    audio.speak("All selected applications have been closed successfully.")

