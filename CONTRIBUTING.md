# Contributing

Thanks for taking the time to improve Volunteer Padlet Automation.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

On Windows, use `py -3` or `python` if that is how Python is installed.

## Development Checks

Run a syntax check before opening a pull request:

```bash
python3 -m compileall main.py mainFunction.py padletAutomation.py daily_reminder.py
```

If you change packaging behavior, also run the relevant packaging script documented in `docs/PACKAGING.md`.

## Pull Request Guidelines

- Keep credentials, `.padlet_settings.json`, `build/`, and `dist/` out of commits.
- Keep UI changes focused and test the app manually.
- Explain any scraper changes, especially if they depend on external page structure.
- Include before/after notes for behavior changes that affect Padlet posts.

