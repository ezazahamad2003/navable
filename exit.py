from groq import Groq
import os
from dotenv import load_dotenv
import string

# Load environment variables
load_dotenv()

# Initialize the Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def is_exit_command(user_input):
    """
    Uses a Groq model to classify if the user input indicates an exit command.

    Parameters:
      - user_input: The user's transcribed text, potentially cleaned.

    Returns:
      True if the intent is classified as "exit", False otherwise.
    """
    # Clean the input for better classification (optional, but can help)
    clean_input = user_input.lower().translate(str.maketrans('', '', string.punctuation)).strip()

    if not clean_input: # Handle empty input after cleaning
        return False

    prompt = f"""
Analyze the user's statement and determine if their primary intent is to stop or exit the current process/application.
Respond with only one word: "exit" or "continue".

User statement: "{clean_input}"
Intent:
"""
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Using a fast model for simple classification
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        intent = response.choices[0].message.content.strip().lower()
        print(f"DEBUG (is_exit_command): Input='{clean_input}', Classified Intent='{intent}'")
        return intent == "exit"

    except Exception as e:
        print(f"❌ Error during exit intent classification: {e}")
        # Fallback: If classification fails, assume not an exit command
        # Or, you could check for simple keywords as a backup:
        # return clean_input in ["stop", "exit", "quit", "goodbye", "bye bye"]
        return False

# Example usage (optional, for testing this file directly)
if __name__ == '__main__':
    test_phrases = ["stop", "exit now", "please continue", "tell me a joke", "goodbye", "quit the application"]
    for phrase in test_phrases:
        print(f"'{phrase}' -> Is exit? {is_exit_command(phrase)}")