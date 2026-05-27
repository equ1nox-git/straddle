#!/bin/bash
# Pulls Inbox + Projects reminders from MacBook via osascript → writes to b450 cache
RESULT=$(ssh -o ConnectTimeout=5 thomasb@100.120.230.78 "osascript <<'APPLE'
tell application \"Reminders\"
    set output to \"[\"
    set listNames to {\"Inbox\", \"Projects\"}
    repeat with listName in listNames
        try
            set theList to list listName
            set remList to every reminder of theList whose completed is false
            repeat with rem in remList
                set remName to name of rem
                set output to output & \"{\\\"list\\\":\\\"\" & listName & \"\\\",\\\"summary\\\":\\\"\" & remName & \"\\\"},\"
            end repeat
        end try
    end repeat
    if length of output > 1 then
        set output to text 1 thru -2 of output
    end if
    return output & \"]\"
end tell
APPLE" 2>/dev/null)

if [ -n "$RESULT" ] && [ "$RESULT" != "[]" ]; then
    echo "$RESULT" > /tmp/reminders_mac.json
    echo "$(date): synced $(echo "$RESULT" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))') reminders" >> /tmp/reminders_sync.log
fi
