import json

import therapy
import audio
import time
import os # Make sure os is imported
import re # Import re for parse_brightness_or_volume
import notepad
import close_active_apps
import whatsapp
import news
import zoom
import brightness

import volume
import google_calendar

import open_file

import visualize



from exit import is_exit_command  # Import our centralized exit classifier

# Set the API key for OpenAI (this is hard-coded; consider using environment variables for security)
from groq import Groq # Make sure Groq is imported
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY")) # Ensure client is initialized

# --- History Management ---
# Change this line
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "conversation_history.json")
MAX_HISTORY_TURNS = 10 # Keep last 10 pairs for context in get_general_response

def load_history(filepath):
    """Loads conversation history from a JSON file."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"WARN: Could not load history file {filepath}: {e}. Starting fresh.")
            return []
    return []

def save_history(filepath, history):
    """Saves conversation history to a JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2) # Use indent for readability
    except IOError as e:
        print(f"ERROR: Could not save history file {filepath}: {e}")
# --- End History Management ---


# Rename function to better reflect its output
def classify_intent_category(user_input):
    """
    Classify the user input into one of the allowed categories.
    """
    prompt = f"""
You are a classification system.
Given the user input, determine the primary category of the request.
Return ONLY the category name, without any explanation or reasoning.

Allowed categories: [
  "therapy", "notepad", "whatsapp", "meeting", "brightness",
  "translate", "volume", "visualize", "close_active_apps", "news",
  "google_calendar", "web-application", "retrive-file",
  "retrive-file", "general"
]

Instructions:
FIRST CHECK FOR CALENDAR CATEGORY:
If the input contains ANY of these indicators, return ONLY "google_calendar":
- Words: calendar, schedule, event, appointment
- Phrases: add to calendar, create event, schedule event
- Context: Google Calendar, calendar event, scheduling
- Time-related: date, time, schedule for

Then check for meeting category:
FIRST CHECK FOR MEETING CATEGORY:
If the input contains ANY of these indicators, return ONLY "meeting":
- Words: meeting, zoom, call, conference, meet, schedule, appointment
- Phrases: set up, organize, plan, arrange
- Context: meeting someone, having a call, joining meetings
- Time-related: calendar, schedule, time, date

Only if it's NOT a meeting request, then check other categories:
- Mental health/emotional support -> "therapy"
- Note-taking/document creation -> "notepad"
   - WhatsApp -> "whatsapp"
   - Screen brightness -> "brightness"
   - Language translation -> "translate"
   - Volume control -> "volume"
   - Data visualization -> "visualize"
   - Music playback -> "spotify"
   - Closing apps -> "close_active_apps"
   - Calendar operations -> "google_calendar"
   - Web browsing -> "web_application"
   - Coding tasks -> "code"
   - File operations -> "retrive-file"
   - AI chat -> "gemini"
   - None of above -> "general"

Example meeting inputs (ALL should return ONLY "meeting"):
- "Can you help me set up a meeting with my friend?"
- "I want to set up a zoom meeting"
- "Schedule a call"
- "Need to meet with someone"
- "Create a video conference"
- "Join the zoom call"
- "Help me organize a meeting"

User Input: {user_input}
Category (return ONLY the single word category name):
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
            top_p=0.95,
            stream=False,
            reasoning_format="hidden"
        )
        
        # Get the raw category and clean it
        category = response.choices[0].message.content.strip().lower()
        
        # Direct keyword matching for common categories
        user_input_lower = user_input.lower()
        
        # Close apps keywords (check before LLM result)
        if "close" in user_input_lower and any(word in user_input_lower for word in ['app', 'application', 'window']):
             return "close_active_apps"
        # Calendar keywords
        if any(word in user_input_lower for word in ['calendar', 'schedule', 'appointment']):
            return "google_calendar"
        # Volume keywords
        if any(word in user_input_lower for word in ['volume', 'sound', 'audio level']):
            return "volume"
        # Brightness keywords
        if any(word in user_input_lower for word in ['brightness', 'screen', 'dim']):
            return "brightness"
        # Meeting keywords
        if any(word in user_input_lower for word in ['zoom', 'meeting', 'conference']):
            return "meeting"
        # File retrieval keywords
        if any(verb in user_input_lower for verb in ['retrieve', 'open', 'find', 'get']) and \
           any(noun in user_input_lower for noun in ['file', 'document', 'doc']):
            return "retrive-file"
        # Visualize keywords
        if 'visualize' in user_input_lower or 'plot' in user_input_lower or 'graph' in user_input_lower:
             return "visualize"
        # News keywords
        if 'news' in user_input_lower or 'headlines' in user_input_lower or 'latest events' in user_input_lower:
             return "news"
        # --- Add this block for notepad ---
        if 'notepad' in user_input_lower or 'note' in user_input_lower or 'write down' in user_input_lower:
             return "notepad"
        # --- End of added block ---
        # WhatsApp keywords
        if 'whatsapp' in user_input_lower or 'send message' in user_input_lower or 'text' in user_input_lower:
            return "whatsapp"



        # If no direct matches, use the LLM classification (if it wasn't empty)
        if category: # Only proceed if LLM gave a non-empty category
            valid_categories = [
                "therapy", "notepad", "whatsapp", "meeting", "brightness", # Ensure 'notepad' is here
                "translate", "volume", "visualize", "spotify", "close_active_apps",
                "google_calendar", "web-application", "code",
                "retrive-file", "general", "gemini", "news"
            ]
            # Remove duplicates
            valid_categories = list(dict.fromkeys(valid_categories))

            if category not in valid_categories:
                print(f"WARN: Unexpected category classification '{category}', defaulting to 'general'.")
                category = "general"
        else:
             # Handle empty LLM response explicitly
             # Check keywords again here just in case, before defaulting
             if 'news' in user_input_lower or 'headlines' in user_input_lower:
                 category = "news"
             elif 'notepad' in user_input_lower or 'note' in user_input_lower or 'write down' in user_input_lower: # Check notepad keywords
                 category = "notepad"
             else:
                 print(f"WARN: LLM classification returned empty and no keywords matched, defaulting to 'general'.")
                 category = "general"


        print(f"DEBUG: classify_intent_category -> {category}")
        return category

    except Exception as e:
        print(f"ERROR in classify_intent_category: {e}")
        return "general"  # Default to general in case of error


def parse_brightness_or_volume(user_input):
    """
    Parses user input for numeric values (e.g., "set brightness to 50%") 
    and determines increase or decrease actions.
    Returns (change_value, set_value).
    Example:
      "increase brightness by 10" -> (10, None)
      "decrease volume" -> (-10, None)
      "set brightness to 70" -> (None, 70)
    """
    user_input = user_input.lower()
    change_value = None
    set_value = None

    if "increase" in user_input or "up" in user_input:
        match = re.search(r'\d+', user_input)
        change_value = int(match.group()) if match else 10
    elif "decrease" in user_input or "down" in user_input:
        match = re.search(r'\d+', user_input)
        change_value = -int(match.group()) if match else -10
    elif "set" in user_input:
        match = re.search(r'\d+', user_input)
        set_value = int(match.group()) if match else 50

    print(f"DEBUG: parse_brightness_or_volume returning change={change_value}, set={set_value}")
    return change_value, set_value

# Update get_general_response to accept history
def get_general_response(user_input, history):
    """
    Generates a response using the Groq model, considering conversation history.

    Args:
        user_input (str): The current input from the user.
        history (list): A list of message dictionaries representing the conversation history
                        (in {"role": ..., "content": ...} format).

    Returns:
        str: The generated response from the assistant.
    """
    # Limit history to the last N turns (N user + N assistant messages) for context
    limited_history_for_context = history[-(MAX_HISTORY_TURNS * 2):]

    # Construct the messages list for the API call
    messages = [
        {"role": "system", "content": (
            "You are AERO, you are almost like a human friend. "
            "You speak in a calm and nice and keep your answers short and brief, "
            "unless the topic really calls for a longer discussion."
        )},
        # Add the limited history
        *limited_history_for_context,
        # Add the current user input
        {"role": "user", "content": user_input}
    ]

    try:
        # Use the Groq client and the specified model
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Or your preferred model
            messages=messages, # Pass the constructed messages list
            max_tokens=150,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR in get_general_response: {e}") # Added print for error
        answer = f"Sorry, I encountered an error trying to respond: {e}"
    return answer


def main():
    audio.speak("Hey, how's it going?")
    # Load history from JSON file at the start
    conversation_history = load_history(HISTORY_FILE)

    while True:
        # 1. Capture user input
        user_input = audio.listen().strip()
        if not user_input:
            continue

        # Prepare user message dictionary
        user_message = {"role": "user", "content": user_input}
        # Append user input to the history list in memory
        conversation_history.append(user_message)

        # 2. Check exit condition FIRST
        if is_exit_command(user_input):
            response_text = "Exiting the application. Goodbye!"
            audio.speak(response_text)
            # Append final assistant response before saving and exiting
            assistant_message = {"role": "assistant", "content": response_text}
            conversation_history.append(assistant_message)
            save_history(HISTORY_FILE, conversation_history) # Save history before breaking
            break # Exit the loop

        # 3. Classify into a category string ONLY IF NOT an exit command
        category = classify_intent_category(user_input)

        print(f"DEBUG: category={category}")

        # --- Initialize response_text for logging ---
        response_text = None

        # 4. Route the request based only on the category
        if category == "therapy":
            response_text = "Therapy action initiated." # Set for logging
            pass # Therapy handles its own flow, no response_text needed here

        elif category == "notepad":
            notepad.open_and_write_notepad()
            response_text = "Notepad action initiated." # Set for logging

        elif category == "whatsapp":
            whatsapp.activate_whatsapp_mode()
            response_text = "WhatsApp mode activated." # Set for logging

        elif category == "meeting":
            zoom.zoom_mode()
            response_text = "Zoom mode activated." # Set for logging

        elif category == "google_calendar":
            google_calendar.prompt_and_create_calendar_event()

        #elif category == "google_calendar":
            # create_calendar_event likely gives feedback, set generic log
          #  google_calendar.create_calendar_event_from_input(user_input)
           # response_text = "Google Calendar action attempted."

        elif category == "news":
            # News mode handles its own interaction and speaking
            response_text = "News mode activated." # For logging purposes
            news.news_mode() # Call the news mode function
            response_text = None # News mode handles its own flow, don't save generic message

        elif category == "brightness":
            change, set_val = parse_brightness_or_volume(user_input)
            brightness.adjust_brightness(change, set_val) # Module handles speaking
            # Set more descriptive log text
            if change is not None:
                response_text = f"Brightness change requested: {change}%"
            elif set_val is not None:
                response_text = f"Brightness set requested: {set_val}%"
            else:
                response_text = "Brightness adjustment attempted (no specific value parsed)."

        elif category == "close_active_apps":
             close_active_apps.close_active_apps() # Module handles speaking/feedback
             response_text = "Attempted to close active applications." # For logging

        elif category =="visualize":
            visualize.visualize_mod()

        elif category == "retrive-file":
            open_file.retrive_file()

        elif category == "volume":
            mute_toggle = "mute" in user_input or "silent" in user_input
            change, set_val = parse_brightness_or_volume(user_input)
            volume.adjust_volume(change, set_val, mute_toggle) # Module handles speaking
            # Set more descriptive log text
            if mute_toggle:
                response_text = "Volume mute toggled."
            elif change is not None:
                response_text = f"Volume change requested: {change}%"
            elif set_val is not None:
                response_text = f"Volume set requested: {set_val}%"
            else:
                 response_text = "Volume adjustment attempted (no specific value parsed)."

        # --- Add this else block to handle general category ---
        else: # Handles "general" or any other unhandled valid category
            print("INFO: Handling as general query.")
            # Pass the current history (loaded and appended to) to get the response
            response_text = get_general_response(user_input, conversation_history)
            audio.speak(response_text) # Speak the general response
        # --- End of added else block ---


        # --- Save history ONLY if NOT in therapy mode AND response exists ---
        # (This part should now correctly save history for 'general' category too)
        if category != "therapy" and response_text is not None:
            assistant_message = {"role": "assistant", "content": response_text}
            conversation_history.append(assistant_message)
            # Limit history size in memory *before* saving if desired
            # conversation_history = conversation_history[-(MAX_HISTORY_TURNS * 2 + 10):] # Keep slightly more than context window
            save_history(HISTORY_FILE, conversation_history)
        elif category != "therapy" and response_text is None:
             # This condition might now only be met if a module fails to set response_text
             print(f"INFO: No assistant response generated or logged for category '{category}'. History not saved for this turn.")


if __name__ == "__main__":
    main()