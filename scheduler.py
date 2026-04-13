import threading
import time
from datetime import datetime
from speaker import speak_sync as speak
from plyer import notification


class ReminderScheduler:
    def __init__(self, reminder_manager):
        self.reminder_manager = reminder_manager
        self.running = False
        self.thread = None
        self.last_checked_minute = None
        self.triggered_this_session = set()  # (id, date) pairs already fired
        self.last_auto_delete = None  # Track last auto-delete time

    def start(self):
        """Start scheduler in background thread."""
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        print("✅ Reminder scheduler started")

    def stop(self):
        """Stop scheduler."""
        self.running = False

    def run(self):
        """Main loop — wakes every 30 s, fires at the right minute."""
        print("🕐 Scheduler is running...")
        while self.running:
            current_minute = datetime.now().strftime("%H:%M")

            if current_minute != self.last_checked_minute:
                self.last_checked_minute = current_minute
                self.check_reminders(current_minute)

            time.sleep(30)

    def check_reminders(self, current_minute):
        """Fire any reminders due right now."""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            pending = self.reminder_manager.get_pending_reminders()

            for reminder in pending:
                # Deduplicate within this session using (id, today) so a
                # recurring reminder that stays in pending due to a DB race
                # doesn't double-fire on the same day.
                session_key = (reminder['id'], today)
                if session_key in self.triggered_this_session:
                    continue

                self.triggered_this_session.add(session_key)

                print(f"\n⏰ REMINDER: {reminder['task']} at {reminder['time']}")
                speak(f"Reminder: {reminder['task']}")
                
                # Send desktop notification
                try:
                    notification.notify(
                        title="Reminder Bot",
                        message=reminder['task'],
                        timeout=5
                    )
                except Exception as e:
                    print(f"⚠️ Notification error: {e}")

                # mark_triggered handles one-time vs recurring correctly
                self.reminder_manager.mark_triggered(reminder['id'])

            # Prevent unbounded growth
            if len(self.triggered_this_session) > 500:
                self.triggered_this_session.clear()

        except Exception as e:
            print(f"⚠️ Scheduler error: {e}")

        # Auto-delete completed tasks periodically (once per hour)
        self._run_auto_delete_if_needed()

    def _run_auto_delete_if_needed(self):
        """Run auto-delete cleanup once per hour."""
        current_hour = datetime.now().strftime("%Y-%m-%d %H")
        if self.last_auto_delete != current_hour:
            self.last_auto_delete = current_hour
            try:
                self.reminder_manager.auto_delete_completed(hours=24)
            except Exception as e:
                print(f"⚠️ Auto-delete error: {e}")