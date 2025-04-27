import os
# Allow duplicate OpenMP runtimes
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import time
import mss
import cv2
import numpy as np
from openai import OpenAI # Make sure OpenAI is imported correctly
from PIL import Image
import io
import audio
import pygetwindow as gw
import easyocr
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import matplotlib

from dotenv import load_dotenv

# Set Matplotlib backend for GUI window
matplotlib.use('TkAgg')

# Load environment variables from .env file
load_dotenv()

# Configure Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables.")
# Create the client instance using the Groq endpoint
client = OpenAI( # Use the imported OpenAI class
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)
# Remove the old configuration lines:
# openai.api_key = GROQ_API_KEY  <- Remove this
# openai.api_base = "https://api.groq.com/openai/v1" <- Remove this

MODEL_NAME = "llama3-70b-8192"

def capture_active_window():
    """Capture the active window or full screen."""
    time.sleep(2)
    active_window = gw.getActiveWindow()
    
    if not active_window:
        audio.speak("\n⚠️ No active window detected! Capturing full screen instead.")
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
    else:
        bbox = (active_window.left, active_window.top, active_window.right, active_window.bottom)
        with mss.mss() as sct:
            screenshot = sct.grab(bbox)

    img = np.array(screenshot)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    pil_image = Image.fromarray(img)

    pil_image.save("debug_screenshot.png")
    print("\n📷 Screenshot saved as 'debug_screenshot.png'.")

    return pil_image

def extract_text_from_image(image_pil):
    """Extract text from a PIL image using EasyOCR."""
    print("[INFO] Extracting text from image...")
    reader = easyocr.Reader(['en'], gpu=False)
    image_np = np.array(image_pil)
    results = reader.readtext(image_np, detail=0)
    extracted_text = "\n".join(results)
    print("[INFO] OCR extraction complete.")
    return extracted_text

def generate_and_execute_plot(image_pil):
    """Generate Python plotting code from Groq and execute it."""
    extracted_text = extract_text_from_image(image_pil)

    prompt = f"""
You are a Python expert.

Given the following extracted table/text from an image:

{extracted_text}

Write clean Python code that uses Matplotlib (and optionally Pandas) to plot this data appropriately.

⚡ VERY IMPORTANT:
- All lists or arrays must be of the SAME length.
- If the number of labels (x-axis) and data points (y-axis) do not match, fix it automatically.
- Output ONLY the Python code, inside triple backticks like ```python ... ```.
- Do NOT include any explanations or extra text.
"""

    print("[INFO] Sending prompt to Groq...")
    try:
        # --- Use the client to make the call ---
        response = client.chat.completions.create( # Use client.chat.completions.create
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that writes clean plotting code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        # --- Access the response content correctly ---
        reply_content = response.choices[0].message.content
    except Exception as api_error:
         print(f"[ERROR] Groq API call failed: {api_error}")
         reply_content = response['choices'][0]['message']['content']

    if reply_content:
        try:
            print("\nGenerated Code:\n", reply_content)

            # 🔥 Flexible regex to match ``` or ```python
            code_match = re.search(r'```(?:python)?\n(.*?)```', reply_content, re.DOTALL)
            if code_match:
                python_code = code_match.group(1)
                print("[INFO] Extracted clean code block.")
            else:
                python_code = reply_content.strip()
                print("[WARNING] No triple backticks found. Using full content.")

            # 🔥 Remove accidental "python" text inside code block
            if python_code.strip().splitlines()[0].strip() == "python":
                print("[INFO] Detected and removing leading 'python' text from code block.")
                python_code = "\n".join(python_code.strip().splitlines()[1:])

            # --- AUTO-FIX DATA MISMATCH ---
            if "pd.DataFrame" in python_code and "data =" in python_code:
                print("[INFO] Checking for possible data length mismatches...")
                try:
                    data_block_match = re.search(r"data\s*=\s*{(.*?)}", python_code, re.DOTALL)
                    if data_block_match:
                        data_block = data_block_match.group(1)
                        lists = re.findall(r'\[(.*?)\]', data_block, re.DOTALL)
                        list_lengths = [len(lst.split(',')) for lst in lists]
                        if len(set(list_lengths)) > 1:
                            print("[WARNING] Mismatch detected! Attempting to fix...")
                            min_length = min(list_lengths)
                            new_data_block = ''
                            for lst in lists:
                                items = lst.split(',')
                                items = items[:min_length]
                                new_data_block += '[' + ','.join(items) + '], '
                            new_data_block = new_data_block.rstrip(', ')
                            python_code = re.sub(r"data\s*=\s*{(.*?)}", f"data = {{{new_data_block}}}", python_code, flags=re.DOTALL)
                            print("[INFO] Auto-fix applied.")
                except Exception as fix_error:
                    print(f"[WARNING] Auto-fix failed: {fix_error}")

            # Execute the code safely
            exec_globals = {
                "plt": plt,
                "pd": pd,
                "sns": sns,
                "np": np,
                "__builtins__": __builtins__,
            }

            print("[INFO] Executing generated plotting code...")
            exec(python_code, exec_globals)
            print("[INFO] Code executed.")

            fig = plt.gcf()
            if fig.get_axes():
                print("[INFO] Plot created successfully. Displaying...")
                fig.canvas.manager.set_window_title('📊 Navable - AI Generated Plot')
                plt.tight_layout()
                plt.show()

                fig.savefig('ai_generated_plot.png')
                print("[INFO] Plot saved as 'ai_generated_plot.png'.")
            else:
                print("[WARNING] No axes detected in figure. Nothing to plot.")

        except Exception as e:
            print(f"[ERROR] Error executing generated code: {e}")
            audio.speak(f"⚠️ Error executing generated code: {e}")
    else:
        print("[ERROR] No content received from Groq.")
        audio.speak("❌ Failed to generate code.")

def visualize_mod():
    """Main function to capture screen and visualize."""
    audio.speak("📸 capturing the screen...")
    screen_img = capture_active_window()
    generate_and_execute_plot(screen_img)

