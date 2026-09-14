"""Tkinter GUI for previewing volunteer opportunities pulled from a Trumba RSS feed.

High-level workflow
1) User checks the agreement checkbox (reveals the rest of the UI).
2) User enters Padlet API key + board ID.
3) User clicks the button to display the parsed volunteer opportunities.

Notes for maintainers
- This file intentionally focuses on UI and presentation.
- All RSS parsing and timezone handling lives in `mainFunction.py`.
"""

import tkinter as tk
import json
import os
import sys
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from daily_reminder import show_reminder
from padletAutomation import (
    createPadletPost,
    getBoardFromPadlet,
    getCustomFieldIdFromBoard,
    getPostFromPadlet,
)
from mainFunction import (
    getOpportunitiesFromRSS,
    getLocalTimezoneInfo,
    getSammamishOpportunities,
    parseFlexibleDate,
    sortOpportunitiesByDate,
    volunteerTimeZone,
)


# ----------------------------
# Configuration constants
# ----------------------------

def getResourcePath(relativePath):
    resourceRoot = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return resourceRoot / relativePath


def getAppDataPath():
    if sys.platform == "win32":
        basePath = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        basePath = Path.home() / "Library" / "Application Support"
    else:
        basePath = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    return basePath / "Harvest Opportunities"


baseUrl = 'https://api.padlet.dev/v1'
headers = {"User-Agent": "VolunteerHarvester/0.1"}
legacySettingsPath = Path(__file__).with_name(".padlet_settings.json")
settingsPath = getAppDataPath() / ".padlet_settings.json"
artworkPath = getResourcePath(Path("generated_assets") / "volunteer-service-art.png")
appIconPath = getResourcePath(Path("generated_assets") / "app-icon.png")

rssUrl = "https://www.trumba.com/calendars/volunteer-1.rss"
dateCustomFieldName = "Event Date"
colorGuidePostSubject = "Volunteer Board Color Guide"
colorGuidePostBody = (
    "Color coding:\n"
    "**Red posts** are opportunities added manually by teachers and staff. "
    "Teachers and staff should use red when adding posts by hand.\n"
    "**Blue posts** are Seattle volunteer opportunities.\n"
    "**Green posts** are Sammamish volunteer opportunities."
)
colorGuidePostDate = "2108-12-01"
colorGuidePostColor = "purple"
blockedOpportunityTitleFragments = (
    ("volunteer orientation", "3rd wed", "each month"),
)
blockedOpportunityLinkFragments = (
    "need_id=1273296",
)
requiredOpportunityFields = ("link", "date", "location", "description")

fontFamily = "Arial"
fontTitle = (fontFamily, 38, "bold")
fontSubtitle = (fontFamily, 15)
fontLabel = (fontFamily, 16, "bold")
fontBody = (fontFamily, 14)
fontBodyBold = (fontFamily, 14, "bold")
fontInput = (fontFamily, 17)
fontLegend = (fontFamily, 14, "bold")
fontSmall = (fontFamily, 12)
fontButton = (fontFamily, 16, "bold")
fontSmallButton = (fontFamily, 12, "bold")

bgColor = "#8F6F6F"
appSurfaceColor = "#7F6262"
panelColor = "#665A5A"
textColor = "#FFFDF9"
mutedTextColor = "#EFE4DF"
inputTextColor = "#2F2929"
inputColor = "#FFFDF9"
inputFocusColor = "#FFF4E6"
buttonColor = "#473E3E"
buttonHoverColor = "#5D5353"
buttonPressedColor = "#332D2D"
buttonDisabledColor = "#897D7D"
warningColor = "#FFE2D5"
cityColors = {
    "Seattle": {
        "card": "#526274",
        "field": "#EEF5FF",
    },
    "Sammamish": {
        "card": "#556D5C",
        "field": "#F0FAF1",
    },
}
padletCityColors = {
    "Seattle": "blue",
    "Sammamish": "green",
}
defaultEventColors = {
    "card": panelColor,
    "field": inputColor,
}

windowTitle = "Harvest Opportunities"
windowGeometry = "1280x760+160+160"
userAgreementText = """Harvest Opportunities User Agreement

Last updated: August 21, 2026

By using Harvest Opportunities, you agree to the following:

1. Purpose. This app helps you review volunteer opportunities from public volunteer feeds and publish selected opportunities to a Padlet board.
2. Review before publishing. You are responsible for reviewing all event titles, dates, locations, descriptions, links, and other details before publishing anything to Padlet.
3. Padlet access. Only use Padlet API keys and board IDs that you are authorized to use. Your use of Padlet remains subject to Padlet's own terms and policies.
4. Local credential storage. If you choose to save your Padlet API key and board ID, they are stored locally on this computer in the app settings file. You are responsible for keeping your device and account secure.
5. Third-party information. Volunteer opportunity details come from outside sources and may be incomplete, outdated, changed, or incorrect. Confirm important details with the organization hosting the opportunity.
6. School and privacy rules. If you use this app for a school, club, nonprofit, or organization, you are responsible for following that organization's rules, privacy requirements, and approval process.
7. No guarantee. This app is provided as-is, without a guarantee that it will always be available, error-free, or suitable for every use.
8. Open-source privacy note. This app does not send your saved Padlet details to the app author. It only uses your information locally and when contacting Padlet or volunteer data sources needed for the app to work.
9. Acceptance. Checking the box below confirms that you have read and agree to this user agreement."""


# ----------------------------
# Pure helpers (no UI)
# ----------------------------

def getPadletPostUrls(posts):
    postUrlSet = {
        normalizeOpportunityUrl(
            post.get("attributes", {}).get("content", {}).get("attachment", {}).get("url")
        )
        for post in posts
    }
    postUrlSet.discard("")
    return postUrlSet


def normalizeOpportunityText(value):
    text = str(value or "").lower()
    text = text.replace("-", " ").replace("–", " ").replace("—", " ")
    return " ".join(text.split())


def normalizeOpportunityUrl(value):
    return str(value or "").strip().rstrip("/")


def shouldSkipOpportunity(title, item):
    normalizedTitle = normalizeOpportunityText(title)
    normalizedLink = normalizeOpportunityUrl(item.get("link", "")).lower()

    if any(fragment in normalizedLink for fragment in blockedOpportunityLinkFragments):
        return True

    return any(
        all(fragment in normalizedTitle for fragment in fragmentGroup)
        for fragmentGroup in blockedOpportunityTitleFragments
    )


def isCompleteOpportunity(title, item):
    if not str(title or "").strip():
        return False

    for fieldName in requiredOpportunityFields:
        if not str(item.get(fieldName, "")).strip():
            return False

    return formatPadletDateProperty(item.get("date", "")) is not None


def isFutureOrTodayOpportunity(item, today=None):
    today = today or datetime.now(volunteerTimeZone).date()
    parsedDate = parseFlexibleDate(str(item.get("date", "")))
    if parsedDate.year == 9999:
        return False
    return parsedDate.date() >= today


def getWashingtonLegalHolidays(year):
    """Returns Washington's fixed, floating, and observed legal holidays."""
    def nthWeekday(month, weekday, occurrence):
        firstOfMonth = date(year, month, 1)
        daysUntilWeekday = (weekday - firstOfMonth.weekday()) % 7
        return firstOfMonth + timedelta(days=daysUntilWeekday + 7 * (occurrence - 1))

    def lastWeekday(month, weekday):
        firstOfNextMonth = date(year + (month == 12), month % 12 + 1, 1)
        lastOfMonth = firstOfNextMonth - timedelta(days=1)
        daysSinceWeekday = (lastOfMonth.weekday() - weekday) % 7
        return lastOfMonth - timedelta(days=daysSinceWeekday)

    thanksgiving = nthWeekday(11, 3, 4)
    holidays = {
        date(year, 1, 1),
        nthWeekday(1, 0, 3),
        nthWeekday(2, 0, 3),
        lastWeekday(5, 0),
        date(year, 6, 19),
        date(year, 7, 4),
        nthWeekday(9, 0, 1),
        date(year, 11, 11),
        thanksgiving,
        thanksgiving + timedelta(days=1),
        date(year, 12, 25),
    }

    # RCW 1.16.050 observes Saturday holidays on Friday and Sunday holidays on Monday.
    observedHolidays = set()
    for holiday in holidays:
        if holiday.weekday() == 5:
            observedHolidays.add(holiday - timedelta(days=1))
        elif holiday.weekday() == 6:
            observedHolidays.add(holiday + timedelta(days=1))
    return holidays | observedHolidays


def isWashingtonLegalHoliday(day):
    """Checks adjacent holiday years so New Year's observance can cross years."""
    return any(
        day in getWashingtonLegalHolidays(year)
        for year in (day.year - 1, day.year, day.year + 1)
    )


def isSchoolDayOpportunity(item):
    """Treats weekdays as school days, except Washington legal holidays."""
    parsedDate = parseFlexibleDate(str(item.get("date", "")))
    if parsedDate.year == 9999:
        return False

    opportunityDate = parsedDate.date()
    return (
        opportunityDate.weekday() < 5
        and not isWashingtonLegalHoliday(opportunityDate)
    )


def filterVolunteerItemsForDisplay(
    volunteerDict,
    opportunityLimit,
    existingUrls=None,
    skipSchooldays=False,
):
    existingUrls = existingUrls or set()
    filteredVolunteerDict = {}
    seenSourceUrls = set()

    for title, item in volunteerDict.items():
        normalizedLink = normalizeOpportunityUrl(item.get("link", ""))
        if shouldSkipOpportunity(title, item):
            continue
        if not isCompleteOpportunity(title, item):
            continue
        if not isFutureOrTodayOpportunity(item):
            continue
        if skipSchooldays and isSchoolDayOpportunity(item):
            continue
        if normalizedLink in seenSourceUrls:
            continue
        if normalizedLink in existingUrls:
            continue

        filteredVolunteerDict[title] = item
        seenSourceUrls.add(normalizedLink)

        if len(filteredVolunteerDict) >= opportunityLimit:
            break

    return filteredVolunteerDict


def fetchSourceVolunteerItems(selectedCities):
    shift, tzAbbrev = getLocalTimezoneInfo()
    volunteerDict = {}

    def addItems(sourceItems):
        for title, item in sourceItems.items():
            uniqueTitle = title
            duplicateNumber = 2
            while uniqueTitle in volunteerDict:
                uniqueTitle = f"{title} ({duplicateNumber})"
                duplicateNumber += 1
            volunteerDict[uniqueTitle] = item

    if "Seattle" in selectedCities:
        addItems(getOpportunitiesFromRSS(rssUrl, shift, tzAbbrev, None))
    if "Sammamish" in selectedCities:
        addItems(getSammamishOpportunities())

    return sortOpportunitiesByDate(volunteerDict)


def fetchNewVolunteerItems(
    apiKey,
    boardId,
    opportunityLimit,
    selectedCities,
    skipSchooldays=False,
):
    """Checks the most recent valid source opportunities and returns only new ones."""
    volunteerDict = fetchSourceVolunteerItems(selectedCities)
    posts = getPostFromPadlet(apiKey, baseUrl, boardId)
    postUrlSet = getPadletPostUrls(posts)
    recentVolunteerDict = filterVolunteerItemsForDisplay(
        volunteerDict,
        opportunityLimit,
        skipSchooldays=skipSchooldays,
    )
    return filterVolunteerItemsForDisplay(
        recentVolunteerDict,
        opportunityLimit,
        postUrlSet,
        skipSchooldays=skipSchooldays,
    )


def buildPostBody(date, location, description):
    return f"Date and Time: {date}\nLocation: {location}\n\nDescription: {description}"


def formatPadletDateProperty(dateText):
    parsedDate = parseFlexibleDate(str(dateText or ""))
    if parsedDate.year == 9999:
        return None
    return parsedDate.date().isoformat()


def normalizePadletDateValue(value):
    dateText = str(value or "").strip()
    if not dateText:
        return ""
    if dateText.startswith(colorGuidePostDate):
        return colorGuidePostDate
    if dateText in ("12/1/2108", "12/01/2108"):
        return colorGuidePostDate
    return formatPadletDateProperty(dateText) or dateText


def getPostSubject(post):
    return (
        post.get("attributes", {})
        .get("content", {})
        .get("subject", "")
        .strip()
    )


def getPostCustomFieldValues(post):
    values = []
    attributes = post.get("attributes", {})
    customFieldCandidates = (
        attributes.get("customFields"),
        attributes.get("custom_fields"),
        post.get("customFields"),
        post.get("custom_fields"),
    )

    for customFields in customFieldCandidates:
        if isinstance(customFields, dict):
            values.extend(customFields.values())
        elif isinstance(customFields, list):
            for field in customFields:
                if isinstance(field, dict):
                    values.append(field.get("value"))

    return values


def postIsColorGuide(post):
    if getPostSubject(post) == colorGuidePostSubject:
        return True

    return any(
        normalizePadletDateValue(value) == colorGuidePostDate
        for value in getPostCustomFieldValues(post)
    )


def ensureColorGuidePost(apiKey, boardId, boardPosts, dateCustomFieldId):
    if any(postIsColorGuide(post) for post in boardPosts):
        return False

    customFields = (
        {dateCustomFieldId: colorGuidePostDate}
        if dateCustomFieldId
        else None
    )
    createPadletPost(
        apiKey,
        baseUrl,
        boardId,
        colorGuidePostSubject,
        colorGuidePostBody,
        None,
        colorGuidePostColor,
        customFields,
    )
    return True


def publishVolunteerEvents(
    apiKey,
    boardId,
    events,
    opportunityLimit,
    skipSchooldays=False,
):
    boardJson = getBoardFromPadlet(apiKey, baseUrl, boardId)
    boardPosts = [obj for obj in boardJson.get("included", []) if obj.get("type") == "post"]
    existingUrls = getPadletPostUrls(boardPosts)
    dateCustomFieldId = getCustomFieldIdFromBoard(boardJson, dateCustomFieldName)
    guideCreated = ensureColorGuidePost(apiKey, boardId, boardPosts, dateCustomFieldId)
    createdCount = 0
    skippedCount = 0

    for event in events[:opportunityLimit]:
        title = event["title"]
        date = event["date"]
        location = event["location"]
        description = event["description"]
        link = event["link"]
        city = event.get("city", "")
        padletColor = padletCityColors.get(city)
        dateProperty = formatPadletDateProperty(date)
        customFields = (
            {dateCustomFieldId: dateProperty}
            if dateCustomFieldId and dateProperty
            else None
        )
        normalizedLink = normalizeOpportunityUrl(link)

        if shouldSkipOpportunity(title, event):
            skippedCount += 1
            continue
        if not isCompleteOpportunity(title, event):
            skippedCount += 1
            continue
        if not isFutureOrTodayOpportunity(event):
            skippedCount += 1
            continue
        if skipSchooldays and isSchoolDayOpportunity(event):
            skippedCount += 1
            continue
        if normalizedLink and normalizedLink in existingUrls:
            skippedCount += 1
            continue

        createPadletPost(
            apiKey,
            baseUrl,
            boardId,
            title,
            buildPostBody(date, location, description),
            link or None,
            padletColor,
            customFields,
        )
        if normalizedLink:
            existingUrls.add(normalizedLink)
        createdCount += 1

    return guideCreated, createdCount, skippedCount


def formatPublishResult(guideCreated, createdCount, skippedCount):
    if guideCreated or createdCount:
        guideText = " Created the color guide post." if guideCreated else ""
        skippedText = f" Skipped {skippedCount} duplicate, past, or incomplete event(s)." if skippedCount else ""
        return (
            f"Padlet board updated successfully.{guideText} "
            f"Created {createdCount} volunteer post(s).{skippedText}"
        )
    return "The Padlet board is up to date. No new posts were created."


def formatPadletError(action, exc):
    message = str(exc)
    lowerMessage = message.lower()
    connectionErrorTerms = (
        "ssl",
        "connectionpool",
        "connection pool",
        "max retries",
        "timed out",
        "timeout",
        "remote end closed",
        "eof occurred",
        "unexpected_eof",
        "connection aborted",
        "failed to establish a new connection",
    )
    if any(term in lowerMessage for term in connectionErrorTerms):
        if "sammamish" not in lowerMessage and "galaxydigital" not in lowerMessage:
            if "padlet" in lowerMessage:
                return f"{action}: Could not connect to Padlet. Please check your internet connection and try again."
            return f"{action}: Could not connect to the volunteer site. Please check your internet connection and try again."
        return (
            f"{action}: Could not connect to the Sammamish volunteer site. "
            "Please try again, or uncheck Sammamish and use Seattle only."
        )
    if "INVALID_API_KEY" in message or "API key is invalid" in message:
        return f"{action}: The Padlet API key is invalid. Please check your API key and try again."
    if "CUSTOM_PROPERTIES_MISSING" in message:
        return (
            f"{action}: Padlet says a required post field is missing. "
            "Please make custom fields optional, then try again."
        )
    if "401" in message:
        return f"{action}: Padlet rejected the API key. Please check your API key and board access."
    if "404" in message:
        return f"{action}: Padlet could not find that board. Please check the board ID."
    return f"{action}: {message}"


def parseOpportunityLimit(limitText):
    try:
        opportunityLimit = int(limitText.strip())
    except ValueError:
        return None

    if opportunityLimit < 1:
        return None
    return opportunityLimit


def parseSelectedCities(seattleSelected, sammamishSelected):
    selectedCities = []
    if seattleSelected:
        selectedCities.append("Seattle")
    if sammamishSelected:
        selectedCities.append("Sammamish")
    return selectedCities


def loadSavedSettings():
    settingsSourcePath = settingsPath if settingsPath.exists() else legacySettingsPath
    if not settingsSourcePath.exists():
        return {}

    try:
        return json.loads(settingsSourcePath.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def writeSavedSettings(savedSettings):
    if not savedSettings:
        deleteSavedSettings()
        return

    settingsPath.parent.mkdir(parents=True, exist_ok=True)
    settingsPath.write_text(json.dumps(savedSettings, indent=2), encoding="utf-8")
    try:
        settingsPath.chmod(0o600)
    except OSError:
        pass


def deleteSavedSettings():
    try:
        settingsPath.unlink()
    except FileNotFoundError:
        pass


def loadSavedCredentials():
    savedSettings = loadSavedSettings()
    if not isinstance(savedSettings, dict):
        return "", ""

    apiKey = str(savedSettings.get("apiKey", "")).strip()
    boardId = str(savedSettings.get("boardId", "")).strip()
    return apiKey, boardId


def loadSavedAgreement():
    savedSettings = loadSavedSettings()
    if not isinstance(savedSettings, dict):
        return False
    return savedSettings.get("agreementAccepted") is True


def saveCredentials(apiKey, boardId):
    apiKey = apiKey.strip()
    boardId = boardId.strip()
    if not apiKey or not boardId:
        return

    savedSettings = loadSavedSettings()
    if not isinstance(savedSettings, dict):
        savedSettings = {}
    savedSettings = {
        **savedSettings,
        "apiKey": apiKey,
        "boardId": boardId,
    }
    writeSavedSettings(savedSettings)


def deleteSavedCredentials():
    savedSettings = loadSavedSettings()
    if not isinstance(savedSettings, dict):
        return
    savedSettings.pop("apiKey", None)
    savedSettings.pop("boardId", None)
    writeSavedSettings(savedSettings)


def saveAgreementAccepted():
    savedSettings = loadSavedSettings()
    if not isinstance(savedSettings, dict):
        savedSettings = {}
    savedSettings["agreementAccepted"] = True
    writeSavedSettings(savedSettings)


def applyCredentialSavePreference(apiKey, boardId, shouldSave):
    if shouldSave:
        saveCredentials(apiKey, boardId)
    else:
        deleteSavedCredentials()


def createActionButton(parent, text, command, width=32, font=fontButton, padx=18, pady=10):
    """Creates a button-like label with reliable colors on macOS Tk."""
    button = tk.Label(
        parent,
        text=text,
        fg=textColor,
        bg=buttonColor,
        font=font,
        padx=padx,
        pady=pady,
        width=width,
        bd=1,
        relief="solid",
        cursor="hand2",
        takefocus=True,
    )
    button.isEnabled = True

    def runCommand(event=None):
        if not button.isEnabled:
            return
        button.configure(bg=buttonHoverColor)
        command()

    def onEnter(event=None):
        if button.isEnabled:
            button.configure(bg=buttonHoverColor)

    def onLeave(event=None):
        if button.isEnabled:
            button.configure(bg=buttonColor)

    def onPress(event=None):
        if button.isEnabled:
            button.configure(bg=buttonPressedColor)

    button.bind("<Enter>", onEnter)
    button.bind("<Leave>", onLeave)
    button.bind("<ButtonPress-1>", onPress)
    button.bind("<ButtonRelease-1>", runCommand)
    button.bind("<Return>", runCommand)
    button.bind("<space>", runCommand)
    button.bind("<FocusIn>", lambda event: button.configure(relief="ridge"))
    button.bind("<FocusOut>", lambda event: button.configure(relief="solid"))
    return button


def setActionButtonEnabled(button, isEnabled):
    button.isEnabled = isEnabled
    button.configure(
        bg=buttonColor if isEnabled else buttonDisabledColor,
        cursor="hand2" if isEnabled else "arrow",
    )


def addFieldFocusStyle(widget, normalBg=inputColor, focusBg=inputFocusColor):
    widget.configure(
        bg=normalBg,
        fg=inputTextColor,
        insertbackground=inputTextColor,
        relief="solid",
        bd=1,
        highlightthickness=2,
        highlightbackground=normalBg,
        highlightcolor=buttonHoverColor,
    )
    widget.bind("<FocusIn>", lambda event: widget.configure(bg=focusBg))
    widget.bind("<FocusOut>", lambda event: widget.configure(bg=normalBg))
    return widget


# ----------------------------
# UI construction
# ----------------------------

def main():
    root = tk.Tk()
    root.title(windowTitle)
    root.geometry(windowGeometry)
    root.configure(bg=bgColor)
    if appIconPath.exists():
        try:
            root.iconphoto(True, tk.PhotoImage(file=str(appIconPath)))
        except tk.TclError:
            pass
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    pageCanvas = tk.Canvas(root, bg=bgColor, highlightthickness=0)
    pageScrollbar = tk.Scrollbar(root, orient="vertical", command=pageCanvas.yview)
    pageFrame = tk.Frame(pageCanvas, bg=bgColor)
    pageFrameWindow = pageCanvas.create_window((0, 0), window=pageFrame, anchor="nw")
    pageCanvas.configure(yscrollcommand=pageScrollbar.set)
    pageCanvas.grid(row=0, column=0, sticky="NSEW")
    pageScrollbar.grid(row=0, column=1, sticky="NS")

    def updateScrollRegion(event=None):
        pageCanvas.configure(scrollregion=pageCanvas.bbox("all"))

    def resizePageFrame(event):
        pageCanvas.itemconfigure(pageFrameWindow, width=event.width)

    def scrollPage(event):
        eventNumber = getattr(event, "num", None)
        eventDelta = getattr(event, "delta", 0)
        if eventNumber == 4:
            pageCanvas.yview_scroll(-1, "units")
        elif eventNumber == 5:
            pageCanvas.yview_scroll(1, "units")
        elif eventDelta:
            direction = -1 if eventDelta > 0 else 1
            pageCanvas.yview_scroll(direction, "units")

    pageFrame.bind("<Configure>", updateScrollRegion)
    pageCanvas.bind("<Configure>", resizePageFrame)
    root.bind_all("<MouseWheel>", scrollPage)
    root.bind_all("<Button-4>", scrollPage)
    root.bind_all("<Button-5>", scrollPage)

    appFrame = tk.Frame(pageFrame, bg=bgColor)
    appFrame.pack(fill="both", expand=True, padx=56, pady=(28, 32))

    # Tk variables make it easy to read user input later.
    apiKeyVar = tk.StringVar(root)
    boardID = tk.StringVar(root)
    opportunityLimitVar = tk.StringVar(root, value="20")
    seattleSelectedVar = tk.BooleanVar(root, value=True)
    sammamishSelectedVar = tk.BooleanVar(root, value=True)
    skipSchooldaysVar = tk.BooleanVar(root, value=False)
    savedApiKey, savedBoardId = loadSavedCredentials()
    savedAgreementAccepted = loadSavedAgreement()
    apiKeyVar.set(savedApiKey)
    boardID.set(savedBoardId)
    saveCredentialsVar = tk.BooleanVar(root, value=bool(savedApiKey or savedBoardId))
    developerModeVar = tk.BooleanVar(root, value=False)
    editableEventRows = []
    actionButtons = []

    # ----------------------------
    # Header
    # ----------------------------

    heading = tk.Frame(appFrame, bg=bgColor)
    heading.grid_columnconfigure(0, weight=1)
    heading.grid_columnconfigure(1, weight=0)
    headingTextFrame = tk.Frame(heading, bg=bgColor)
    headingTextFrame.grid(row=0, column=0, sticky="W")
    developerFrame = tk.Frame(heading, bg=bgColor)
    developerFrame.grid(row=0, column=1, sticky="NE", padx=(18, 0))

    titleLabel = tk.Label(
        headingTextFrame,
        text="Harvest Opportunities",
        font=fontTitle,
        fg=textColor,
        bg=bgColor,
        anchor="w",
        justify="left",
    )
    titleLabel.pack(anchor="w")

    authorLabel = tk.Label(
        headingTextFrame,
        text="Review new Seattle and Sammamish opportunities, edit them, then publish to Padlet.",
        font=fontSubtitle,
        fg=mutedTextColor,
        bg=bgColor,
        anchor="w",
        justify="left",
    )
    authorLabel.pack(anchor="w", pady=(4, 0))

    workflowFrame = tk.Frame(headingTextFrame, bg=bgColor)
    workflowFrame.pack(anchor="w", fill="x", pady=(18, 0))

    workflowSteps = (
        ("1", "Connect Padlet"),
        ("2", "Review Opportunities"),
        ("3", "Publish Updates"),
    )
    for stepNumber, stepText in workflowSteps:
        stepFrame = tk.Frame(workflowFrame, bg=panelColor, padx=12, pady=8, bd=1, relief="solid")
        stepFrame.pack(side="left", padx=(0, 10))
        tk.Label(
            stepFrame,
            text=stepNumber,
            font=fontBodyBold,
            fg=inputTextColor,
            bg=inputFocusColor,
            width=2,
        ).pack(side="left", padx=(0, 8))
        tk.Label(
            stepFrame,
            text=stepText,
            font=fontBodyBold,
            fg=textColor,
            bg=panelColor,
        ).pack(side="left")

    developerToggle = tk.Checkbutton(
        developerFrame,
        text="Developer Mode",
        font=fontSmallButton,
        fg=textColor,
        bg=bgColor,
        activebackground=bgColor,
        activeforeground=textColor,
        selectcolor=bgColor,
        variable=developerModeVar,
    )
    developerToggle.pack(side="right")

    heading.pack(fill="x", pady=(0, 20))

    # ----------------------------
    # Agreement checkbox (gates the rest of the UI)
    # ----------------------------

    # We use a BooleanVar so maintainers can check state if needed.
    userAgreementVar = tk.BooleanVar(root, value=savedAgreementAccepted)

    def openUserAgreement():
        agreementWindow = tk.Toplevel(root)
        agreementWindow.title("User Agreement")
        agreementWindow.geometry("760x520+220+180")
        agreementWindow.configure(bg=bgColor)
        agreementWindow.transient(root)

        agreementWindowFrame = tk.Frame(
            agreementWindow,
            bg=appSurfaceColor,
            padx=18,
            pady=18,
        )
        agreementWindowFrame.pack(fill="both", expand=True, padx=18, pady=18)
        agreementWindowFrame.grid_columnconfigure(0, weight=1)
        agreementWindowFrame.grid_rowconfigure(1, weight=1)

        tk.Label(
            agreementWindowFrame,
            text="User Agreement",
            font=fontLabel,
            fg=textColor,
            bg=appSurfaceColor,
        ).grid(row=0, column=0, columnspan=2, sticky="W", pady=(0, 10))

        agreementBody = tk.Text(
            agreementWindowFrame,
            wrap="word",
            font=fontSmall,
            fg=inputTextColor,
            bg=inputColor,
            bd=0,
            padx=12,
            pady=10,
        )
        agreementBody.insert("1.0", userAgreementText)
        agreementBody.configure(state="disabled")
        agreementBody.grid(row=1, column=0, sticky="NSEW")

        agreementBodyScrollbar = tk.Scrollbar(
            agreementWindowFrame,
            orient="vertical",
            command=agreementBody.yview,
        )
        agreementBodyScrollbar.grid(row=1, column=1, sticky="NS")
        agreementBody.configure(yscrollcommand=agreementBodyScrollbar.set)

        closeButton = tk.Button(
            agreementWindowFrame,
            text="Close",
            font=fontSmallButton,
            fg=textColor,
            bg=buttonColor,
            activeforeground=textColor,
            activebackground=buttonHoverColor,
            command=agreementWindow.destroy,
            padx=12,
            pady=6,
        )
        closeButton.grid(row=2, column=0, columnspan=2, sticky="E", pady=(12, 0))

    agreementFrame = tk.Frame(appFrame, bg=appSurfaceColor, padx=18, pady=18, bd=1, relief="solid")
    agreementFrame.grid_columnconfigure(0, weight=1)

    tk.Label(
        agreementFrame,
        text="Before you continue",
        font=fontLabel,
        fg=textColor,
        bg=appSurfaceColor,
    ).grid(row=0, column=0, sticky="W", pady=(0, 8))

    tk.Label(
        agreementFrame,
        text="Please read the agreement before using the app.",
        font=fontBody,
        fg=mutedTextColor,
        bg=appSurfaceColor,
    ).grid(row=1, column=0, sticky="W", pady=(0, 12))

    agreementAcceptRow = tk.Frame(agreementFrame, bg=appSurfaceColor)
    agreementAcceptRow.grid(row=2, column=0, sticky="W")

    userAgreement = tk.Checkbutton(
        agreementAcceptRow,
        text="I have read and agree to the",
        font=fontLabel,
        fg=textColor,
        bg=appSurfaceColor,
        activebackground=appSurfaceColor,
        activeforeground=textColor,
        selectcolor=appSurfaceColor,
        variable=userAgreementVar,
    )
    userAgreement.pack(side="left")

    userAgreementLink = tk.Label(
        agreementAcceptRow,
        text="user agreement",
        font=(fontFamily, 16, "bold underline"),
        fg=warningColor,
        bg=appSurfaceColor,
        cursor="hand2",
    )
    userAgreementLink.pack(side="left", padx=(4, 0))
    userAgreementLink.bind("<Button-1>", lambda event: openUserAgreement())

    tk.Label(
        agreementAcceptRow,
        text=".",
        font=fontLabel,
        fg=textColor,
        bg=appSurfaceColor,
    ).pack(side="left")

    if not savedAgreementAccepted:
        agreementFrame.pack(fill="x", pady=(0, 18))

    # ----------------------------
    # API entry panel
    # ----------------------------

    apiFrame = tk.Frame(appFrame, bg=appSurfaceColor, padx=18, pady=18, bd=1, relief="solid")
    apiFrame.grid_columnconfigure(1, weight=1)
    apiFrame.grid_columnconfigure(2, weight=0)

    apiKeyLabel = tk.Label(
        apiFrame,
        text="Enter your API key:",
        font=fontLabel,
        fg=textColor,
        bg=appSurfaceColor,
    )
    apiKeyLabel.grid(row=0, column=0, sticky="E", padx=(0, 14), pady=(0, 12))

    apiKeyEntry = tk.Entry(
        apiFrame,
        font=fontInput,
        fg=inputTextColor,
        bg=inputColor,
        insertbackground=inputTextColor,
        textvariable=apiKeyVar,
        width=58,
    )
    addFieldFocusStyle(apiKeyEntry)
    apiKeyEntry.grid(row=0, column=1, sticky="EW", pady=(0, 10))

    boardIDLabel = tk.Label(
        apiFrame,
        text="Enter your Board ID:",
        font=fontLabel,
        fg=textColor,
        bg=appSurfaceColor,
    )
    boardIDLabel.grid(row=1, column=0, sticky="E", padx=(0, 14), pady=(0, 12))

    boardIDEntry = tk.Entry(
        apiFrame,
        font=fontInput,
        fg=inputTextColor,
        bg=inputColor,
        insertbackground=inputTextColor,
        textvariable=boardID,
        width=58,
    )
    addFieldFocusStyle(boardIDEntry)
    boardIDEntry.grid(row=1, column=1, sticky="EW", pady=(0, 10))

    opportunityLimitLabel = tk.Label(
        apiFrame,
        text="Number of opportunities to update:",
        font=fontLabel,
        fg=textColor,
        bg=appSurfaceColor,
    )
    opportunityLimitLabel.grid(row=3, column=0, sticky="W", padx=(0, 14), pady=(0, 12))

    opportunityLimitEntry = tk.Entry(
        apiFrame,
        font=fontInput,
        fg=inputTextColor,
        bg=inputColor,
        insertbackground=inputTextColor,
        textvariable=opportunityLimitVar,
        width=8,
    )
    addFieldFocusStyle(opportunityLimitEntry)
    opportunityLimitEntry.grid(row=3, column=1, sticky="W", pady=(0, 10))

    citySelectionLabel = tk.Label(
        apiFrame,
        text="Cities to extract from:",
        font=fontLabel,
        fg=textColor,
        bg=appSurfaceColor,
    )
    citySelectionLabel.grid(row=4, column=0, sticky="NW", padx=(0, 14), pady=(0, 12))

    citySelectionFrame = tk.Frame(apiFrame, bg=appSurfaceColor)
    citySelectionFrame.grid(row=4, column=1, sticky="W", pady=(0, 12))

    seattleCheckbox = tk.Checkbutton(
        citySelectionFrame,
        text="Seattle",
        font=fontBodyBold,
        fg=textColor,
        bg=appSurfaceColor,
        activebackground=appSurfaceColor,
        activeforeground=textColor,
        selectcolor=appSurfaceColor,
        variable=seattleSelectedVar,
    )
    seattleCheckbox.pack(side="left", padx=(0, 18))

    sammamishCheckbox = tk.Checkbutton(
        citySelectionFrame,
        text="Sammamish",
        font=fontBodyBold,
        fg=textColor,
        bg=appSurfaceColor,
        activebackground=appSurfaceColor,
        activeforeground=textColor,
        selectcolor=appSurfaceColor,
        variable=sammamishSelectedVar,
    )
    sammamishCheckbox.pack(side="left")

    skipSchooldaysCheckbox = tk.Checkbutton(
        apiFrame,
        text="Skip weekdays\n(keep Washington legal holidays)",
        anchor="w",
        justify="left",
        font=fontBodyBold,
        fg=textColor,
        bg=appSurfaceColor,
        activebackground=appSurfaceColor,
        activeforeground=textColor,
        selectcolor=appSurfaceColor,
        variable=skipSchooldaysVar,
    )
    skipSchooldaysCheckbox.grid(row=5, column=1, sticky="EW", pady=(0, 12))
    skipSchooldaysCheckbox.bind(
        "<Configure>",
        lambda event: skipSchooldaysCheckbox.configure(wraplength=max(1, event.width - 40)),
    )

    cityLegendFrame = tk.Frame(apiFrame, bg=appSurfaceColor)
    cityLegendFrame.grid(row=6, column=1, sticky="W", pady=(0, 10))

    def addCityLegend(parent, cityName):
        legendItem = tk.Frame(parent, bg=appSurfaceColor)
        legendItem.pack(side="left", padx=(0, 14))
        tk.Label(
            legendItem,
            text="",
            bg=cityColors[cityName]["card"],
            width=3,
            height=1,
            bd=1,
            relief="solid",
        ).pack(side="left", padx=(0, 5))
        tk.Label(
            legendItem,
            text=cityName,
            font=fontLegend,
            fg=textColor,
            bg=appSurfaceColor,
        ).pack(side="left")

    addCityLegend(cityLegendFrame, "Seattle")
    addCityLegend(cityLegendFrame, "Sammamish")

    if artworkPath.exists():
        rawArtworkImage = tk.PhotoImage(file=str(artworkPath))
        artworkImage = rawArtworkImage.subsample(3, 3)
        artworkLabel = tk.Label(apiFrame, image=artworkImage, bg=appSurfaceColor, bd=0)
        artworkLabel.image = artworkImage
        artworkLabel.rawImage = rawArtworkImage
        artworkLabel.grid(row=3, column=2, rowspan=5, sticky="E", padx=(24, 0), pady=(0, 0))

    saveCredentialsCheckbox = tk.Checkbutton(
        apiFrame,
        text="Save Padlet API key and board ID on this computer",
        font=fontBodyBold,
        fg=textColor,
        bg=appSurfaceColor,
        activebackground=appSurfaceColor,
        activeforeground=textColor,
        selectcolor=appSurfaceColor,
        variable=saveCredentialsVar,
    )
    saveCredentialsCheckbox.grid(row=2, column=1, sticky="W", pady=(0, 12))

    disclaimerLabel = tk.Label(
        apiFrame,
        text=(
            "This app does not communicate with the author and is fully open-sourced on GitHub. "
            "Saved Padlet details stay local on this computer."
        ),
        font=fontSmall,
        fg=mutedTextColor,
        bg=appSurfaceColor,
        wraplength=900,
        justify="left",
    )
    disclaimerLabel.grid(row=9, column=0, columnspan=3, sticky="W", pady=(12, 0))

    # ----------------------------
    # Volunteer results panel
    # ----------------------------

    volunteerTextFrame = tk.Frame(appFrame, bg=bgColor)

    statusLabel = tk.Label(
        volunteerTextFrame,
        text="Ready to check for volunteer opportunities.",
        font=fontBodyBold,
        fg=textColor,
        bg=panelColor,
        padx=16,
        pady=12,
        wraplength=900,
        justify="left",
    )
    statusLabel.bind(
        "<Configure>",
        lambda event: statusLabel.configure(wraplength=max(event.width - 24, 300)),
    )

    eventsFrame = tk.Frame(volunteerTextFrame, bg=bgColor)

    statusLabel.pack(fill="x", pady=(0, 8))
    eventsFrame.pack(fill="both", expand=True)

    # This label appears only when the user tries to submit without credentials.
    enterApiWarningLabel = tk.Label(
        appFrame,
        text="Please enter your Padlet API key and board ID to continue.",
        font=fontLabel,
        fg=warningColor,
        bg=bgColor,
    )

    # ----------------------------
    # Event handlers
    # ----------------------------

    def setStatus(message):
        statusLabel.configure(text=message)

    def setBusy(isBusy, message=None):
        if message:
            setStatus(message)
        for button in actionButtons:
            setActionButtonEnabled(button, not isBusy)
        root.configure(cursor="watch" if isBusy else "")
        root.update_idletasks()

    def clearEditableEvents():
        editableEventRows.clear()
        for child in eventsFrame.winfo_children():
            child.destroy()
        updateScrollRegion()

    def addEditableEvent(rowNumber, title, item):
        city = item.get("city", "")
        eventColors = cityColors.get(city, defaultEventColors)
        cardColor = eventColors["card"]
        fieldColor = eventColors["field"]

        eventCard = tk.Frame(eventsFrame, bg=cardColor, bd=1, relief="solid", padx=18, pady=16)
        eventCard.grid(row=rowNumber, column=0, sticky="EW", pady=(0, 14))
        eventCard.grid_columnconfigure(1, weight=1)
        eventsFrame.grid_columnconfigure(0, weight=1)

        fields = {
            "title": tk.StringVar(value=title),
            "date": tk.StringVar(value=item.get("date", "")),
            "location": tk.StringVar(value=item.get("location", "")),
        }
        originalValues = {
            "title": title,
            "date": item.get("date", ""),
            "location": item.get("location", ""),
            "description": item.get("description", ""),
        }
        originalLink = item.get("link", "")
        skipVar = tk.BooleanVar(root, value=False)

        headingLabel = tk.Label(
            eventCard,
            text=f"Event {rowNumber + 1}" + (f" - {city}" if city else ""),
            font=fontLabel,
            fg=textColor,
            bg=cardColor,
        )
        headingLabel.grid(row=0, column=0, sticky="W", pady=(0, 8))

        cardActions = tk.Frame(eventCard, bg=cardColor)
        cardActions.grid(row=0, column=1, sticky="E", pady=(0, 8))

        def resetEvent():
            fields["title"].set(originalValues["title"])
            fields["date"].set(originalValues["date"])
            fields["location"].set(originalValues["location"])
            descriptionBox.delete("1.0", tk.END)
            descriptionBox.insert("1.0", originalValues["description"])
            skipVar.set(False)

        openLinkButton = createActionButton(
            cardActions,
            "Open Link",
            lambda: webbrowser.open(originalLink) if originalLink else None,
            width=9,
            font=fontSmallButton,
            padx=7,
            pady=4,
        )
        openLinkButton.pack(side="right", padx=(6, 0))

        resetButton = createActionButton(
            cardActions,
            "Reset",
            resetEvent,
            width=7,
            font=fontSmallButton,
            padx=7,
            pady=4,
        )
        resetButton.pack(side="right", padx=(6, 0))

        skipCheckbox = tk.Checkbutton(
            cardActions,
            text="Skip",
            font=fontSmallButton,
            fg=textColor,
            bg=cardColor,
            activebackground=cardColor,
            activeforeground=textColor,
            selectcolor=cardColor,
            variable=skipVar,
        )
        skipCheckbox.pack(side="right")

        fieldLabels = [
            ("Event name", "title"),
            ("Date", "date"),
            ("Location", "location"),
        ]

        for fieldIndex, (labelText, fieldName) in enumerate(fieldLabels, start=1):
            tk.Label(
                eventCard,
                text=f"{labelText}:",
                font=fontBodyBold,
                fg=textColor,
                bg=cardColor,
            ).grid(row=fieldIndex, column=0, sticky="NW", padx=(0, 12), pady=(0, 8))

            eventEntry = tk.Entry(
                eventCard,
                textvariable=fields[fieldName],
                font=fontBody,
                fg=inputTextColor,
                bg=fieldColor,
                insertbackground=inputTextColor,
            )
            addFieldFocusStyle(eventEntry, fieldColor, inputFocusColor)
            if fieldName == "date":
                eventEntry.configure(
                    state="readonly",
                    readonlybackground=fieldColor,
                    cursor="arrow",
                )
            eventEntry.grid(row=fieldIndex, column=1, sticky="EW", pady=(0, 8))

        tk.Label(
            eventCard,
            text="Link:",
            font=fontBodyBold,
            fg=textColor,
            bg=cardColor,
        ).grid(row=4, column=0, sticky="NW", padx=(0, 12), pady=(0, 8))

        linkLabel = tk.Label(
            eventCard,
            text=originalLink,
            font=fontBody,
            fg=mutedTextColor,
            bg=cardColor,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        linkLabel.grid(row=4, column=1, sticky="EW", pady=(0, 8))
        linkLabel.bind(
            "<Configure>",
            lambda event: linkLabel.configure(wraplength=max(event.width - 20, 320)),
        )

        tk.Label(
            eventCard,
            text="Description:",
            font=fontBodyBold,
            fg=textColor,
            bg=cardColor,
        ).grid(row=5, column=0, sticky="NW", padx=(0, 12), pady=(0, 8))

        descriptionBox = tk.Text(
            eventCard,
            height=5,
            wrap="word",
            font=fontBody,
            fg=inputTextColor,
            bg=fieldColor,
            insertbackground=inputTextColor,
        )
        descriptionBox.insert("1.0", item.get("description", ""))
        addFieldFocusStyle(descriptionBox, fieldColor, inputFocusColor)
        descriptionBox.grid(row=5, column=1, sticky="EW", pady=(0, 8))

        editableEventRows.append({
            "fields": fields,
            "descriptionBox": descriptionBox,
            "link": originalLink,
            "city": city,
            "skipVar": skipVar,
        })

    def renderEditableEvents(volunteerDict):
        clearEditableEvents()
        if not volunteerDict:
            setStatus("The Padlet board is up to date. No new volunteer opportunities to display.")
            return

        setStatus(
            f"{len(volunteerDict)} new volunteer opportunities found. "
            "Edit the event details below, then update Padlet. Dates and links are locked to prevent errors."
        )
        for rowNumber, (title, item) in enumerate(volunteerDict.items()):
            addEditableEvent(rowNumber, title, item)

    def collectEditedEvents():
        editedEvents = []
        for row in editableEventRows:
            if row["skipVar"].get():
                continue
            fields = row["fields"]
            event = {
                "title": fields["title"].get().strip(),
                "date": fields["date"].get().strip(),
                "location": fields["location"].get().strip(),
                "description": row["descriptionBox"].get("1.0", "end-1c").strip(),
                "link": row["link"],
                "city": row.get("city", ""),
            }
            if event["title"] or event["link"]:
                editedEvents.append(event)
        return editedEvents

    def showStatusOnly(message):
        clearEditableEvents()
        setStatus(message)

    def onAgree():
        """Reveals the API and results panels once the user checks the box."""
        if userAgreementVar.get():
            saveAgreementAccepted()
            agreementFrame.pack_forget()
            apiFrame.pack(fill="x", pady=(0, 18))
            volunteerTextFrame.pack(fill="both", expand=True, pady=(0, 10))
        else:
            # If unchecked, hide panels and any warning text.
            apiFrame.pack_forget()
            volunteerTextFrame.pack_forget()
            enterApiWarningLabel.pack_forget()

    def onSubmit():
        """Validates credentials and displays volunteer opportunities."""
        apiKey = apiKeyVar.get().strip()
        board_Id = boardID.get().strip()

        if not apiKey or not board_Id:
            enterApiWarningLabel.pack()
            return

        opportunityLimit = parseOpportunityLimit(opportunityLimitVar.get())
        if opportunityLimit is None:
            enterApiWarningLabel.pack_forget()
            showStatusOnly("Please enter a positive whole number for the number of opportunities to update.")
            return

        selectedCities = parseSelectedCities(seattleSelectedVar.get(), sammamishSelectedVar.get())
        if not selectedCities:
            enterApiWarningLabel.pack_forget()
            showStatusOnly("Please select at least one city to extract volunteer opportunities from.")
            return

        # Hide warning (if shown previously).
        enterApiWarningLabel.pack_forget()
        applyCredentialSavePreference(apiKey, board_Id, saveCredentialsVar.get())

        setBusy(True, "Checking Padlet and volunteer sources...")
        try:
            volunteerDict = fetchNewVolunteerItems(
                apiKey,
                board_Id,
                opportunityLimit,
                selectedCities,
                skipSchooldaysVar.get(),
            )
            renderEditableEvents(volunteerDict)
        except Exception as exc:  # noqa: BLE001 (GUI wants a user-friendly error)
            showStatusOnly(formatPadletError("Could not check volunteer opportunities", exc))
        finally:
            setBusy(False)

    userAgreement.configure(command=onAgree)
    if savedAgreementAccepted:
        onAgree()

    submitButton = createActionButton(apiFrame, "Display Volunteer Opportunities", onSubmit)
    actionButtons.append(submitButton)
    submitButton.grid(row=7, column=1, sticky="W", pady=(14, 0))

    def updatePadlet():
        apiKey = apiKeyVar.get().strip()
        board_Id = boardID.get().strip()
        if not apiKey or not board_Id:
            enterApiWarningLabel.pack()
            return

        opportunityLimit = parseOpportunityLimit(opportunityLimitVar.get())
        if opportunityLimit is None:
            enterApiWarningLabel.pack_forget()
            setStatus("Please enter a positive whole number for the number of opportunities to update.")
            return

        enterApiWarningLabel.pack_forget()
        applyCredentialSavePreference(apiKey, board_Id, saveCredentialsVar.get())

        setBusy(True, "Updating Padlet board...")
        try:
            editedEvents = collectEditedEvents()[:opportunityLimit]
            guideCreated, createdCount, skippedCount = publishVolunteerEvents(
                apiKey,
                board_Id,
                editedEvents,
                opportunityLimit,
                skipSchooldaysVar.get(),
            )
            showStatusOnly(formatPublishResult(guideCreated, createdCount, skippedCount))
        except Exception as exc:  # noqa: BLE001 (GUI wants a user-friendly error)
            setStatus(formatPadletError("Could not update Padlet board", exc))
        finally:
            setBusy(False)

    updatePadletButton = createActionButton(apiFrame, "Update Padlet Board", updatePadlet)
    actionButtons.append(updatePadletButton)
    updatePadletButton.grid(row=8, column=1, sticky="W", pady=(10, 0))

    def runDirectDeveloperUpdate():
        apiKey = apiKeyVar.get().strip()
        board_Id = boardID.get().strip()
        if not apiKey or not board_Id:
            enterApiWarningLabel.pack()
            return

        opportunityLimit = parseOpportunityLimit(opportunityLimitVar.get())
        if opportunityLimit is None:
            enterApiWarningLabel.pack_forget()
            showStatusOnly("Please enter a positive whole number for the number of opportunities to update.")
            return

        selectedCities = parseSelectedCities(seattleSelectedVar.get(), sammamishSelectedVar.get())
        if not selectedCities:
            enterApiWarningLabel.pack_forget()
            showStatusOnly("Please select at least one city to extract volunteer opportunities from.")
            return

        enterApiWarningLabel.pack_forget()
        applyCredentialSavePreference(apiKey, board_Id, saveCredentialsVar.get())

        setBusy(True, "Developer mode: fetching opportunities and updating Padlet without editing...")
        try:
            volunteerDict = fetchNewVolunteerItems(
                apiKey,
                board_Id,
                opportunityLimit,
                selectedCities,
                skipSchooldaysVar.get(),
            )
            events = [
                {
                    **item,
                    "title": title,
                }
                for title, item in volunteerDict.items()
            ]
            guideCreated, createdCount, skippedCount = publishVolunteerEvents(
                apiKey,
                board_Id,
                events,
                opportunityLimit,
                skipSchooldaysVar.get(),
            )
            showStatusOnly(formatPublishResult(guideCreated, createdCount, skippedCount))
        except Exception as exc:  # noqa: BLE001 (GUI wants a user-friendly error)
            showStatusOnly(formatPadletError("Could not run developer direct update", exc))
        finally:
            setBusy(False)

    def runNotificationTest():
        try:
            show_reminder()
        except Exception as exc:  # noqa: BLE001 (GUI wants a user-friendly error)
            setStatus(f"Could not show test notification: {exc}")

    notificationTestButton = createActionButton(
        developerFrame,
        "Test Notification",
        runNotificationTest,
        width=15,
        font=fontSmallButton,
        padx=8,
        pady=5,
    )
    directUpdateButton = createActionButton(
        developerFrame,
        "Direct Update",
        runDirectDeveloperUpdate,
        width=12,
        font=fontSmallButton,
        padx=8,
        pady=5,
    )
    actionButtons.extend([notificationTestButton, directUpdateButton])

    def updateDeveloperControls():
        if developerModeVar.get():
            directUpdateButton.pack(side="right", padx=(8, 0))
            notificationTestButton.pack(side="right", padx=(8, 0))
        else:
            notificationTestButton.pack_forget()
            directUpdateButton.pack_forget()

    developerToggle.configure(command=updateDeveloperControls)
    updateDeveloperControls()

    def onClose():
        applyCredentialSavePreference(apiKeyVar.get(), boardID.get(), saveCredentialsVar.get())
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", onClose)

    root.mainloop()


if __name__ == "__main__":
    main()
