import os
import subprocess
import tempfile
from groq import Groq
import audio
from dotenv import load_dotenv # Import load_dotenv

# --- Load API Key Securely ---
load_dotenv() # Load variables from .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    # Handle the case where the key is missing
    # Option 1: Raise an error
    raise ValueError("GROQ_API_KEY not found in environment variables. Please ensure it's set in your .env file.")
    # Option 2: Print a warning and potentially disable functionality (less ideal for core features)
    # print("WARN: GROQ_API_KEY not found. Notepad generation might fail.")
    # client = None # Or handle appropriately later

# Initialize the Groq client for notepad tasks using the loaded key
if GROQ_API_KEY: # Only initialize if the key was found
    client = Groq(api_key=GROQ_API_KEY)
else:
    # If you chose Option 2 above, handle the missing client here
    # For Option 1 (raising error), this 'else' is not strictly needed
    # but good practice if you might change the error handling later.
    client = None
# --- End API Key Loading ---


def generate_notepad_content(topic):
    """
    Uses Groq to generate a well-structured and engaging piece of text on the given topic.

    Parameters:
      - topic: A string representing the topic.

    Returns:
      The generated content as a string or None if client is not initialized.
    """
    # Add a check if the client was initialized successfully
    if not client:
        print("ERROR: Groq client not initialized due to missing API key.")
        return "Error: Could not generate content because the API key is missing." # Return an error message

    prompt = f"""
You are a creative and knowledgeable writer. Generate a detailed, informative, and engaging article about:
{topic}

Write in a clear and concise manner, suitable for a notepad summary.
"""
    try: # Add try...except block for API calls
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        return content
    except Exception as e:
        print(f"ERROR: Failed to generate notepad content via Groq: {e}")
        return f"Error: Failed to generate content. API Error: {e}" # Return an error message


def open_and_write_notepad():
    """
    Activates the notepad agent:
      - Announces via audio that notepad mode is active.
      - Listens for a voice command.
          * If the command contains "close notepad", it closes the Notepad window.
          * Otherwise, it treats the command as a writing prompt, generates text via Groq,
            writes the text to a temporary file, and opens it in Notepad.
    """
    # Announce that the notepad agent is active
    audio.speak("Hey, notepad agent is active. What would you like me to write?")
    
    # Listen for a voice command
    command = audio.listen().strip()
    if not command:
        audio.speak("I did not catch that. Please try again.")
        return

    # If the command includes a close instruction, close Notepad
    if "close notepad" in command.lower():
        audio.speak("Closing notepad.")
        os.system("taskkill /f /im notepad.exe")
        return

    # Otherwise, treat the command as a writing prompt
    audio.speak("Generating your note. Please wait.")
    content = generate_notepad_content(command)

    # Check if content generation failed (e.g., due to missing API key)
    if content is None or content.startswith("Error:"):
        audio.speak(content or "Sorry, I couldn't generate the note.") # Speak the error or a default message
        return # Stop execution if content generation failed

    # Write the generated content to a temporary text file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
    temp_file.write(content)
    temp_file.close()

    audio.speak("Your note is ready. Opening Notepad.")
    # Open Notepad with the temporary file
    subprocess.Popen(["notepad.exe", temp_file.name])
