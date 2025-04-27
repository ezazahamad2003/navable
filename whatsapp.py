# whatsapp.py

import subprocess
import pyautogui
import time

# 1. Import your shared audio module and exit classifier
import audio
from exit import is_exit_command

def open_whatsapp():
    """
    Open WhatsApp Desktop via the Windows 'start' command.
    Assumes WhatsApp is installed from the Microsoft Store on Windows.
    """
    try:
        subprocess.Popen(["cmd", "/c", "start whatsapp:"])  # Opens WhatsApp Desktop
        time.sleep(5)  # Allow time for WhatsApp to open
        return True
    except Exception as e:
        print(f"Error opening WhatsApp: {e}")
        return False

def search_and_open_contact(contact):
    """
    Search for a contact and open their chat in WhatsApp Desktop.
    Uses PyAutoGUI to automate the search and select process.
    """
    print(f"Searching for contact: {contact}")
    time.sleep(2)
    # Open search bar (Ctrl+F)
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(1)
    # Type the contact's name
    pyautogui.typewrite(contact)
    time.sleep(1)
    # Press Enter to select the contact
    pyautogui.press('enter')
    time.sleep(2)
    # Click outside the search bar to ensure focus on the chat window
    pyautogui.click(200, 200)

def send_message(message):
    """
    Send a message to the currently opened WhatsApp chat.
    """
    print(f"Sending message: {message}")
    pyautogui.typewrite(message)
    time.sleep(1)
    pyautogui.press('enter')
    print("Message sent successfully.")

def send_whatsapp_message(contact, message):
    """
    Automate sending a WhatsApp message to a specific contact.
    """
    if open_whatsapp():
        search_and_open_contact(contact)
        send_message(message)
    else:
        print("Failed to open WhatsApp.")

def activate_whatsapp_mode():
    """
    Voice-based flow to send a WhatsApp message:
      - Prompt user (via TTS) for contact name
      - Listen for contact name
      - Prompt user for message
      - Listen for message
      - Automate sending the message
      - Allow user to say 'stop' to exit
    """
    print("\n--- WhatsApp Mode Activated ---")
    # audio.speak("WhatsApp mode activated. Please tell me the contact name you want to message. Say 'stop' at any time to exit.")

    while True:
        # 2. Listen for contact name
        audio.speak("Please say the contact name.")
        contact_name = audio.listen().strip()
        
        # Check for exit command
        if is_exit_command(contact_name):
            audio.speak("Exiting WhatsApp mode. Take care!")
            return
        
        if not contact_name:
            audio.speak("I didn't catch that. Please try again.")
            continue
        
        # Prompt for the message
        audio.speak(f"Contact name is {contact_name}. Now please say your message.")
        message_text = audio.listen().strip()
        
        # Check for exit command
        if is_exit_command(message_text):
            audio.speak("Exiting WhatsApp mode. Take care!")
            return
        
        if not message_text:
            audio.speak("I didn't catch that. Please try again.")
            continue
        
        # 3. Send the message
        audio.speak(f"Sending your message to {contact_name}. Please wait.")
        send_whatsapp_message(contact_name, message_text)
        
        audio.speak(f"Your message to {contact_name} was sent successfully.")
        
        # If you want the mode to end after one message:
        # audio.speak("WhatsApp mode is complete. Let me know if you need anything else.")
        break

    print("--- WhatsApp Mode Finished ---\n")
