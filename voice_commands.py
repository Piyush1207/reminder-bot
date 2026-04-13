from __future__ import annotations

import re
import speech_recognition as sr
import time
import threading


class VoiceRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.available = False
        self._init_microphone()

    def _init_microphone(self):
        """Initialize microphone"""
        try:
            # Test if microphone is available
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("🎤 Microphone available for voice commands")
                print("✅ Voice recognition ready")
                self.available = True
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            self.available = False

    def listen_for_command(self, timeout=5) -> str | None:
        """
        Listen for a voice command and return it as lowercase text, or None.
        """
        if not self.available:
            return None
        
        try:
            print("🎤 Listening for command...")
            
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
            
            print("🔄 Processing...")
            text = self.recognizer.recognize_google(audio)
            print(f"📝 Recognised: '{text}'")
            return text.lower()
            
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            return None
        except sr.UnknownValueError:
            print("❓ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Recognition service error: {e}")
            print("💡 Check your internet connection")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def listen_for_task(self) -> str | None:
        """Listen specifically for a task description"""
        print("🎤 Please say your task clearly...")
        return self.listen_for_command(timeout=8)

    def listen_for_time(self) -> str | None:
        """Listen for time (e.g., 'two PM' or '14:30')"""
        print("🎤 Please say the time...")
        raw = self.listen_for_command(timeout=5)
        if raw:
            return self._parse_spoken_time(raw)
        return None

    @staticmethod
    def _parse_spoken_time(text: str) -> str:
        """
        Convert spoken time to HH:MM.
        Handles:
          - "two PM"  -> "14:00"
          - "9:30 AM" -> "09:30"
          - "14:30"   -> "14:30"
        """
        if not text:
            return text

        text = text.lower().strip()

        word_to_num = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
            'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
        }

        is_pm = 'pm' in text or 'p m' in text or "p.m" in text
        is_am = 'am' in text or 'a m' in text or "a.m" in text

        # Try word-based hour first
        for word, num in word_to_num.items():
            if word in text:
                hour = num
                if is_pm and hour != 12:
                    hour += 12
                elif is_am and hour == 12:
                    hour = 0
                return f"{hour:02d}:00"

        # Try digit-based match (e.g., "9 30", "9:30", "14:30")
        match = re.search(r'(\d{1,2})[:\s]?(\d{2})?', text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"

        return text


# Module-level convenience functions
_recognizer: VoiceRecognizer | None = None


def _get_recognizer() -> VoiceRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = VoiceRecognizer()
    return _recognizer


def listen_for_command() -> str | None:
    return _get_recognizer().listen_for_command()


def listen_for_task() -> str | None:
    return _get_recognizer().listen_for_task()


def listen_for_time() -> str | None:
    return _get_recognizer().listen_for_time()


if __name__ == "__main__":
    print("Testing voice recognition... say something like 'add task' or 'two PM'")
    result = listen_for_command()
    if result:
        print(f"✅ You said: {result}")
    else:
        print("❌ Voice recognition returned nothing")