import time
import mss
import cv2
import numpy as np
import google.generativeai as genai
from PIL import Image
import io
import audio
import pygetwindow as gw
import easyocr
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os # Import os
from dotenv import load_dotenv # Import dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API
GENAI_API_KEY = os.getenv("GENAI_API_KEY") # Load key from environment variable
if not GENAI_API_KEY:
    raise ValueError("GENAI_API_KEY not found in environment variables.") # Add check
genai.configure(api_key=GENAI_API_KEY)

def capture_active_window():
    """Automatically detects and captures the active window."""
    time.sleep(2)  # Allow time for the screen to update
    active_window = gw.getActiveWindow()
    
    if not active_window:
        audio.speak("\n⚠️ No active window detected! Capturing full screen instead.")
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Default to full-screen capture
            screenshot = sct.grab(monitor)
    else:
        # audio.speak(f"\n🖥️ Capturing active window: {active_window.title}")
        bbox = (active_window.left, active_window.top, active_window.right, active_window.bottom)
        with mss.mss() as sct:
            screenshot = sct.grab(bbox)  # Capture only the active window

    img = np.array(screenshot)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)  # Convert to RGB format
    pil_image = Image.fromarray(img)

    # Save for verification
    pil_image.save("debug_screenshot.png")
    print("\n📷 Screenshot saved as 'debug_screenshot.png'. Open it to verify the correct screen was captured.")

    return pil_image

def generate_and_execute_plot(image_pil):
    """Uses Gemini AI to generate Python plotting code and executes it."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    img_io = io.BytesIO()
    image_pil.save(img_io, format="JPEG")
    img_bytes = img_io.getvalue()
    
    response = model.generate_content(
        contents=[
            {"role": "user", "parts": [
                {"text": "Extract the tabular data from this image and generate Python code using Matplotlib to plot it appropriately. Ensure the code is valid and formatted correctly."},
                {"mime_type": "image/jpeg", "data": img_bytes}
            ]}
        ]
    )
    
    if response and response.text:
        try:
            # audio.speak("\n📊 Generated plot, please wait:")
            print(response.text)
            
            # Extract valid Python code block
            code_match = re.search(r'```python\n(.*?)\n```', response.text, re.DOTALL)
            if code_match:
                python_code = code_match.group(1)
                exec_globals = {}
                exec(python_code, exec_globals)  # Execute the extracted code
            else:
                audio.speak("\n⚠️ No valid Python code block detected in response.")
        except Exception as e:
            audio.speak(f"\n⚠️ Error executing generated code: {e}")
    else:
        audio.speak("\n❌ Failed to generate Python code for plotting.")

def visualize_mod():
    """Automatically detect and analyze the active screen."""
    audio.speak("📸 capturing the screen...")
    screen_img = capture_active_window()  # Take a fresh screenshot
    
    # Step 1: Generate and execute plot code
    generate_and_execute_plot(screen_img)

