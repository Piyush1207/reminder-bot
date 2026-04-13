# Task Management - Addition & Deletion Guide

## Adding Tasks

### Via Voice Command
1. **Clap twice** to activate
2. Say: `"add"` or `"add task"`
3. Say the task name (e.g., `"Morning meeting"`)
4. Say the time (e.g., `"9 AM"` or `"09:00"`)
5. Task is added to your schedule

### Via Keyboard
1. Clap twice or refer to command help
2. Type: `add`
3. Enter task name when prompted
4. Enter time in HH:MM format (e.g., `09:30`)
5. Confirmation message appears

### Via Script (Direct DB Entry)
```bash
python add_tasks.py
```
Choose option:
- **1**: Add single daily task
- **2**: Add one-time task (specific date)
- **3**: Add multiple sample tasks

---

## Deleting Tasks

### Via Voice Command ✨ **NEW**
1. **Clap twice** to activate
2. Say: `"delete"` or `"remove task"`
3. Bot will list all active reminders
4. Say the **reminder number** or **task name**
5. Task is deleted

### Via Keyboard ✨ **NEW**
1. Clap twice or refer to help
2. Type: `delete` or `remove`
3. View list of active reminders
4. Enter reminder **ID number** or **task name**
5. Confirmation message shows

**Examples:**
- Say/Type: `1` → Deletes first reminder in list
- Say/Type: `meeting` → Deletes all reminders containing "meeting"
- Say/Type: `remove gym` → Deletes reminder with "gym" in name

---

## Auto-Delete System (Automatic)

**Completed tasks are automatically deleted after 24 hours.**

### How it works:
- Once-time reminders automatically marked "completed" when triggered
- Scheduler runs cleanup **every hour**
- Completed tasks older than 24 hours are automatically removed
- **Daily/recurring reminders** are NOT auto-deleted (reset daily instead)

### Customization:
Edit `scheduler.py` line ~80:
```python
self.reminder_manager.auto_delete_completed(hours=24)  # Change 24 to desired hours
```

---

## Available Task Operations

| Operation | Command | Example |
|-----------|---------|---------|
| **View Today** | `reminders` | "reminders" / "show tasks" |
| **Add Task** | `add` | "add" / "add task" |
| **Delete Task** | `delete` or `remove` | "delete" / "remove task" |
| **Check Jobs** | `jobs` | Job alerts |
| **List Saved Jobs** | `saved jobs` | View matched positions |
| **Exit** | `exit` / `quit` | Stop bot |

---

## Task Status & Lifecycle

### Task States:
1. **Active** - Waiting to trigger
2. **Triggered** - Fired at scheduled time (for daily) OR marked complete (for one-time)
3. **Completed** - One-time reminder marked done
4. **Deleted** - Manually removed OR auto-deleted after 24 hours

### One-Time vs. Daily Reminders:

**One-Time Task** (specific date):
```
Task: "Annual review" on 2026-04-25 at 10:00
Status: Active → Triggers once → Auto-deleted 24h after completion
```

**Daily Task** (no date):
```
Task: "Morning standup" at 09:00 (no date specified)
Status: Active → Triggers daily → Resets next day → Never expires
```

---

## ✅ New Features Summary

✨ **New in this update:**
- ✅ Interactive delete command (`delete` / `remove`)
- ✅ Delete by reminder ID number
- ✅ Delete by task name (fuzzy matching)
- ✅ View all active reminders before deleting
- ✅ Voice command support for deletion
- ✅ Bulk delete by name pattern

🔧 **Existing features:**
- ✅ Auto-delete completed tasks (24h default)
- ✅ Hourly cleanup scheduler
- ✅ Daily/recurring reminders never expire
- ✅ One-time reminders clean themselves

---

## Database Info

All tasks stored in: `reminders.db`

SQLite schema:
```sql
reminders (
  id              INTEGER PRIMARY KEY,
  task            TEXT NOT NULL,
  time            TEXT (HH:MM format),
  date            TEXT (YYYY-MM-DD, NULL = daily),
  completed       BOOLEAN,
  last_triggered_date TEXT,
  completed_at    TIMESTAMP,
  created_at      TIMESTAMP
)
```

**To manually reset reminders:**
```bash
rm reminders.db  # Delete local database, will recreate on next run
```

---

## Troubleshooting

**Q: Reminder won't delete**
- A: Ensure you enter the correct reminder ID or exact task name
- Try listing reminders first to confirm the name

**Q: Tasks keep reappearing**
- A: If recurring (daily) task, it resets each day. This is expected.
- Use delete command each time if you want to skip a day

**Q: Auto-delete not working**
- A: Verify scheduler is running. Check console for "✅ Scheduler started"
- Auto-delete runs once per hour automatically

**Q: Want to keep a completed task?**
- A: Manually delete before 24-hour window, or edit `scheduler.py` to increase the hour threshold

---

**Ready to manage your tasks!** 🎯
