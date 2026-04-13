# 🤖 Reminder Bot

A voice-activated personal assistant for Windows that listens for a **double clap** to wake up, reads your reminders aloud, and monitors job boards for MERN stack opportunities — all in the background.

---

## ✨ Features

| Feature | Description |
|---|---|
| 👏 **Clap detection** | Clap twice to activate the bot (no hotkey needed) |
| 🔊 **Text-to-speech** | Speaks responses using Windows SAPI (falls back to pyttsx3/espeak) |
| 🎤 **Voice commands** | Speak commands after waking the bot (keyboard fallback always available) |
| 📅 **Reminder management** | Add, read, and delete one-time or daily recurring reminders |
| ⏰ **Auto scheduler** | Fires reminders at the exact minute with desktop notifications |
| 💼 **Job alert monitor** | Searches Indeed, RemoteOK, WeWorkRemotely; scores jobs against your MERN profile |
| 🗑️ **Auto-cleanup** | Completed one-time reminders are auto-deleted after 24 hours |

---

## 🚀 Quick Start

### 1. Clone / download the project
```bash
git clone <repo-url>
cd reminder-bot
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** `PyAudio` can be tricky on Windows. If `pip install PyAudio` fails, download the correct `.whl` from [https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install it manually:
> ```bash
> pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl
> ```

### 4. Configure API keys (optional)
```bash
copy .env.example .env
```
Edit `.env` and add your **TheirStack API key** for live job search. Without it, the bot falls back to web scraping.

### 5. Run the bot
```bash
python main.py
# or double-click run_bot.bat
```

---

## 🎮 Available Commands

Once the bot is running, **clap twice** to activate, then say or type a command:

| Command | Action |
|---|---|
| `reminders` | Read today's reminders aloud |
| `add` | Interactively add a new reminder |
| `delete` / `remove` | Delete a reminder by number or name |
| `jobs` | Manually check for new MERN job listings |
| `saved jobs` | List previously found job matches |
| `stop jobs` | Pause the job monitor |
| `resume jobs` | Resume the job monitor |
| `browser` | Open default browser |
| `spotify` | Launch Spotify |
| `files` | Open File Explorer |
| `exit` / `cancel` | Dismiss the prompt |

---

## ⚙️ Configuration

### `config.json` — Bot settings
| Key | Default | Description |
|---|---|---|
| `clap_sensitivity` | `0.05` | Microphone RMS threshold for clap detection (lower = more sensitive) |
| `clap_timeout` | `1.0` | Max seconds between two claps to count as a double-clap |
| `mic_device` | `null` | Microphone device index (null = system default) |
| `voice_enabled` | `true` | Enable/disable voice recognition |
| `startup_announcement` | `true` | Read today's schedule on launch |

### `job_alert_config.json` — Job monitor settings
Edit your tech stack, preferred locations, experience level, and notification threshold in this file.

---

## 🏗️ Project Structure

```
reminder-bot/
├── main.py                  # Entry point — orchestrates all modules
├── clap_detector.py         # Microphone listener + double-clap detection
├── voice_commands.py        # Google Speech-to-Text + spoken time parser
├── speaker.py               # TTS engine (SAPI → pyttsx3 → espeak → print)
├── reminder_manager.py      # SQLite CRUD for reminders (one-time & recurring)
├── scheduler.py             # Background scheduler — fires reminders at HH:MM
├── app_launcher.py          # Cross-platform app/URL launcher
├── job_alert_monitor.py     # Job scraper + scoring engine + notifications
├── add_tasks.py             # CLI utility to seed reminders into the DB
├── config.json              # Bot configuration
├── job_alert_config.json    # Job monitor configuration
├── requirements.txt         # Python dependencies
├── .env.example             # Template for API keys
└── run_bot.bat              # Windows one-click launcher
```

---

## 🗄️ Database Schema

### `reminders.db`
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task` | TEXT | Reminder text |
| `time` | TEXT | HH:MM format |
| `date` | TEXT | YYYY-MM-DD (NULL = daily recurring) |
| `completed` | BOOLEAN | Whether task has been done |
| `last_triggered_date` | TEXT | Prevents double-firing recurring reminders |
| `completed_at` | TIMESTAMP | Used for 24-hour auto-delete |

### `job_notification.db`
Tracks seen jobs (`seen_jobs`) and notification history (`job_alerts`) to prevent duplicate alerts.

---

## 🔧 Troubleshooting

**Bot can't hear claps?**
- Lower `clap_sensitivity` in `config.json` (try `0.02`)
- Make sure your microphone is set as the system default

**Voice recognition not working?**
- Requires internet (uses Google STT)
- Disable with `"voice_enabled": false` in `config.json` to use keyboard-only mode

**Job monitor finds no jobs?**
- Job board HTML structures change frequently — scrapers may need updating
- Add a TheirStack API key in `.env` for more reliable results

**`PyAudio` install fails?**
- See the manual `.whl` install instructions in the Quick Start section above

---

## 📝 License

MIT — free to use and modify.