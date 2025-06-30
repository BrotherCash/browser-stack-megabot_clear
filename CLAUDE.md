# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot that manages BrowserStack access among multiple users. The bot implements a queue system where only one user can use BrowserStack at a time, with authorization controls and admin approval for new users.

## Architecture

**Single-file application**: The entire bot logic is contained in `bot.py` - a monolith that handles:
- User authentication and authorization flow
- SQLite database operations for user management 
- BrowserStack session management (simple busy/free state)
- Telegram bot message handling and callbacks
- Admin approval workflow

**Database schema**: SQLite database (`bot_users.db`) with single `users` table containing:
- User identification (tg_id, username, first_name, last_name)
- Authorization status (role: 'user'/'admin', status: 'pending'/'approved'/'blocked')
- Timestamps for user registration

**State management**: Global variables track current BrowserStack session:
- `busy`: Boolean indicating if BrowserStack is in use
- `user`: Dictionary storing current user's info when active

## Development Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the bot locally:**
```bash
python bot.py
# or
python3 bot.py
```

**Deploy to Heroku:**
The `Procfile` defines the worker process. The bot runs as a background worker, not a web server.

## Important Notes

**Python version**: The project uses Python 3.9 (specified in `.python-version`)

**Database initialization**: The bot automatically creates SQLite database and admin user on first run

**Bot token**: Hard-coded in `bot.py:5` - should be moved to environment variables for production

**Admin configuration**: Admin ID and details are hard-coded in constants (lines 16-18)

**No testing framework**: The project has no tests - all testing must be done manually with a real Telegram bot

**Heroku deployment**: Uses worker dyno type, not web dyno (see Procfile)