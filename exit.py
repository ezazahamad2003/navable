import re
import string
from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def is_exit_command(user_input):
    """
    Uses a Groq model to classify if the user input indicates an intent to exit *this specific application*.

    Parameters:
      - user_input: The user's transcribed text.

    Returns:
      True if the intent is classified as "exit", False otherwise.
    """
    clean_input = user_input.lower().translate(str.maketrans('', '', string.punctuation)).strip()

    if not clean_input:
        return False

    # Improved prompt to differentiate exiting this app vs closing others
    prompt = f"""
Analyze the user's statement and determine if their primary intent is specifically to stop or exit **the current assistant application (AERO)**.
Distinguish this from requests to close *other* applications or windows.

Respond with only one word:
- "exit": If the user wants to stop or quit the current assistant application.
- "continue": If the user wants to continue interacting or is asking to close *other* applications/windows.

Examples:
- "stop" -> exit
- "exit now" -> exit
- "goodbye" -> exit
- "close all apps" -> continue
- "can you close the browser?" -> continue
- "shut down the program" -> exit
- "tell me a joke" -> continue

User statement: "{clean_input}"
Intent (exit/continue):
"""
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        intent = response.choices[0].message.content.strip().lower()
        # Basic validation in case the model returns something unexpected
        if intent not in ["exit", "continue"]:
             print(f"WARN (is_exit_command): Unexpected LLM response '{intent}'. Defaulting to 'continue'.")
             intent = "continue"

        print(f"DEBUG (is_exit_command): Input='{clean_input}', Classified Intent='{intent}'")
        return intent == "exit"

    except Exception as e:
        print(f"❌ Error during exit intent classification: {e}")
        # Fallback: More robust keyword check as backup
        exit_keywords = ["exit", "quit", "goodbye", "bye bye", "turn off", "shut down"]
        # Check for specific exit keywords, avoiding "close"
        if any(re.search(rf"\b{re.escape(keyword)}\b", clean_input) for keyword in exit_keywords):
             print("DEBUG (is_exit_command): Fallback keyword match found -> exit")
             return True
        print("DEBUG (is_exit_command): Fallback -> continue")
        return False

# Example usage (optional, for testing this file directly)
if __name__ == '__main__':
    test_phrases = ["stop", "exit now", "please continue", "tell me a joke", "goodbye", "quit the application"]
    for phrase in test_phrases:
        print(f"'{phrase}' -> Is exit? {is_exit_command(phrase)}")