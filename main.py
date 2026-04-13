import threading
import time
import sys
import json
import os
import queue
import io

# Fix Unicode support on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from clap_detector import ClapDetector
from reminder_manager import ReminderManager
from app_launcher import AppLauncher
from scheduler import ReminderScheduler
from speaker import speak
from job_alert_monitor import JobAlertMonitor

# voice_commands requires PyAudio — import is optional
try:
    from voice_commands import VoiceRecognizer
    _VOICE_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Voice recognition unavailable ({e}). Using keyboard input.")
    _VOICE_AVAILABLE = False

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, "config.json")

DEFAULT_CONFIG = {
    "clap_sensitivity": 0.05,
    "clap_timeout": 1.0,
    "mic_device": None,
    "voice_enabled": True,
    "startup_announcement": True,
}


class ReminderBot:
    def __init__(self):
        self.reminder_manager = ReminderManager()
        self.app_launcher = AppLauncher()
        self.scheduler = ReminderScheduler(self.reminder_manager)
        self.job_monitor = JobAlertMonitor()
        self.config = self._load_config()

        self.voice_recognizer = None
        if _VOICE_AVAILABLE and self.config.get("voice_enabled", True):
            try:
                self.voice_recognizer = VoiceRecognizer()
                if not self.voice_recognizer.available:
                    self.voice_recognizer = None
            except Exception as e:
                print(f"⚠️  Voice recogniser failed: {e}")

        self.clap_detector = ClapDetector(
            on_clap=self.handle_clap,
            sensitivity=self.config.get("clap_sensitivity", 0.05),
            timeout=self.config.get("clap_timeout", 1.0),
        )
        self.running = True
        self.processing_command = False

        # Single background thread reads stdin continuously so keyboard input
        # is never blocked by the clap-detector thread.
        self._input_queue = queue.Queue()
        self._stdin_thread = threading.Thread(
            target=self._stdin_reader, daemon=True
        )
        self._stdin_thread.start()

    # ── Stdin reader (runs in its own daemon thread) ───────────────────────────

    def _stdin_reader(self):
        """Continuously read lines from stdin and push them onto the queue."""
        while True:
            try:
                line = sys.stdin.readline()
                if line:
                    self._input_queue.put(line.strip())
            except Exception:
                break

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    content = f.read().strip()
                    if content:
                        cfg = json.loads(content)
                        print("✅ Config loaded")
                        return {**DEFAULT_CONFIG, **cfg}
            except Exception as e:
                print(f"⚠️  Config error ({e}), using defaults")
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()

    # ── Input helper ──────────────────────────────────────────────────────────

    def _get_input(self, prompt_text: str, voice_prompt: str = None,
                   timeout: int = 8) -> str:
        """
        Collect user input — keyboard and voice run simultaneously.
        The first non-empty response wins.
        """
        speak(voice_prompt or prompt_text)

        # Drain any stale input that arrived before we started listening
        while not self._input_queue.empty():
            self._input_queue.get_nowait()

        print(f"⌨️  {prompt_text}  ", end="", flush=True)

        result_holder = [None]
        done = threading.Event()

        # Voice listener thread
        def _listen_voice():
            if self.voice_recognizer and self.voice_recognizer.available:
                try:
                    val = self.voice_recognizer.listen_for_command(timeout=timeout)
                    if val and not done.is_set():
                        result_holder[0] = val
                        done.set()
                except Exception as e:
                    print(f"\n⚠️ Voice recognition error: {e}")

        voice_thread = threading.Thread(target=_listen_voice, daemon=True)
        voice_thread.start()

        # Keyboard: poll the queue until timeout or done
        deadline = time.time() + timeout
        while not done.is_set() and time.time() < deadline:
            try:
                typed = self._input_queue.get(timeout=0.2)
                if typed:
                    result_holder[0] = typed
                    done.set()
                    break
            except queue.Empty:
                pass

        done.set()
        voice_thread.join(timeout=0.5)

        val = (result_holder[0] or "").lower().strip()
        if val:
            print(val)
        else:
            print()
        return val

    # ── Startup ───────────────────────────────────────────────────────────────

    def startup_routine(self):
        print("\n🤖 Reminder Bot Starting...")
        speak("Welcome back!")
        time.sleep(0.8)
        speak("Here is your schedule for today.")
        time.sleep(0.8)

        today_reminders = self.reminder_manager.get_today_reminders()
        if today_reminders:
            print(f"\n📅 Today's Tasks ({len(today_reminders)}):")
            speak(f"You have {len(today_reminders)} tasks today.")
            time.sleep(1)
            for i, r in enumerate(today_reminders, 1):
                print(f"  {i}. 📌 {r['time']} - {r['task']}")
                speak(f"At {r['time']}, {r['task']}")
                time.sleep(1.5)
        else:
            print("  ✅ No tasks for today")
            speak("You have no scheduled tasks for today.")

        self.scheduler.start()

    # ── Clap handler ──────────────────────────────────────────────────────────

    def handle_clap(self):
        """Handle two claps detection"""
        if self.processing_command:
            print("\n👏 Clap detected but bot is busy. Please wait...")
            return

        self.processing_command = True
        try:
            print("\n" + "="*50)
            print("👏 TWO CLAPS DETECTED! 👏")
            print("="*50)

            speak("Yes?")
            time.sleep(0.3)

            mode_hint = "(voice or keyboard)" if self.voice_recognizer else "(type and press Enter)"
            print(f"\n📋 Available commands {mode_hint}:")
            print("   reminders · add · delete · browser · spotify · files · jobs · saved jobs · exit\n")

            command = self._get_input(
                prompt_text="Command:",
                voice_prompt="What would you like to do?",
                timeout=5,
            )

            self._dispatch_command(command)

        except Exception as e:
            print(f"\n⚠️ Error: {e}")
        finally:
            self.processing_command = False
            print("\n🎧 Listening. Clap twice to activate.\n")

    def _dispatch_command(self, command: str):
        """Dispatch commands to appropriate handlers"""
        if not command:
            speak("No command received. Try again.")
            return

        # Job alert commands
        if "jobs" in command and "saved" not in command and "stop" not in command:
            speak("Checking for new MERN stack jobs")
            self.job_monitor.check_now()
        elif "saved jobs" in command or "show jobs" in command:
            self.job_monitor.show_saved_jobs()
        elif "stop jobs" in command or "pause jobs" in command:
            self.job_monitor.stop_monitoring()
            speak("Job monitoring paused")
        elif "resume jobs" in command or "start jobs" in command:
            self.job_monitor.start_monitoring()
            speak("Job monitoring resumed")
        # Reminder commands
        elif "reminder" in command and "add" not in command and "delete" not in command and "remove" not in command:
            self.read_today_reminders()
        elif "add" in command and "task" not in command:
            self.add_reminder_interactive()
        elif "delete" in command or "remove" in command or "remove task" in command or "delete task" in command:
            self.delete_reminder_interactive()
        # General commands
        elif "browser" in command:
            self.app_launcher.open_browser()
            speak("Opening browser")
        elif "spotify" in command:
            self.app_launcher.open_spotify()
            speak("Opening Spotify")
        elif "file" in command:
            self.app_launcher.open_file_manager()
            speak("Opening file manager")
        elif command in {"exit", "cancel", "quit", "no", "never mind", "nevermind"}:
            speak("Okay")
        else:
            speak("Command not recognised")
            print(f"❌ Unknown command: '{command}'")

    # ── Commands ──────────────────────────────────────────────────────────────

    def read_today_reminders(self):
        """Read today's reminders aloud"""
        reminders = self.reminder_manager.get_today_reminders()
        if reminders:
            print(f"\n📅 Today's Reminders ({len(reminders)}):")
            speak(f"You have {len(reminders)} tasks today.")
            time.sleep(1)
            for i, r in enumerate(reminders, 1):
                print(f"   {i}. {r['time']} - {r['task']}")
                speak(f"At {r['time']}, {r['task']}")
                time.sleep(1.5)
        else:
            print("\n✅ No reminders for today")
            speak("No reminders for today")

    def add_reminder_interactive(self):
        """Add a new reminder interactively"""
        print("\n➕ ADD NEW REMINDER")

        task = self._get_input(
            prompt_text="Task name:",
            voice_prompt="What should I remind you about?",
            timeout=10,
        )
        if not task:
            speak("No task provided. Cancelled.")
            return

        time_str = self._get_input(
            prompt_text="Time (HH:MM):",
            voice_prompt="At what time?",
            timeout=8,
        )
        if not time_str:
            speak("No time provided. Cancelled.")
            return

        # Normalise spoken time if voice was used
        if _VOICE_AVAILABLE and self.voice_recognizer:
            time_str = self.voice_recognizer._parse_spoken_time(time_str)

        try:
            from datetime import datetime as dt
            dt.strptime(time_str, "%H:%M")
            self.reminder_manager.add_reminder(task, time_str)
            print(f"\n✅ Reminder added: '{task}' at {time_str}")
            speak(f"Done. I'll remind you about {task} at {time_str}.")
        except ValueError:
            print("❌ Invalid time format. Use HH:MM (e.g., 09:30)")
            speak("Invalid time format. Please try again using H H colon M M.")

    def delete_reminder_interactive(self):
        """Delete reminders interactively"""
        print("\n🗑️  DELETE REMINDER")
        
        # Show active reminders
        active = self.reminder_manager.list_active_reminders()
        if not active:
            print("No active reminders to delete")
            speak("No active reminders to delete")
            return
        
        print("\n📋 Active Reminders:")
        for i, r in enumerate(active, 1):
            recurrence = f"on {r['date']}" if r['date'] else "(daily)"
            print(f"  {i}. [{r['id']}] {r['time']} - {r['task']} {recurrence}")
        
        speak(f"Which reminder would you like to delete? I found {len(active)} active reminders.")
        
        choice = self._get_input(
            prompt_text="Enter reminder number or task name to delete:",
            voice_prompt="Task number or name?",
            timeout=8,
        )
        
        if not choice:
            speak("Cancelled.")
            return
        
        # Try parsing as ID number first
        try:
            reminder_id = int(choice.strip())
            # Verify it exists
            if any(r['id'] == reminder_id for r in active):
                self.reminder_manager.delete_reminder(reminder_id)
                print(f"✅ Reminder {reminder_id} deleted")
                speak(f"Reminder deleted")
                return
        except ValueError:
            pass
        
        # Try matching by task name
        deleted_count = self.reminder_manager.delete_reminder_by_name(choice)
        if deleted_count > 0:
            print(f"✅ Deleted {deleted_count} reminder(s) matching '{choice}'")
            speak(f"Deleted {deleted_count} reminder")
        else:
            print(f"❌ No reminders found matching '{choice}'")
            speak("No reminders found with that name")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Main bot loop"""
        if self.config.get("startup_announcement", True):
            self.startup_routine()

        clap_thread = threading.Thread(
            target=self.clap_detector.start, daemon=True
        )
        clap_thread.start()

        mode = "🎤 Voice + ⌨️  keyboard" if self.voice_recognizer else "⌨️  Keyboard only"
        print("\n" + "="*50)
        print("🎧 REMINDER BOT IS RUNNING 🎧")
        print("="*50)
        print(f"   Input mode: {mode}")
        print("   👏 Clap twice to activate commands")
        print("   ⌨️  Press Ctrl+C to stop")
        print("="*50 + "\n")

        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            self.job_monitor.stop_monitoring()
            self.clap_detector.stop()
            self.scheduler.stop()
            sys.exit(0)


if __name__ == "__main__":
    bot = ReminderBot()
    bot.run()