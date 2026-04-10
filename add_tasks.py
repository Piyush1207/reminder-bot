"""Standalone utility to add reminders to the database."""
from reminder_manager import ReminderManager

rm = ReminderManager()  # uses the absolute DB path from reminder_manager.py


def add_task(task, time_str, date=None):
    try:
        rm.add_reminder(task, time_str, date)
        recurrence = f"on {date}" if date else "daily"
        print(f"✅ Added: '{task}' at {time_str} ({recurrence})")
        return True
    except ValueError as e:
        print(f"❌ {e}")
        return False


def add_multiple_tasks():
    tasks = [
        ("Morning meeting",  "09:00"),
        ("Lunch break",      "12:30"),
        ("Submit report",    "15:00"),
        ("Team sync",        "16:30"),
        ("Take medicine",    "20:00"),
    ]
    for task, time_str in tasks:
        add_task(task, time_str)
    print("\n📋 All tasks added successfully!")


if __name__ == "__main__":
    print("Task Addition Tool")
    print("1. Add single task (daily/recurring)")
    print("2. Add single task (one-time, specific date)")
    print("3. Add multiple sample tasks (daily)")

    choice = input("Choose (1/2/3): ").strip()

    if choice == "1":
        task = input("Task: ").strip()
        time_str = input("Time (HH:MM): ").strip()
        add_task(task, time_str)           # date=None → daily
    elif choice == "2":
        task = input("Task: ").strip()
        time_str = input("Time (HH:MM): ").strip()
        date = input("Date (YYYY-MM-DD): ").strip()
        add_task(task, time_str, date)
    elif choice == "3":
        add_multiple_tasks()
    else:
        print("Invalid choice.")