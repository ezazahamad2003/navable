import audio  # for TTS feedback
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

def get_volume_interface():
    """Obtain the system's audio endpoint volume interface."""
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    return volume

def get_current_volume():
    """Returns the current master volume as a scalar between 0.0 and 1.0."""
    volume = get_volume_interface()
    return volume.GetMasterVolumeLevelScalar()

def increase_volume(step=0.1):
    """
    Increases volume by the given step (as a fraction of 1, e.g. 0.1 for 10%).
    """
    volume = get_volume_interface()
    current = volume.GetMasterVolumeLevelScalar()
    new_volume = min(current + step, 1.0)
    volume.SetMasterVolumeLevelScalar(new_volume, None)
    audio.speak(f"Increasing volume by {int(step * 100)} percent.")

def decrease_volume(step=0.1):
    """
    Decreases volume by the given step (as a fraction of 1, e.g. 0.1 for 10%).
    """
    volume = get_volume_interface()
    current = volume.GetMasterVolumeLevelScalar()
    new_volume = max(current - step, 0.0)
    volume.SetMasterVolumeLevelScalar(new_volume, None)
    audio.speak(f"Decreasing volume by {int(step * 100)} percent.")

def set_volume(value=50):
    """
    Sets volume to the given percentage (0 to 100).
    """
    scalar = value / 100.0
    volume = get_volume_interface()
    volume.SetMasterVolumeLevelScalar(scalar, None)
    audio.speak(f"Setting volume to {value} percent.")

def mute():
    """
    Mutes the system volume.
    """
    volume = get_volume_interface()
    volume.SetMute(1, None)
    audio.speak("Muting volume.")

def unmute():
    """
    Unmutes the system volume.
    """
    volume = get_volume_interface()
    volume.SetMute(0, None)
    audio.speak("Unmuting volume.")

def adjust_volume(change, set_value, mute_toggle):
    """
    Adjusts volume based on the parsed command:
      - If mute_toggle is True, mutes the system.
      - If a change value is provided, increases (if positive) or decreases (if negative) volume.
      - If a set_value is provided, sets the volume to that specific value.
    
    The change value is expected to be an integer percentage (e.g., 10 for 10% increase or -10 for 10% decrease).
    """
    if mute_toggle:
        mute()
    else:
        if change is not None:
            # Convert the change percentage to a fraction (e.g., 10 -> 0.10)
            step_fraction = abs(change) / 100.0
            if change > 0:
                increase_volume(step_fraction)
            elif change < 0:
                decrease_volume(step_fraction)
        elif set_value is not None:
            set_volume(set_value)
        else:
            audio.speak("I couldn't determine how to adjust the volume.")
