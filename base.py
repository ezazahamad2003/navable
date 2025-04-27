import json
import therapy
import audio
import time
import os # Make sure os is imported
import re # Import re for parse_brightness_or_volume
import notepad
import close_active_apps
import whatsapp
import zoom
import brightness
# import gemini
import volume
# import calendar
# import spotify
# import web_application
import open_file
# import code
# import translate
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
HISTORY_FILE = r"c:\Users\ezaza\Desktop\navable\conversation_history.json"
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

    Parameters:
      - user_input: The transcribed user input.

    Returns:
      The classified category as a string (e.g., "therapy", "notepad", "general").
    """
    prompt = f"""
You are a classification system.
Given the user input, determine the primary category of the request.

Allowed categories: [
  "therapy",
  "notepad",
  "whatsapp",
  "meeting",
  "brightness",
  "translate",
  "volume",
  "visualize",
  "spotify",
  "close_active_apps",
  "calendar",
  "web-application",
  "code",
  "web_application",
  "retrive-file"
  "general"
  "gemini",
]

Instructions:
1. Analyze the user's intent.
2. If the intent clearly relates to therapy or mental well-being, respond with "therapy".
3. If the intent clearly relates to taking notes or using a notepad, respond with "notepad".
4. For all other intents, respond with "general".
5. Respond with ONLY the single category word ("general", "notepad", or "therapy"). No extra text or formatting.

User input:
{user_input}

Category:
"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192", # Using a smaller, faster Groq model for classification
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10, # Reduced max_tokens as we expect a single word
            temperature=0 # Keep temperature low for classification
        )
        # Get the raw category string directly
        category = response.choices[0].message.content.strip().lower()

        # Basic validation to ensure it's one of the expected categories
        if category not in ["general", "notepad", "therapy"]:
            print(f"WARN: Unexpected category classification '{category}', defaulting to 'general'.")
            category = "general" # Default to general if unexpected response

        print(f"DEBUG: classify_intent_category -> {category}")
        return category

    except Exception as e:
        print(f"ERROR in classify_intent_category: {e}")
        return "general" # Default to general in case of error


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
    audio.speak("Hey zaz, how's it going?")
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

        # 2. Check exit condition
        if is_exit_command(user_input):
            response_text = "Exiting the application. Goodbye!"
            audio.speak(response_text)
            # Append final assistant response before saving and exiting
            assistant_message = {"role": "assistant", "content": response_text}
            conversation_history.append(assistant_message)
            save_history(HISTORY_FILE, conversation_history) # Save history before breaking
            break

        # 3. Classify into a category string
        category = classify_intent_category(user_input) # Call the renamed function

        print(f"DEBUG: category={category}")

        # --- Initialize response_text for logging ---
        response_text = None # Default to None, will be set by handlers

        # 4. Route the request based only on the category
        if category == "therapy":
            # Therapy mode runs independently and does NOT update main history JSON
            print("INFO: Entering therapy mode. History will not be saved to main log.")
            therapy.activate_therapy_mode()

        elif category == "notepad":
            # Notepad likely doesn't need history context, but we log the interaction
            notepad.open_and_write_notepad()

        elif category == "whatsapp":
            whatsapp.activate_whatsapp_mode()

        # --- Add example logging for other categories ---
        elif category == "meeting":
            zoom.zoom_mode()
            response_text = "Zoom mode activated." # Example response
            audio.speak(response_text)

        # ... handle other categories similarly, setting response_text ...
        # Example for brightness (assuming adjust_brightness doesn't speak)
        elif category == "brightness":
            # Placeholder for action parsing if needed
            action = "set" # Example action
            if action in ["increase", "decrease", "set"]:
                change, set_val = parse_brightness_or_volume(user_input)
                brightness.adjust_brightness(change, set_val)
                response_text = f"Brightness adjusted."
            else:
                brightness.adjust_brightness(None, None)
                response_text = "Brightness adjustment initiated."
            audio.speak(response_text) # Speak the outcome

        # Example for gemini (assuming gemini_mode handles its own speaking)
        elif category == "gemini":
             audio.speak("Hey! whats up ?")
             gemini.gemini_mode()
             # Gemini mode handles its own interaction, maybe log a generic message
             response_text = "Gemini mode finished." # Or None if it shouldn't be logged
        
        elif category == "volume":
            # Similar logic for volume
            mute_toggle = "mute" in user_input or "silent" in user_input
            if action in ["increase", "decrease", "set"]:
                change, set_val = parse_brightness_or_volume(user_input)
                volume.adjust_volume(change, set_val, mute_toggle)
            else:
                volume.adjust_volume(None, None, mute_toggle)
        # --- General Category ---
        else: # category == "general" or unhandled
            # Pass the current history (loaded and appended to) to get the response
            response_text = get_general_response(user_input, conversation_history)
            audio.speak(response_text)
            # Assistant response for 'general' is handled below

        # --- Save history ONLY if NOT in therapy mode AND response exists ---
        if category != "therapy" and response_text is not None:
            assistant_message = {"role": "assistant", "content": response_text}
            conversation_history.append(assistant_message)
            # Limit history size in memory *before* saving if desired
            # conversation_history = conversation_history[-(MAX_HISTORY_TURNS * 2 + 10):] # Keep slightly more than context window
            save_history(HISTORY_FILE, conversation_history)
        elif category != "therapy" and response_text is None:
             print(f"INFO: No assistant response generated or logged for category '{category}'. History not saved for this turn.")


if __name__ == "__main__":
    main()