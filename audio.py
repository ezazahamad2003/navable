import os
import wave
import tempfile
import pyaudio
import webrtcvad
import numpy as np
from dotenv import load_dotenv
from groq import Groq  # Groq SDK for transcription
from deepgram import DeepgramClient, SpeakOptions # Import Deepgram specifics
import pygame # Import pygame for playback

# Load Environment Variables
load_dotenv()

# --- Groq Initialization (for Transcription) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables.")
# Initialize Groq Client for transcription tasks
groq_client = Groq(api_key=GROQ_API_KEY)
# --- End Groq Initialization ---

# --- Deepgram Initialization (for TTS) ---
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY not found in environment variables.")
# Initialize Deepgram Client globally for TTS tasks
try:
    deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
except Exception as e:
    print(f"🚨 Failed to initialize Deepgram client: {e}")
    raise # Stop execution if Deepgram client fails

# Initialize pygame mixer for playback
pygame.mixer.init()
# --- End Deepgram Initialization ---


def speak(text):
    """Speak the given text using Groq PlayAI-TTS (MP3 handled properly)."""
    print(f"🔊 Attempting to speak via Groq PlayAI-TTS: '{text}'")
    temp_mp3 = None
    temp_wav = None

    try:
        # Generate speech
        response = client.audio.speech.create(
            model="playai-tts",
            voice="Fritz-PlayAI",
            input=text,
            response_format="mp3"
        )
        print("✅ Groq TTS API call successful.")

        # Save MP3 audio temporarily
        temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        response.write_to_file(temp_mp3.name)
        temp_mp3.flush() # Ensure data is written before conversion
        mp3_path = temp_mp3.name
        temp_mp3.close() # Close the file handle before conversion/playback
        print(f"   - MP3 saved to: {mp3_path}")

        # Convert MP3 to WAV
        audio = AudioSegment.from_mp3(mp3_path)
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav_path = temp_wav.name
        audio.export(wav_path, format="wav")
        temp_wav.close() # Close the file handle before playback
        print(f"   - WAV converted and saved to: {wav_path}")

        # Play WAV audio using playsound (blocking)
        print(f"   - Playing audio using playsound: {wav_path}...")
        playsound(wav_path, block=True) # block=True waits for sound to finish
        print("   - Audio playback finished (playsound).")

    except Exception as e:
        # Enhanced error logging
        print(f"❌ Error in speak function: {type(e).__name__} - {e}")
        print("Traceback:")
        print(traceback.format_exc())
    finally:
        # Clean up temp files after playback attempt (or failure)
        print("   - Cleaning up temporary audio files...")
        if temp_mp3 and os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
                print(f"   - Temp file {mp3_path} deleted.")
            except Exception as e:
                print(f"⚠️ Error deleting MP3 {mp3_path}: {e}")
        else:
            if temp_mp3:
                print(f"   - Temp MP3 file {mp3_path} not found.")

        if temp_wav and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
                print(f"   - Temp file {wav_path} deleted.")
            except Exception as e:
                print(f"⚠️ Error deleting WAV {wav_path}: {e}")
        else:
            if temp_wav:
                 print(f"   - Temp WAV file {wav_path} not found.")

    print("--- Exiting speak function ---") # DEBUG

# --- MP3 Playback Function ---
def play_mp3(file_path):
    """
    Plays an MP3 file using pygame.
    """
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        print("🔊 Playing MP3...")

        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        print("🔊 Audio playback complete.")
        pygame.mixer.music.unload() # Unload the file to release it

    except Exception as e:
        print(f"🚨 Error playing MP3: {e}")
# --- End MP3 Playback Function ---


def record_audio(samplerate=16000, channels=1, chunk=320, silence_duration=3):
    """Record audio from mic until silence is detected."""
    print("🎤 Listening... Speak now!")

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=samplerate,
                    input=True,
                    frames_per_buffer=chunk)

    vad = webrtcvad.Vad(0)
    frames = []
    silence_count = 0
    silence_limit = int(silence_duration * samplerate / chunk)

    while True:
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        pcm = np.frombuffer(data, dtype=np.int16)
        if vad.is_speech(pcm.tobytes(), samplerate):
            silence_count = 0
        else:
            silence_count += 1
        if silence_count > silence_limit:
            print("⏹ Silence detected. Stopping.")
            break

    stream.stop_stream()
    stream.close()
    p.terminate()

    if len(frames) == 0:
        print("🚫 No valid audio captured.")
        return None

    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    with wave.open(temp_wav.name, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(samplerate)
        wf.writeframes(b''.join(frames))

    print(f"✅ Audio recorded at: {temp_wav.name}")
    return temp_wav.name


def transcribe_audio(file_path):
    """Send audio to Groq Whisper Large v3 Turbo via SDK and get transcription."""
    # Use the globally initialized Groq client
    if not groq_client:
        print("🚨 Groq client not initialized. Cannot transcribe.")
        return ""

    if not os.path.exists(file_path):
        print(f"❌ Audio file not found: {file_path}")
        return ""
    try:
        print("🧠 Transcribing via Groq Whisper Large v3 Turbo (SDK)...")
        with open(file_path, "rb") as audio_file:
            # Use the global groq_client
            transcription = groq_client.audio.transcriptions.create(
                file=(os.path.basename(file_path), audio_file.read()),
                model="whisper-large-v3-turbo",
                language="en"
            )
        # Ensure transcription object and text attribute exist
        return transcription.text if transcription and hasattr(transcription, 'text') else ""
    except Exception as e:
        print(f"❌ Groq SDK Transcription Error: {e}")
        return ""


def listen():
    """Record audio, transcribe, and return the text."""
    audio_path = record_audio()

    if audio_path is None:
        print("🤷 No speech detected, retrying...")
        return ""

    text = transcribe_audio(audio_path)

    try:
        os.remove(audio_path)
        print(f"🗑 Temp file {audio_path} deleted.")
    except Exception as e:
        print(f"⚠️ Could not delete temp file: {e}")

    if not text or text.isspace():
        print("🤷 No speech detected, retrying...")
        return ""

    cleaned_text = text.strip()
    words = cleaned_text.split()

    if len(words) <= 1:
        print("🤷 Detected too short speech, retrying...")
        return ""

    print(f"🔍 Final Transcription: '{cleaned_text}'")
    return cleaned_text

