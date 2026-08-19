# Daily Reminder Setup

Use `daily_reminder.py` with the operating system scheduler. This shows a daily popup reminder to run the Volunteer Padlet app. It does not automatically open the app or update Padlet.

## Windows

Open PowerShell and run this from the project folder:

```powershell
$Project = (Get-Location).Path
$Python = "python"
$Script = Join-Path $Project "daily_reminder.py"

schtasks /Create `
  /TN "Volunteer Padlet Daily Reminder" `
  /SC DAILY `
  /ST 08:00 `
  /TR "`"$Python`" `"$Script`"" `
  /F
```

Because this reminder shows a popup, configure the task to run only when the user is logged on if you edit it in Task Scheduler.

To test it immediately:

```powershell
schtasks /Run /TN "Volunteer Padlet Daily Reminder"
```

To remove it:

```powershell
schtasks /Delete /TN "Volunteer Padlet Daily Reminder" /F
```

## macOS

Create `~/Library/LaunchAgents/com.andrew.volunteer-padlet-reminder.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.andrew.volunteer-padlet-reminder</string>

    <key>ProgramArguments</key>
    <array>
      <string>python3</string>
      <string>/absolute/path/to/Volunteer-Opportunity-Downloader/daily_reminder.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
      <key>Hour</key>
      <integer>8</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/tmp/volunteer-padlet-reminder.out.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/volunteer-padlet-reminder.err.log</string>
  </dict>
</plist>
```

Replace `/absolute/path/to/Volunteer-Opportunity-Downloader/daily_reminder.py` with the real full path.

Then run:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.andrew.volunteer-padlet-reminder.plist
launchctl enable gui/$(id -u)/com.andrew.volunteer-padlet-reminder
launchctl kickstart -k gui/$(id -u)/com.andrew.volunteer-padlet-reminder
```

To remove it:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.andrew.volunteer-padlet-reminder.plist
```
