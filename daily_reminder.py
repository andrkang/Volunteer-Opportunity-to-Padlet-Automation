"""Show a daily reminder to run the Harvest Opportunities app.

This script is meant to be called by the operating system scheduler:
- Windows Task Scheduler
- macOS LaunchAgent

It only reminds the user. It does not open the app or update Padlet.
"""

import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


APP_DIR = Path(__file__).resolve().parent
TITLE = "Harvest Opportunities Reminder"
MESSAGE = f"Please run the Harvest Opportunities app today.\n\nApp folder:\n{APP_DIR}"


def show_reminder():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo(TITLE, MESSAGE, parent=root)
    root.destroy()


def main():
    try:
        show_reminder()
    except Exception as exc:
        print(f"Could not show reminder: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
