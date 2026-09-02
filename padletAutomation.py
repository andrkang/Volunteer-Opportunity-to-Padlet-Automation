import requests

headers = {"User-Agent": "VolunteerHarvester/0.1"}

def createPadletPost(apiKey, baseUrl, boardId, subject, body, attachmentUrl=None, color=None, customFields=None):
    url = f"{baseUrl.rstrip('/')}/boards/{boardId}/posts"

    headers = {
        "X-API-KEY": apiKey,
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json"
    }

    if attachmentUrl is not None:
        attachmentUrl = str(attachmentUrl).strip()
        if attachmentUrl == "":
            attachmentUrl = None

    if color is not None:
        color = str(color).strip().lower()
        if color == "":
            color = None

    payload = {
        "data": {
            "type": "post",
            "attributes": {
                "content": {
                    "subject": subject,
                    "body": body,
                    **({"attachment": {"url": attachmentUrl}} if attachmentUrl else {})
                },
                **({"color": color} if color else {}),
                **({"custom_fields": customFields} if customFields else {})
            }
        }
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)

    if resp.status_code >= 400:
        raise RuntimeError(f"Create post failed {resp.status_code}: {resp.text}")

    return resp.json()

def getBoardFromPadlet(apiKey, baseUrl, boardId):
    url = f"{baseUrl.rstrip('/')}/boards/{boardId}"

    headers = {
        "X-API-KEY": apiKey,
        "Accept": "application/vnd.api+json",
    }

    params = {"include": "posts,sections"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)

    if resp.status_code >= 400:
        raise RuntimeError(f"Get posts failed {resp.status_code}: {resp.text}")

    return resp.json()

def getPostFromPadlet(apiKey, baseUrl, boardId):
    boardJson = getBoardFromPadlet(apiKey, baseUrl, boardId)

    included = boardJson.get("included", [])

    posts = [obj for obj in included if obj.get("type") == "post"]

    return posts

def normalizeCustomFieldName(fieldName):
    return "".join(char.lower() for char in str(fieldName) if char.isalnum())

def objectContainsNormalizedValue(obj, targetValue):
    if not targetValue:
        return False
    if isinstance(obj, dict):
        return any(objectContainsNormalizedValue(value, targetValue) for value in obj.values())
    if isinstance(obj, list):
        return any(objectContainsNormalizedValue(value, targetValue) for value in obj)
    return normalizeCustomFieldName(obj) == targetValue

def objectContainsDateType(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if normalizeCustomFieldName(key) in ("type", "fieldtype", "datatype", "inputtype"):
                if normalizeCustomFieldName(value) in ("date", "datetime"):
                    return True
            if objectContainsDateType(value):
                return True
    if isinstance(obj, list):
        return any(objectContainsDateType(value) for value in obj)
    return False

def objectContainsRequiredFlag(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if normalizeCustomFieldName(key) in ("required", "isrequired"):
                if value is True:
                    return True
            if objectContainsRequiredFlag(value):
                return True
    if isinstance(obj, list):
        return any(objectContainsRequiredFlag(value) for value in obj)
    return False

def findReadableFieldName(obj):
    if isinstance(obj, dict):
        for key in ("name", "label", "title", "key", "displayName", "display_name"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in obj.values():
            foundName = findReadableFieldName(value)
            if foundName:
                return foundName
    if isinstance(obj, list):
        for value in obj:
            foundName = findReadableFieldName(value)
            if foundName:
                return foundName
    return None

def getCustomFieldRecordsFromBoard(boardJson):
    records = []
    seenFieldIds = set()

    def addRecord(fieldId, fieldData):
        if not fieldId:
            return
        fieldId = str(fieldId)
        if fieldId in seenFieldIds:
            return
        seenFieldIds.add(fieldId)
        records.append({
            "id": fieldId,
            "name": findReadableFieldName(fieldData) or str(fieldId),
            "isDate": objectContainsDateType(fieldData),
            "isRequired": objectContainsRequiredFlag(fieldData),
            "data": fieldData,
        })

    possibleBoardAttributes = [
        boardJson.get("attributes", {}),
        boardJson.get("data", {}).get("attributes", {}),
    ]

    for boardAttributes in possibleBoardAttributes:
        customFields = (
            boardAttributes.get("customFields")
            or boardAttributes.get("custom_fields")
            or boardAttributes.get("fields")
        )

        if isinstance(customFields, dict):
            for fieldId, fieldData in customFields.items():
                if isinstance(fieldData, dict):
                    addRecord(
                        fieldData.get("id")
                        or fieldData.get("uuid")
                        or fieldData.get("fieldId")
                        or fieldData.get("customFieldId")
                        or fieldId,
                        fieldData,
                    )
                else:
                    addRecord(fieldId, {"name": fieldData})
        elif isinstance(customFields, list):
            for fieldData in customFields:
                if isinstance(fieldData, dict):
                    addRecord(
                        fieldData.get("id")
                        or fieldData.get("uuid")
                        or fieldData.get("fieldId")
                        or fieldData.get("customFieldId"),
                        fieldData,
                    )

    for includedItem in boardJson.get("included", []):
        if includedItem.get("type") in ("customField", "custom_field", "field"):
            addRecord(
                includedItem.get("id"),
                includedItem.get("attributes", includedItem),
            )

    return records

def getCustomFieldNamesFromBoard(boardJson):
    return [record["name"] for record in getCustomFieldRecordsFromBoard(boardJson)]

def getRequiredDateCustomFieldIdsFromBoard(boardJson):
    return [
        record["id"]
        for record in getCustomFieldRecordsFromBoard(boardJson)
        if record["isRequired"] and record["isDate"]
    ]

def getCustomFieldIdFromBoard(boardJson, fieldName):
    targetName = normalizeCustomFieldName(fieldName)
    fieldRecords = getCustomFieldRecordsFromBoard(boardJson)

    for record in fieldRecords:
        if normalizeCustomFieldName(record["name"]) == targetName:
            return record["id"]
        if objectContainsNormalizedValue(record["data"], targetName):
            return record["id"]

    dateFieldRecords = [record for record in fieldRecords if record["isDate"]]
    if targetName == "eventdate" and len(dateFieldRecords) == 1:
        return dateFieldRecords[0]["id"]

    def findInObject(obj, fallbackId=None):
        if isinstance(obj, dict):
            fieldNames = [
                obj.get("name"),
                obj.get("label"),
                obj.get("title"),
                obj.get("key"),
                obj.get("displayName"),
                obj.get("display_name"),
            ]
            if any(normalizeCustomFieldName(name) == targetName for name in fieldNames if name):
                return (
                    obj.get("id")
                    or obj.get("uuid")
                    or obj.get("fieldId")
                    or obj.get("customFieldId")
                    or fallbackId
                )

            for key, value in obj.items():
                if normalizeCustomFieldName(key) == targetName and isinstance(value, str):
                    return value
                foundId = findInObject(value, key if isinstance(value, dict) else None)
                if foundId:
                    return foundId

        if isinstance(obj, list):
            for value in obj:
                foundId = findInObject(value)
                if foundId:
                    return foundId

        return None

    return findInObject(boardJson)

def getPostById(apiKey, baseUrl, postId, boardId):
    posts = getPostFromPadlet(apiKey, baseUrl , boardId)
    for post in posts:
        if post.get("id") == postId:
            return post
    return None

def checkIfPostIsEqual(apiKey, baseUrl, postId, boardId, newLink):
    post = getPostById(apiKey, baseUrl, postId, boardId)
    return post.get("attributes", {}).get("content", {}).get("attachment", {}).get("url") == newLink
