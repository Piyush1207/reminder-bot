import platform
import subprocess
import time

def speak(text):
    """Simple cross-platform TTS with fallback to print"""
    print(f"\n🔊 BOT SAYS: {text}\n")
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Try Windows SAPI first
            try:
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(text)
                return
            except:
                # Fallback to PowerShell
                subprocess.run(['powershell', '-Command', 
                               f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'],
                              capture_output=True)
        elif system == "Darwin":  # macOS
            subprocess.run(['say', text], check=False)
        else:  # Linux
            subprocess.run(['espeak', text], check=False)
    except Exception as e:
        print(f"  (Speech failed: {e})")
        print(f"  Text was: {text}")
