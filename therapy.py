from groq import Groq
import audio
import string  # For cleaning punctuation
import random  # For random greetings
from exit import is_exit_command
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_therapy_response(user_input):
    """
    Generate a humanistic, poetic therapy response from AI using a voice-adapted prompt.

    Parameters:
      - user_input: The transcribed user input.

    Returns:
      The generated therapist response.
    """
    prompt = f"""
You are a thoughtful, warm-hearted therapist who speaks with gentle wisdom and soulful insight, like a close friend.
Your tone is calm, empathetic, and lightly humorous when appropriate.
Keep your replies brief and to the point. Speak with warmth and kindness, but avoid long elaborations unless truly necessary.
Notice the emotion behind the user's words and respond in a way that feels naturally supportive of their emotional state.

User: {user_input}
Therapist:
"""  # UPDATED Prompt

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0
    )
    return response.choices[0].message.content.strip()

def activate_therapy_mode():
    """
    Starts the AI therapy session using voice interaction.

    Listens for the user's voice input, processes it to generate an AI response,
    and speaks out the response using shared audio functions.

    When the Groq classifier indicates an exit command, the therapy loop terminates
    and control returns to the main application.
    """
    print("\nGen Z AI Therapist Activated (Voice Mode)")
    greetings = [
        "Alright, let's chat. Whenever you want to stop, just say 'stop'.",
        "I'm here. Talk to me whenever you're ready. Say 'stop' when you feel done.",
        "Let's have a heart-to-heart. Just say 'stop' when you want to take a break."
    ]  # UPDATED Randomized greetings
    audio.speak(random.choice(greetings))

    while True:
        user_input = audio.listen().strip()
        if not user_input:
            continue  # If transcription fails or is empty, try again

        # Clean the user input: remove punctuation and extra whitespace
        clean_input = user_input.lower().translate(str.maketrans('', '', string.punctuation)).strip()

        # Use Groq to check if the user wants to exit therapy mode.
        if is_exit_command(clean_input):
            audio.speak("Alright, I'm always here if you need to talk. Take care.")
            break  # Exit therapy mode and return to base.py

        # Generate the AI therapy response and speak it.
        ai_response = get_therapy_response(user_input)
        audio.speak(ai_response)
