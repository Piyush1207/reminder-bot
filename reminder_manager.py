import sqlite3
import os
from datetime import datetime

# Always resolve DB relative to this file's directory, not the working directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.db")

class ReminderManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.init_database()

    def init_database(self):
        """Create reminders table if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    time TEXT NOT NULL,       -- HH:MM format
                    date TEXT,                -- YYYY-MM-DD, NULL means daily/recurring
                    completed BOOLEAN DEFAULT 0,
                    last_triggered_date TEXT, -- tracks last fire date for recurring reminders
                    completed_at TIMESTAMP,   -- timestamp when task was marked complete
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Migrate existing DBs that lack last_triggered_date column
            try:
                conn.execute("ALTER TABLE reminders ADD COLUMN last_triggered_date TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            # Migrate existing DBs that lack completed_at column
            try:
                conn.execute("ALTER TABLE reminders ADD COLUMN completed_at TIMESTAMP")
            except sqlite3.OperationalError:
                pass  # Column already exists

    def add_reminder(self, task, time_str, date=None):
        """Add a new reminder. date=None means it repeats daily."""
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM format")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO reminders (task, time, date) VALUES (?, ?, ?)",
                (task, time_str, date)
            )
            return cursor.lastrowid

    def get_today_reminders(self):
        """Get all reminders for today (both dated and recurring)."""
        today = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM reminders
                WHERE (
                    (date = ? AND completed = 0)
                    OR
                    (date IS NULL AND (
                        last_triggered_date IS NULL
                        OR last_triggered_date != ?
                    ))
                )
                ORDER BY time
            ''', (today, today))
            return [dict(row) for row in cursor.fetchall()]

    def get_pending_reminders(self):
        """Get reminders that should fire right now."""
        current_time = datetime.now().strftime("%H:%M")
        today = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM reminders
                WHERE time = ?
                AND (
                    (date = ? AND completed = 0)
                    OR
                    (date IS NULL AND (
                        last_triggered_date IS NULL
                        OR last_triggered_date != ?
                    ))
                )
            ''', (current_time, today, today))
            return [dict(row) for row in cursor.fetchall()]

    def mark_triggered(self, reminder_id):
        """
        One-time reminders: mark completed.
        Daily reminders (date IS NULL): store today's date so they reset tomorrow.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT date FROM reminders WHERE id = ?", (reminder_id,)
            ).fetchone()

            if row is None:
                return

            if row[0] is None:
                # Recurring — just stamp today, fires again tomorrow
                conn.execute(
                    "UPDATE reminders SET last_triggered_date = ? WHERE id = ?",
                    (today, reminder_id)
                )
            else:
                # One-time — mark done and timestamp completion
                conn.execute(
                    "UPDATE reminders SET completed = 1, completed_at = ? WHERE id = ?",
                    (now, reminder_id)
                )

    # Backward-compatible alias
    def mark_completed(self, reminder_id):
        self.mark_triggered(reminder_id)

    def delete_reminder(self, reminder_id):
        """Delete a reminder permanently."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))

    def auto_delete_completed(self, hours=24):
        """
        Auto-delete completed one-time reminders older than specified hours.
        Default: delete completed tasks older than 24 hours.
        """
        from datetime import timedelta
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM reminders WHERE completed = 1 AND completed_at <= ? AND completed_at IS NOT NULL",
                (cutoff_time,)
            )
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                print(f"🗑️  Auto-deleted {deleted_count} completed task(s) older than {hours} hour(s)")
            return deleted_count