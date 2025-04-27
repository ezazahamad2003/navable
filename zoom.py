import requests
import json
import os
import subprocess
import pyautogui
import time
import pyperclip
from datetime import datetime, timezone, timedelta
import os
import subprocess
import time
import base64
import pygetwindow as gw
from PIL import ImageGrab
import openai  # Ensure OpenAI library is installed and updated
from groq import Groq
import audio
from dotenv import load_dotenv # Import dotenv

# Load environment variables from .env file
load_dotenv()

# --- Groq Initialization ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables.")
# Initialize the Groq client using the environment variable
client = Groq(api_key=GROQ_API_KEY)
# --- End Groq Initialization ---


# --- Zoom OAuth Credentials ---
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")

if not all([ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, ZOOM_ACCOUNT_ID]):
    raise ValueError("Zoom API credentials (CLIENT_ID, CLIENT_SECRET, ACCOUNT_ID) not found in environment variables.")

# --- Zoom API endpoints ---
# Use the loaded ACCOUNT_ID
TOKEN_URL = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ZOOM_ACCOUNT_ID}"
ZOOM_MEETING_URL = "https://api.zoom.us/v2/users/me/meetings"
# --- End Zoom Credentials/Endpoints ---

# --- OpenAI Initialization ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")
# Initialize the OpenAI client using the environment variable
gpt_client = openai.OpenAI(api_key=OPENAI_API_KEY)
# --- End OpenAI Initialization ---


# 🔹 Token storage file
TOKEN_FILE = "zoom_token.json"

# NOTE:
# Make sure you have set up your Groq client.
# For example, if using a hypothetical Groq SDK:
# from groq_sdk import Client
# client = Client(api_key="YOUR_GROQ_API_KEY")
#
# For this example, we assume that a global `client` object is already available.

def fetch_new_token():
    """Fetch a new OAuth token from Zoom and save it to a file."""
    # Use environment variables for client ID and secret
    response = requests.post(TOKEN_URL, auth=(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET))
    if response.status_code == 200:
        token_data = response.json()
        expiry_time = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=token_data["expires_in"])
        token_data["expiry_time"] = expiry_time.isoformat()
        with open(TOKEN_FILE, "w") as file:
            json.dump(token_data, file)
        return token_data
    else:
        print("❌ Error fetching new token:", response.text)
        # Consider more specific error handling or logging here
        # exit(1) # Avoid exiting the entire application if possible
        return None # Indicate failure

def get_access_token():
    """Retrieve a valid access token, fetching a new one if needed."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as file:
                token_data = json.load(file)
            expiry_time_str = token_data.get("expiry_time", None)
            if expiry_time_str:
                expiry_time = datetime.fromisoformat(expiry_time_str)
                if datetime.utcnow().replace(tzinfo=timezone.utc) < expiry_time:
                    return token_data["access_token"]
            else:
                print("⚠️ Token file exists but expiry_time is missing. Fetching new token.")
        except (json.JSONDecodeError, KeyError):
            print("⚠️ Corrupted or invalid token file. Fetching new token.")
    return fetch_new_token()["access_token"]

def parse_meeting_command_groq(user_input):
    """
    Uses the Groq API to extract meeting details from natural language input.
    
    Expected JSON output (strictly JSON, no extra text) should have the following keys:
      - "topic": the meeting title.
      - "date": the meeting date in YYYY-MM-DD format.
      - "time": the meeting start time in HH:MM AM/PM format.
      - "duration": the meeting duration in minutes (an integer).

    Example:
      Input: "Schedule a meeting titled 'Team Sync' on 2025-02-10 at 03:00 PM for 30 minutes"
      Output: {"topic": "Team Sync", "date": "2025-02-10", "time": "03:00 PM", "duration": 30}
    """
    prompt = f"""
You are an AI assistant that only returns structured JSON data.
Extract the meeting details from the user input. The JSON must have the following keys:
  - "topic": the meeting title.
  - "date": the meeting date in YYYY-MM-DD format.
  - "time": the meeting start time in HH:MM AM/PM format.
  - "duration": the meeting duration in minutes as an integer.
Ensure the output is strictly JSON with no additional commentary.

Example:
Input: "Schedule a meeting titled 'Team Sync' on 2025-02-10 at 03:00 PM for 30 minutes"
Output: {{"topic": "Team Sync", "date": "2025-02-10", "time": "03:00 PM", "duration": 30}}

User Input: {user_input}
Output:
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # Deterministic output
            max_tokens=50
        )

        if not response or not response.choices:
            print("❌ ERROR: Empty response from Groq.")
            return None

        output = response.choices[0].message.content.strip()
        print(f"DEBUG: Groq Response: {output}")

        if not output.startswith("{"):
            print("❌ ERROR: Groq did not return valid JSON.")
            return None

        result = json.loads(output)
        topic = result.get("topic", "Untitled Meeting")
        date_str = result.get("date")
        time_str = result.get("time")
        duration = result.get("duration")

        if not date_str or not time_str or duration is None:
            print("❌ ERROR: Missing meeting details in Groq output.")
            return None

        return {
            "topic": topic,
            "date": date_str,
            "time": time_str,
            "duration": duration
        }

    except json.JSONDecodeError as e:
        print(f"❌ JSON Parsing Error: {e}")
        return None
    except Exception as e:
        print(f"❌ ERROR parsing command with Groq: {e}")
        return None

def schedule_zoom_meeting():
    """Schedule a Zoom meeting using meeting details parsed via Groq."""
    access_token = get_access_token()  # Ensure a valid token is used
    if not access_token: # Check if token retrieval failed
        print("❌ Failed to obtain Zoom access token. Cannot schedule meeting.")
        return None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # ✅ Get natural language input for meeting details
    audio.speak(
        "Please describe the meeting  "
    )
    time.sleep(1)

    user_input = audio.listen().strip()

    meeting_details = parse_meeting_command_groq(user_input)
    if not meeting_details:
        print("❌ Failed to parse meeting details. Please try again.")
        return None

    topic = meeting_details["topic"]
    date_str = meeting_details["date"]
    time_input = meeting_details["time"]
    duration = meeting_details["duration"]
    original_time_format = f"{time_input} PST"  # For display purposes

    # Convert the provided time to 24-hour format for the Zoom API
    try:
        formatted_time = datetime.strptime(time_input, "%I:%M %p").strftime("%H:%M")
    except ValueError:
        print("❌ Time format error. Please ensure the time is in HH:MM AM/PM format.")
        return None

    start_time = f"{date_str}T{formatted_time}:00"

    meeting_payload = {
        "topic": topic,
        "type": 2,  # Scheduled meeting
        "start_time": start_time,
        "duration": int(duration),
        "timezone": "America/Los_Angeles",  # PST
        "agenda": "User scheduled meeting",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "join_before_host": False,
            "mute_upon_entry": True,
            "waiting_room": True
        }
    }

    response = requests.post(ZOOM_MEETING_URL, headers=headers, data=json.dumps(meeting_payload))
    if response.status_code == 201:
        meeting_info = response.json()
        zoom_details = {
            "topic": meeting_info['topic'],
            "start_time": original_time_format,  # Use the original display format
            "meeting_id": meeting_info['id'],
            "join_url": meeting_info['join_url']
        }
        print("\n✅ Meeting created successfully!")
        print(f"📌 Meeting Name: {zoom_details['topic']}")
        print(f"🕒 Start Time: {zoom_details['start_time']}")
        print(f"🔢 Meeting ID: {zoom_details['meeting_id']}")
        print(f"🔗 Join URL: {zoom_details['join_url']}")
        return zoom_details
    else:
        print("\n❌ Failed to create meeting:", response.status_code)
        print(response.json())
        return None

def open_whatsapp():
    """Open WhatsApp Desktop."""
    try:
        subprocess.Popen(["cmd", "/c", "start whatsapp:"])
        time.sleep(5)  # Allow time for WhatsApp to open
        return True
    except Exception as e:
        print(f"❌ Error opening WhatsApp: {e}")
        return False

def search_and_open_contact(contact):
    """Search for a contact and open their chat in WhatsApp Desktop."""
    print(f"🔍 Searching for contact: {contact}")
    time.sleep(2)
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(1)
    pyautogui.typewrite(contact)
    time.sleep(1)
    pyautogui.press('enter')
    time.sleep(2)
    pyautogui.click(200, 200)

def send_message(message):
    """Send a message to the selected contact."""
    print(f"✉️ Sending message:\n{message}")
    for part in message.split("\n"):
        pyautogui.typewrite(part)
        pyautogui.press('enter')
        time.sleep(1)
    print("✅ Message sent successfully.")

def send_whatsapp_message(contact, meeting_details):
    """Automate sending a WhatsApp message with Zoom meeting details."""
    if open_whatsapp():
        search_and_open_contact(contact)
        message_text = f"""
📅 *Meeting Name:* {meeting_details['topic']}
🕒 *Start Time:* {meeting_details['start_time']}
🔢 *Meeting ID:* {meeting_details['meeting_id']}
🔗 *Join URL:* {meeting_details['join_url']}
        """.strip()
        send_message(message_text)
    else:
        print("❌ Failed to open WhatsApp.")

def zoom_mode():
    """Main function to schedule a meeting and optionally send it via WhatsApp."""
    zoom_meeting_details = schedule_zoom_meeting()
    if zoom_meeting_details:
        audio.speak("Do you want to send the meeting details to someone via WhatsApp?") # Slightly clearer phrasing
        send_confirmation = audio.listen().strip().lower()
        # More robust check for confirmation
        if "yes" in send_confirmation or "yeah" in send_confirmation:
            audio.speak("Provide the WhatsApp contact name to send the Zoom details:")
            contact_name = audio.listen().strip()
            if contact_name: # Check if contact name was actually provided
                send_whatsapp_message(contact_name, zoom_meeting_details)
                # time.sleep(10) # Consider if this sleep is necessary
            else:
                audio.speak("No contact name provided. Skipping WhatsApp message.")
        else:
            audio.speak("Okay, not sending the meeting details via WhatsApp.")
    else:
        audio.speak("Failed to schedule the Zoom meeting.") # Inform user about failure


# gpt_client = openai.OpenAI(api_key = "sk-proj-...") # Removed hardcoded key, initialized above

def get_active_window_title():
    """Returns the title of the currently active window."""
    active_window = gw.getActiveWindow()
    return active_window.title if active_window else None

def wait_for_screen_change(timeout=30):
    """Waits until the user switches from Visual Studio Code."""
    print("🔄 Waiting for user to switch from Visual Studio Code...")
    initial_screen = get_active_window_title()
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
        new_screen = get_active_window_title()
        if new_screen and new_screen != initial_screen:
            print(f"✅ Screen changed from VS Code to: {new_screen}")
            return
    print("⏳ Timeout reached. No screen change detected.")

def capture_screen():
    """Captures the current screen and saves it as an image."""
    screenshot_path = "screen_capture.png"
    screenshot = ImageGrab.grab()
    screenshot.save(screenshot_path)
    return screenshot_path

def encode_image(image_path):
    """Encodes the image as a Base64 string for OpenAI API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analyze_and_complete_code(image_path):
    """Uses OpenAI GPT-4 Vision to extract and complete Python code."""
    # Use the globally initialized gpt_client
    if not gpt_client:
        print("🚨 OpenAI client not initialized.")
        return ""
    try:
        print("🔍 Sending image to OpenAI for analysis...")
        base64_image = encode_image(image_path)

        response = gpt_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Extract any Python code from the image, complete it if needed, and return only the fully completed Python code without additional text.Comment out the non code part"},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract and complete the Python code from this image:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=800
        )

        extracted_code = response.choices[0].message.content.strip()

        # Remove any markdown formatting like ```python
        if "```python" in extracted_code:
            extracted_code = extracted_code.replace("```python", "").replace("```", "").strip()

        print(f"📜 Completed Code Extracted:\n{extracted_code}")
        return extracted_code
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return ""

# def write_to_notepad(code):
#     """Writes completed code to Notepad."""
#     temp_file = os.path.expanduser("~/Desktop/completed_code.txt")

#     with open(temp_file, "w") as file:
#         file.write(code)

#     # Open Notepad with the file
#     subprocess.run(["notepad.exe", temp_file])
#     print("✅ Completed code written to Notepad.")


# Sample code with intended indentation
code_x = """
def is_valid(board, row, col, num):
    for x in range(9):
        if board[row][x] == num:
            return False
    for x in range(9):
        if board[x][col] == num:
            return False
    startRow = row - row % 3
    startCol = col - col % 3
    for i in range(3):
        for j in range(3):
            if board[startRow + i][startCol + j] == num:
                return False
    return True

def solve_sudoku(board):
    for row in range(9):
        for col in range(9):
            if board[row][col] == 0:
                for num in range(1, 10):
                    if is_valid(board, row, col, num):
                        board[row][col] = num
                        if solve_sudoku(board):
                            return True
                        board[row][col] = 0
                return False
    return True

if __name__ == "__main__":
    board = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]
    if solve_sudoku(board):
        print("Solution Found")
    else:
        print("No solution exists")
"""

def write_to_active_window(code):
    """Pastes the given code into the current active window using clipboard paste."""
    audio.speak("Started pasting code.")
    # Copy the code to the clipboard
    pyperclip.copy(code)
    # Wait briefly to ensure the clipboard is updated
    time.sleep(0.5)
    # Simulate Ctrl+V to paste the code
    pyautogui.hotkey("ctrl", "v")
    audio.speak("✅ Code has been pasted into the active window.")


def complete_code_if_incomplete():
    """Analyzes the screen, extracts, and completes the code before writing to Notepad."""
    # wait_for_screen_change(timeout=30) # Commented out as per original logic

    image_path = capture_screen() # Capture screen needs to be called if used

    audio.speak("Captured what's in the image.") # Corrected typo
    # time.sleep(10) # Consider if this sleep is necessary
    audio.speak("Sure, let me generate the solution.")

    completed_code = analyze_and_complete_code(image_path) # Use the captured image path
    # write_to_active_window(code_x) # This writes the hardcoded sudoku, not the analyzed code

    if completed_code:
        audio.speak("Pasting the completed code now.")
        write_to_active_window(completed_code) # Write the code extracted and completed by AI
    else:
        audio.speak("Sorry, I couldn't extract or complete the code from the image.")
        print("📷 No valid Python code detected or OpenAI error occurred.")

def main():
    # time.sleep(10) # Consider if this sleep is necessary

    # zoom_mode() # Commenting out zoom_mode call as per original logic
    # time.sleep(60) # Consider if this sleep is necessary
    audio.speak("I can see that you are in a zoom call. I can also see there is a sudoku solver code written on a white board. Do you need help with anything?") # Corrected typo
    # time.sleep(15) # Consider if this sleep is necessary

    # Listen for user confirmation before proceeding
    user_response = audio.listen().strip().lower()
    if "yes" in user_response or "yeah" in user_response or "sure" in user_response:
        audio.speak("Sure, generating the code.")
        complete_code_if_incomplete() # Call the function that captures, analyzes, and pastes
        # write_to_active_window(code_x) # Remove this line, handled by complete_code_if_incomplete
    else:
        audio.speak("Okay, let me know if you need help later.")


    # complete_code_if_incomplete() # Moved inside the confirmation block
    # audio.speak("wrote code successfully ") # Moved inside complete_code_if_incomplete or removed

if __name__ == "__main__":
    main()
