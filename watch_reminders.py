"""Create a user-run macOS Reminders import with the dose data encoded as JSON."""
import base64
from datetime import datetime
import json
from uuid import NAMESPACE_URL, uuid5


def reminders_script(entries, owner):
    rows = []
    for start, name, detail in dict.fromkeys(entries):
        if isinstance(start, datetime):
            uid = uuid5(NAMESPACE_URL, repr((owner, start.isoformat(), name, detail)))
            rows.append(dict(year=start.year, month=start.month, day=start.day, hour=start.hour,
                             minute=start.minute, name=name, body=f"{detail}\nReco ID {uid}"))
    payload = base64.b64encode(json.dumps(rows, ensure_ascii=False).encode()).decode()
    # Only base64 data is inserted into executable source. Patient text stays in JSON.
    return TEMPLATE.replace("PAYLOAD", payload)


TEMPLATE = '''use framework "Foundation"
use scripting additions

set encoded to current application's NSData's alloc()'s initWithBase64EncodedString:"PAYLOAD" options:0
set itemsToAdd to current application's NSJSONSerialization's JSONObjectWithData:encoded options:0 |error|:(missing value)
tell application "Reminders"
    if not (exists list "Reco") then make new list with properties {name:"Reco"}
    set destination to list "Reco"
    set savedNotes to body of every reminder of destination
    repeat with i from 0 to ((itemsToAdd's |count|()) as integer) - 1
        set row to itemsToAdd's objectAtIndex:i
        set noteText to (row's objectForKey:"body") as text
        if savedNotes does not contain noteText then
            set dueTime to current date
            set day of dueTime to 1
            set year of dueTime to (row's objectForKey:"year") as integer
            set month of dueTime to (row's objectForKey:"month") as integer
            set day of dueTime to (row's objectForKey:"day") as integer
            set time of dueTime to ((row's objectForKey:"hour") as integer) * 3600 + ((row's objectForKey:"minute") as integer) * 60
            make new reminder at end of reminders of destination with properties {name:(row's objectForKey:"name") as text, body:noteText, due date:dueTime, remind me date:dueTime}
            set end of savedNotes to noteText
        end if
    end repeat
end tell
'''
