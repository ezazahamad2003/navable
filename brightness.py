# brightness.py

import os
import math
import audio  # If you need to speak feedback, or skip if not required.

def increase_brightness(value=10):
    """
    Increases screen brightness by `value` percent (default=10).
    """
    cmd = (
        f"powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,[math]::min(100, (Get-WmiObject "
        f"-Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness + {value}))"
    )
    os.system(cmd)
    audio.speak(f"Increasing brightness by {value} percent.")

def decrease_brightness(value=10):
    """
    Decreases screen brightness by `value` percent (default=10).
    """
    cmd = (
        f"powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,[math]::max(0, (Get-WmiObject "
        f"-Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness - {value}))"
    )
    os.system(cmd)
    audio.speak(f"Decreasing brightness by {value} percent.")

def set_brightness(value=50):
    """
    Sets screen brightness to `value` percent (default=50).
    """
    cmd = (
        f"powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,{value})"
    )
    os.system(cmd)
    audio.speak(f"Setting brightness to {value} percent.")

    
def adjust_brightness(change, set_value):
    if change is not None:
        if change > 0:
            print(f"DEBUG: Increasing brightness by {change}")
            increase_brightness(change)
        elif change < 0:
            print(f"DEBUG: Decreasing brightness by {-change}")
            decrease_brightness(-change)
    elif set_value is not None:
        print(f"DEBUG: Setting brightness to {set_value}")
        set_brightness(set_value)
    else:
        audio.speak("I couldn't determine how to adjust the brightness.")
