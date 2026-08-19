# Volunteer Padlet Automation

Desktop helper for finding local volunteer opportunities and posting new ones to a Padlet board.

The app reads Seattle volunteer opportunities from a Trumba RSS feed and Sammamish opportunities from Galaxy Digital, filters out duplicate, incomplete, and past events, then creates Padlet posts for the remaining opportunities. It is built as a small Tkinter desktop app so non-technical users can preview opportunities before publishing them.

## Features

- Fetches Seattle and Sammamish volunteer opportunities.
- Filters duplicate source links and existing Padlet posts.
- Skips incomplete or past opportunities.
- Adds Padlet post colors by city.
- Optionally stores Padlet credentials in the user's local app-data folder.
- Includes scripts for building macOS and Windows installers.

## Project Layout

```text
.
├── main.py                  # Tkinter UI and publishing workflow
├── mainFunction.py          # Volunteer source scraping, RSS parsing, and date handling
├── padletAutomation.py      # Padlet API helpers
├── daily_reminder.py        # Optional OS-scheduled reminder popup
├── generated_assets/        # Source images and app icons used by the packaged app
├── scripts/                 # Build scripts
├── installer/               # Platform installer definitions
├── docs/                    # Setup and packaging documentation
├── requirements.txt         # Runtime dependencies
└── requirements-packaging.txt
```

## Requirements

- Python 3.10 or newer
- A Padlet API key
- A Padlet board ID

Tkinter is included with most standard Python installers. If your Python distribution does not include Tkinter, install a Python build that includes GUI support.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 main.py
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Private Data

The app can save the Padlet API key and board ID locally. Those settings are written outside the repository in the user's app-data folder. A legacy local `.padlet_settings.json` file is also ignored so credentials are not committed accidentally.

Before publishing this repository publicly, check the Git history for secrets if real API keys were ever committed.

## Documentation

- [Packaging guide](docs/PACKAGING.md)
- [Daily reminder setup](docs/DAILY_REMINDER_SETUP.md)

## Publishing Checklist

- Choose and add an open-source license.
- Confirm no credentials, local settings, packaged apps, or installer outputs are tracked.
- Build release artifacts from a clean checkout.
- Add screenshots or a short demo GIF if the GitHub repository will be shared with end users.

