import os
import glob
import time
from fuzzywuzzy import process
import pygetwindow as gw
import audio  # Assumes your audio module has listen() and speak() functions

def get_known_locations():
    """Retrieve common user folder paths dynamically."""
    user_home = os.path.expanduser("~")
    paths = {
        "desktop": os.path.join(user_home, "Desktop"),
        "documents": os.path.join(user_home, "Documents"),
        "downloads": os.path.join(user_home, "Downloads"),
        "c drive": "C:\\",
        "d drive": "D:\\"
    }
    # Handle OneDrive redirection on Windows
    if os.name == "nt":
        onedrive_path = os.path.join(user_home, "OneDrive")
        if os.path.exists(os.path.join(onedrive_path, "Desktop")):
            paths["desktop"] = os.path.join(onedrive_path, "Desktop")
        if os.path.exists(os.path.join(onedrive_path, "Documents")):
            paths["documents"] = os.path.join(onedrive_path, "Documents")
        if os.path.exists(os.path.join(onedrive_path, "Downloads")):
            paths["downloads"] = os.path.join(onedrive_path, "Downloads")
    return paths

def resolve_location(location):
    """Resolve a user-provided location into a valid system path."""
    base_paths = get_known_locations()
    loc = location.lower().strip(" .")
    if loc in base_paths:
        return base_paths[loc]
    if loc.startswith(('c drive', 'd drive')):
        return f"{loc[0].upper()}:\\"
    if os.path.isabs(loc):
        return os.path.normpath(loc)
    return None

def find_best_match(file_name, search_path):
    """Find the closest matching file in the given path using fuzzy matching."""
    try:
        all_items = os.listdir(search_path)
        best_match, confidence = process.extractOne(file_name, all_items)
        if confidence > 70:
            return os.path.join(search_path, best_match)
    except Exception as e:
        audio.speak(f"Error finding best match: {e}")
    return None

def find_file_with_any_extension(file_name, search_path):
    """Search for a file with any extension in the specified folder."""
    pattern = os.path.join(search_path, f"{file_name}.*")
    files = glob.glob(pattern)
    return files[0] if files else None

def bring_window_to_front(partial_title, timeout=10):
    """
    Attempt to bring a window whose title contains partial_title to the front.
    Waits up to 'timeout' seconds.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        windows = gw.getAllWindows()
        print("Available window titles:")
        for w in windows:
            print(f" - {w.title}")
        for window in windows:
            if partial_title.lower() in window.title.lower():
                try:
                    window.activate()
                    audio.speak(f"Brought window '{window.title}' to the front.")
                    return True
                except Exception as e:
                    print(f"Error activating window: {e}")
        time.sleep(1)
    # audio.speak("Could not find the window to bring to the front.")
    return False

def parse_file_command(command):
    """
    Parse a command like "open demo from downloads" into a file name and location.
    If "from" is present, splits the command around it.
    Otherwise, defaults location to 'downloads'.
    This function also strips trailing punctuation.
    """
    command = command.lower()
    if " from " in command:
        parts = command.split(" from ")
        file_name = parts[0].replace("open", "").strip(" .")
        location = parts[1].strip(" .")
    else:
        file_name = command.replace("open", "").strip(" .")
        location = "downloads"
    return file_name, location

def open_or_retrieve_file(file_name, location):
    """Open or retrieve a file from the specified location."""
    search_path = resolve_location(location)
    if not search_path:
        audio.speak(f"Could not resolve location '{location}'.")
        return
    if not os.path.exists(search_path):
        audio.speak(f"Path '{search_path}' does not exist.")
        return
    matched_path = find_best_match(file_name, search_path)
    if not matched_path:
        matched_path = find_file_with_any_extension(file_name, search_path)
    if matched_path:
        if os.path.isfile(matched_path):
            audio.speak(f"Opening file {file_name} from {location}.")
            os.startfile(matched_path)
            # Use the file's base name as a hint to bring its window forward.
            window_title = os.path.basename(matched_path)
            bring_window_to_front(window_title)
        else:
            audio.speak(f"Found {file_name}, but it's not a file.")
    else:
        audio.speak(f"Sorry, no file named {file_name} found in {location}.")

def retrive_file():
    """
    Capture a single voice command that includes both the file name and location,
    then parse and open the file.
    Example command: "open demo from downloads"
    """
    audio.speak("Sure! What would you like me to retrive ? ")
    try:
        command = audio.listen().strip()
    except Exception as e:
        audio.speak("Error capturing your command.")
        print(f"Error in audio.listen(): {e}")
        return
    if not command:
        audio.speak("I did not catch a command. Exiting file retrieval.")
        return
    file_name, location = parse_file_command(command)
    print(f"Parsed command: file_name='{file_name}', location='{location}'")
    open_or_retrieve_file(file_name, location)


