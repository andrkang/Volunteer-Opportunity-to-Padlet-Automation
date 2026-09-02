import requests
from bs4 import BeautifulSoup
import feedparser
import time
from datetime import datetime, timezone
import html as htmlModule
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

url = "https://sammamish.galaxydigital.com/need/"
seattleRSS = "https://www.trumba.com/calendars/volunteer-1.rss"
volunteerTimeZoneName = "America/Los_Angeles"
volunteerTimeZone = ZoneInfo(volunteerTimeZoneName)
headers = {"User-Agent": "VolunteerHarvester/0.1"}
sammamishHeaders = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "close",
}

def removeSpace(title):
    result = title[0]
    for index in range(1, len(title)):
        if (not title[index-1].isspace()) and title[index].isupper():
            result += " "
        result += title[index]
    return result 

def getOpportunities(url, headers, sign):
    html = requests.get(url, headers=headers, timeout=20).text
    soup = BeautifulSoup(html, "lxml")

    volunteerDict = dict()
    for a in soup.select("a"):
        title = a.get_text(strip=True)
        link = a.get("href")
        if title and link and sign in link.lower():
            if title[:18] == "Get Connected Icon":
                title = title[18:]
            title = removeSpace(title)
                    
            if title not in volunteerDict:
                volunteerDict[title] = link

    for opportunity in volunteerDict:
        print(opportunity)
        print(volunteerDict[opportunity])
        print("\n")

    return volunteerDict

def getSammamishOpportunities(maxPages=5):
    """Returns Sammamish opportunities in the same shape as the Seattle RSS parser."""
    detailLinks = []
    seenLinks = set()

    for pageNumber in range(1, maxPages + 1):
        pageUrl = url if pageNumber == 1 else f"{url}?page={pageNumber}"
        try:
            resp = getSammamishPage(pageUrl)
        except Exception:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        pageLinks = []
        for aTag in soup.select("a[href]"):
            href = aTag.get("href", "")
            if "detail" not in href.lower():
                continue
            detailUrl = urljoin(url, href)
            if detailUrl in seenLinks:
                continue
            seenLinks.add(detailUrl)
            pageLinks.append((aTag.get_text(" ", strip=True), detailUrl))

        if not pageLinks:
            break
        detailLinks.extend(pageLinks)

    volunteerDict = {}
    for fallbackTitle, detailUrl in detailLinks:
        try:
            detail = getSammamishOpportunityDetail(detailUrl, fallbackTitle)
        except Exception:
            continue
        title = detail["title"]
        uniqueTitle = title
        duplicateNumber = 2
        while uniqueTitle in volunteerDict:
            uniqueTitle = f"{title} ({duplicateNumber})"
            duplicateNumber += 1
        volunteerDict[uniqueTitle] = detail

    return volunteerDict

def getSammamishPage(pageUrl, timeout=20, retries=2):
    lastError = None
    for attemptNumber in range(retries + 1):
        try:
            resp = requests.get(pageUrl, headers=sammamishHeaders, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            lastError = exc
            if attemptNumber < retries:
                time.sleep(0.4)
    raise lastError

def getRssText(feedUrl, timeout=20, retries=2):
    lastError = None
    for attemptNumber in range(retries + 1):
        try:
            resp = requests.get(feedUrl, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            lastError = exc
            if attemptNumber < retries:
                time.sleep(0.4)
    raise lastError

def getSammamishOpportunityDetail(detailUrl, fallbackTitle):
    resp = getSammamishPage(detailUrl)

    soup = BeautifulSoup(resp.text, "html.parser")
    title = extractSammamishTitle(soup, fallbackTitle)
    pageText = soup.get_text("\n", strip=True)
    dateText = extractSammamishDate(pageText, fallbackTitle)
    location = extractSammamishLocation(pageText)
    description = extractSammamishDescription(soup, pageText)

    return {
        "title": title,
        "link": detailUrl,
        "date": dateText,
        "description": description,
        "location": location,
        "city": "Sammamish",
        "sortDate": parseFlexibleDate(dateText),
    }

def extractSammamishTitle(soup, fallbackTitle):
    for selector in ("h1", "h2", ".need-title", ".title"):
        tag = soup.select_one(selector)
        if tag:
            title = tag.get_text(" ", strip=True)
            if title:
                return removeSpace(title)
    return removeSpace(fallbackTitle).strip()

def cleanSammamishDateText(dateText):
    normalizedDate = re.sub(r"\s+", " ", dateText).strip()
    normalizedDate = re.sub(r"\bSept\.?", "Sep", normalizedDate, flags=re.IGNORECASE)
    monthPattern = (
        r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
    )
    dateMatch = re.search(
        rf"(?:\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?,?\s+)?"
        rf"((?:{monthPattern})\.?\s+\d{{1,2}},\s+\d{{4}}"
        rf"(?:,?\s+\d{{1,2}}(?::\d{{2}})?\s*(?:a\.?m\.?|p\.?m\.?))?)",
        normalizedDate,
        flags=re.IGNORECASE,
    )
    if dateMatch:
        return re.sub(r"\bSept\.?", "Sep", dateMatch.group(1), flags=re.IGNORECASE)
    return normalizedDate

def extractSammamishDate(pageText, fallbackTitle):
    combinedText = f"{fallbackTitle}\n{pageText}"
    lines = [line.strip() for line in combinedText.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        match = re.search(r"Happens\s+On\s+(.+)", line, flags=re.IGNORECASE)
        if match:
            dateText = re.sub(r"\s+", " ", match.group(1)).strip()
            if index + 1 < len(lines) and re.search(r"\d", lines[index + 1]) and re.search(r"am|pm|:", lines[index + 1], flags=re.IGNORECASE):
                return cleanSammamishDateText(f"{dateText} {lines[index + 1].strip()}")
            return cleanSammamishDateText(dateText)

    patterns = [
        r"Runs\s+Until\s+([^\n]+)",
        r"Date\s*:?\s*([^\n]+)",
        r"([A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4}[^\n]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, combinedText, flags=re.IGNORECASE)
        if match:
            return cleanSammamishDateText(match.group(1))
    return ""

def extractSammamishLocation(pageText):
    patterns = [
        r"Location\s*:?\s*([^\n]+(?:\n[^\n]+){0,2})",
        r"Address\s*:?\s*([^\n]+(?:\n[^\n]+){0,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, pageText, flags=re.IGNORECASE)
        if match:
            lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
            return ", ".join(lines)
    return "Sammamish"

def extractSammamishDescription(soup, pageText):
    metaDescription = soup.select_one("meta[property='og:description'], meta[name='description']")
    if metaDescription and metaDescription.get("content"):
        return metaDescription.get("content", "").strip()

    paragraphs = [
        paragraph.get_text(" ", strip=True)
        for paragraph in soup.select("p")
        if paragraph.get_text(" ", strip=True)
    ]
    if paragraphs:
        return "\n\n".join(paragraphs[:3])

    lines = [line.strip() for line in pageText.splitlines() if line.strip()]
    return "\n".join(lines[:8])

def parseFlexibleDate(dateStr):
    cleanedDate = re.sub(r"\s+", " ", dateStr.replace("\xa0", " ")).strip()
    cleanedDate = re.sub(r"\bSept\.?", "Sep", cleanedDate, flags=re.IGNORECASE)
    cleanedDate = re.sub(r"\s+at\s+", " ", cleanedDate, flags=re.IGNORECASE)
    cleanedDate = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", cleanedDate, flags=re.IGNORECASE)
    cleanedDate = re.sub(r"(\d)(am|pm)", r"\1 \2", cleanedDate, flags=re.IGNORECASE)

    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", cleanedDate):
        isoDate = cleanedDate.rstrip("Z").replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(isoDate, fmt)
            except ValueError:
                pass

    dateStart = re.split(r"\s+(?:through|until|to)\s+|\s*[-–—]\s*", cleanedDate, maxsplit=1, flags=re.IGNORECASE)[0]
    dateCandidates = [
        dateStart,
        re.sub(r"\s+[A-Z]{2,5}$", "", dateStart),
    ]
    formats = [
        "%d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S",
        "%B %d, %Y %I:%M %p",
        "%B %d, %Y %I %p",
        "%B %d, %Y",
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y %I %p",
        "%b %d, %Y",
    ]
    for dateCandidate in dateCandidates:
        for fmt in formats:
            try:
                return datetime.strptime(dateCandidate, fmt)
            except ValueError:
                pass
    match = re.search(r"([A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})", dateStart)
    if match:
        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(match.group(1), fmt)
            except ValueError:
                pass
    return datetime.max

def getLocalTimezoneInfo():
    volunteerNow = datetime.now(volunteerTimeZone)
    return 0, volunteerNow.tzname() or "PT"

def convertGMT(dateStr, shift, timeZone):
    dateStr = dateStr.strip()
    if not dateStr:
        return ""

    match = re.search(r"(\d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2}) GMT$", dateStr)
    if not match:
        return dateStr

    try:
        parsedDate = datetime.strptime(match.group(1), "%d %b %Y %H:%M:%S")
    except ValueError:
        return dateStr

    convertedDate = parsedDate.replace(tzinfo=timezone.utc).astimezone(volunteerTimeZone)
    return f"{convertedDate.strftime('%d %b %Y %H:%M:%S')} {convertedDate.tzname() or timeZone}"

#Date: 08 Mar 2026 16:00:00 GMT

def getOpportunitiesFromRSS(url, shift, tzAbbrev, maxOpportunities=20):
    rssText = getRssText(url)
    feed = feedparser.parse(rssText)
    if feed.bozo:
        print("Feed had issues:", repr(feed.bozo_exception))

    volunteerDict = dict()

    for entry in feed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        date = convertGMT(entry.get("published", "").strip(), shift, tzAbbrev)
        if title and link and date and (maxOpportunities is None or len(volunteerDict) < maxOpportunities):
            volunteerDict[title] = dict()
            volunteerDict[title]["link"] = link
            volunteerDict[title]["date"] = date
            volunteerDict[title]['description'] = entry.get("description", "").strip()
            volunteerDict[title]['location'], volunteerDict[title]['description'] = parseLocationAndDescription(entry.get("description", "").strip())
            volunteerDict[title]["city"] = "Seattle"
            volunteerDict[title]["sortDate"] = parseFlexibleDate(date)

    return volunteerDict

def sortOpportunitiesByDate(volunteerDict):
    def parseDate(item):
        if isinstance(item.get("sortDate"), datetime):
            return item["sortDate"]
        dateStr = item.get("date", "")
        parts = dateStr.strip().split()
        if len(parts) < 5:
            return parseFlexibleDate(dateStr)
        dateNoTz = " ".join(parts[:4])
        try:
            return datetime.strptime(dateNoTz, "%d %b %Y %H:%M:%S")
        except ValueError:
            return datetime.max

    sortedItems = sorted(
        volunteerDict.items(),
        key=lambda item: parseDate(item[1])
    )

    # Convert back to dict (preserves this order)
    sortedDict = dict(sortedItems)

    return sortedDict

def parseLocationAndDescription(descriptionHtml):
    soup = BeautifulSoup(descriptionHtml, "html.parser")
    for br in soup.find_all('br'):
        br.replace_with('\n')
    rawText = soup.get_text('\n', strip=True)
    rawText = htmlModule.unescape(rawText).replace("\xa0", " ")
    lines = [ln.strip() for ln in rawText.split('\n') if ln.strip()]
    location = lines[0] if len(lines) >= 1 else ""
    descriptionStart = 1
    if len(lines) >= 3 and looksLikeEventDateLine(lines[1]):
        descriptionStart = 2
    description = "\n".join(lines[descriptionStart:]) if len(lines) > descriptionStart else ""
    return location, description

def looksLikeEventDateLine(line):
    monthPattern = r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
    return bool(
        re.search(monthPattern, line, flags=re.IGNORECASE)
        and re.search(r"\b\d{4}\b", line)
        and re.search(r"\b(?:am|pm|a\.m\.|p\.m\.)\b|\d\s*[–—-]\s*\d", line, flags=re.IGNORECASE)
    )
