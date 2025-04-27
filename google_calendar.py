import os
import re
import webbrowser
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import audio  # Assuming your audio.py is available

# Google Calendar API Scope
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Extended number mapping
NUMBER_MAPPING = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "twenty-one": "21", "twenty-two": "22",
    "twenty-three": "23", "twenty-four": "24", "twenty-five": "25", 
    "twenty-six": "26", "twenty-seven": "27", "twenty-eight": "28", 
    "twenty-nine": "29", "thirty": "30", "thirty-one": "31"
}

def preprocess_text(natural_text):
    """
    Normalize spoken numbers, fix common speech errors, and normalize time formats.
    """
    natural_text = natural_text.lower()

    # Fix common mistranscription errors
    natural_text = natural_text.replace("add even", "add event")
    natural_text = natural_text.replace("even that", "event that")
    natural_text = natural_text.replace("fif", "five")  # Fix 'fif' error

    # Fix a.m. and p.m. to am and pm (remove dots)
    natural_text = natural_text.replace("a.m.", "am")
    natural_text = natural_text.replace("p.m.", "pm")

    # Replace number words with digits
    for word, digit in NUMBER_MAPPING.items():
        natural_text = re.sub(rf"\b{word}\b", digit, natural_text, flags=re.IGNORECASE)

    # Normalize time formats like '5PM' -> '5:00 PM'
    natural_text = re.sub(r"(\d{1,2})(am|pm)", r"\1:00 \2", natural_text)

    return natural_text

def authenticate_google_calendar():
    creds = None
    token_path = "token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid or not creds.refresh_token:
            os.remove(token_path)
            creds = None

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("calendar", "v3", credentials=creds)

def extract_event_details(natural_text):
    """
    Extracts event details such as title, date, start time, and end time from natural language text.
    """
    try:
        # Preprocess
        natural_text = preprocess_text(natural_text)

        # --- Title extraction ---
        # Smarter title extraction: allow optional starting "a"
        title_match = re.search(r"(?:schedule|hold|create|set up|add)?(?:\s*a\s*)?([\w\s]+?)(?:\s*on|\s*for|\s*at|\s*from|$)", natural_text, re.IGNORECASE)
        title = title_match.group(1).strip().capitalize() if title_match else "Event"

        # --- Date extraction ---
        date_match = re.search(r"(?:on|for)\s+(.+?)\s+(?:from|at)", natural_text, re.IGNORECASE)
        raw_date = date_match.group(1).strip() if date_match else None


        year = datetime.now().year  # Default year
        if raw_date:
                # 🛠 Fix: remove "th", "st", "nd", "rd"
                raw_date = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', raw_date, flags=re.IGNORECASE)
                
                # Handle optional year if user says it
                year_match = re.search(r"(19|20)\d{2}", raw_date)
                if year_match:
                    year = int(year_match.group(0))
                    raw_date = raw_date.replace(str(year), "").strip()
                else:
                    year = datetime.now().year

                # ✨ Detect if format is "28 April" (day first) and flip to "April 28"
                tokens = raw_date.split()
                if tokens and tokens[0].isdigit():
                    # Example: ['28', 'April']
                    raw_date = f"{tokens[1]} {tokens[0]}"  # Flip: Month Day

                # Now try parsing
                try:
                    date = datetime.strptime(raw_date, "%B %d").replace(year=year).strftime("%Y-%m-%d")
                except ValueError:
                    date = datetime.strptime(raw_date, "%b %d").replace(year=year).strftime("%Y-%m-%d")
        else:
            date = None


        # Extract times
        time_match = re.search(r"from (\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:to\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)))?",natural_text, re.IGNORECASE)

        if time_match:
            start_time = time_match.group(1).strip()
            end_time = time_match.group(4).strip() if time_match.group(4) else None
        else:
            start_time, end_time = None, None

        # Convert times to 24-hour
        start_time_24 = datetime.strptime(start_time, "%I:%M %p").strftime("%H:%M") if start_time else None
        if end_time:
            end_time_24 = datetime.strptime(end_time, "%I:%M %p").strftime("%H:%M")
        elif start_time:
            # Auto-add 1 hour if no end time
            start_dt = datetime.strptime(start_time, "%I:%M %p")
            end_dt = start_dt + timedelta(hours=1)
            end_time_24 = end_dt.strftime("%H:%M")
        else:
            end_time_24 = None

        if not title or not date or not start_time_24 or not end_time_24:
            raise ValueError("Incomplete event details extracted.")

        return {
            "title": title,
            "date": date,
            "start_time": start_time_24,
            "end_time": end_time_24,
        }

    except Exception as e:
        print(f"❌ Error extracting event details: {e}")
        return None

def create_calendar_event(event_details):
    try:
        service = authenticate_google_calendar()
        event = {
            "summary": event_details["title"],
            "description": f"Created via AI Assistant: {event_details['title']}",
            "start": {
                "dateTime": f"{event_details['date']}T{event_details['start_time']}:00",
                "timeZone": "America/Los_Angeles",
            },
            "end": {
                "dateTime": f"{event_details['date']}T{event_details['end_time']}:00",
                "timeZone": "America/Los_Angeles",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 30}],
            },
        }

        created_event = service.events().insert(calendarId="primary", body=event).execute()
        print(f"✅ Event created successfully: {created_event.get('htmlLink')}")
        audio.speak(f"Your event '{event_details['title']}' has been created successfully.")
        webbrowser.open(created_event.get('htmlLink'))

    except HttpError as error:
        print(f"❌ An error occurred: {error}")
        audio.speak("An error occurred while creating the event. Please try again.")

def create_calendar_event_from_input(event_input):
    audio.speak("Processing your request.")
    event_details = extract_event_details(event_input)

    if not event_details:
        audio.speak("Failed to extract event details. Please try again.")
    else:
        create_calendar_event(event_details)

def prompt_and_create_calendar_event():
    """
    Ask the user for event details via voice, listen, then create the event.
    """
    try:
        audio.speak("Sure, what event would you like to add?")
        user_input = audio.listen().strip()
        if user_input:
            create_calendar_event_from_input(user_input)
        else:
            audio.speak("I did not catch any event details. Please try again.")
    except Exception as e:
        print(f"❌ Error in prompt_and_create_calendar_event: {e}")
        audio.speak("Something went wrong while adding your event.")
