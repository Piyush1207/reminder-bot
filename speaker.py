"""
Cross-platform Text-to-Speech

Priority order:
  Windows  -> Windows SAPI (win32com)
  macOS    -> 'say' command (built-in)
  Linux    -> pyttsx3 -> espeak (fallback)

Falls back to printing if nothing works.
"""
import sys
import subprocess
import threading
import time


def _make_engine():
    """Return a (speak_fn, label) pair for the current platform."""

    # ── Windows ───────────────────────────────────────────────────────────────
    if sys.platform == "win32":
        try:
            import win32com.client
            sapi = win32com.client.Dispatch("SAPI.SpVoice")
            sapi.Rate = 0
            sapi.Volume = 100
            print("✅ TTS: Windows SAPI ready")

            def _speak(text):
                try:
                    sapi.Speak(text)
                    time.sleep(0.2)
                except Exception as e:
                    print(f"❌ SAPI error: {e}")

            return _speak, "SAPI"
        except Exception as e:
            print(f"⚠️  SAPI unavailable ({e}), trying pyttsx3...")

    # ── macOS ─────────────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        def _speak(text):
            try:
                subprocess.run(["say", text], check=True)
            except Exception as e:
                print(f"❌ 'say' error: {e}")

        print("✅ TTS: macOS 'say' ready")
        return _speak, "say"

    # ── Linux / pyttsx3 (cross-platform fallback) ─────────────────────────────
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        engine.setProperty("volume", 1.0)
        print("✅ TTS: pyttsx3 ready")

        # pyttsx3 is not thread-safe; serialise calls with a lock
        _lock = threading.Lock()

        def _speak(text):
            with _lock:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"❌ pyttsx3 error: {e}")

        return _speak, "pyttsx3"
    except Exception as e:
        print(f"⚠️  pyttsx3 unavailable ({e}), trying espeak...")

    # ── Linux / espeak (last resort) ──────────────────────────────────────────
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(["espeak", "--version"],
                           capture_output=True, check=True)
            print("✅ TTS: espeak ready")
            
            def _speak(text):
                try:
                    subprocess.run(["espeak", text], check=True)
                except Exception as e:
                    print(f"❌ espeak error: {e}")
            
            return _speak, "espeak"
        except Exception:
            pass
    
    # ── Print-only fallback ───────────────────────────────────────────────────
    print("⚠️  No TTS engine found. Speech will be printed only.")
    
    def _speak(text):
        pass  # already printed by the speak() wrapper below
    
    return _speak, "print"


_engine_fn, _engine_name = _make_engine()


def speak(text: str):
    """Speak text aloud (and always print it too)."""
    if not text:
        return
    print(f"🔊 {text}")
    _engine_fn(text)


# Alias kept for scheduler.py compatibility
def speak_sync(text: str):
    speak(text)


if __name__ == "__main__":
    speak("Hello! The reminder bot text-to-speech is working.")
    time.sleep(0.5)
    speak(f"Running on {sys.platform} using {_engine_name}.")