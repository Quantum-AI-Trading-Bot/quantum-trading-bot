#!/bin/bash
set -e

export DISPLAY=:1

echo "=== IB Gateway Window Handler ==="

# Find all IB Gateway related windows
echo "Finding IB Gateway windows..."
xdotool search --name "Gateway" | while read window_id; do
    echo "Found Gateway window: $window_id"
    xdotool windowraise $window_id
    sleep 1
    xdotool key Tab
    sleep 1
done

# Find and handle Login Messages window
LOGIN_WINDOW=$(xdotool search --name "Login Messages" | head -1)
if [ -n "$LOGIN_WINDOW" ]; then
    echo "Found Login Messages window: $LOGIN_WINDOW"
    xdotool windowraise $LOGIN_WINDOW
    sleep 2
    xdotool key space  # Dismiss any dialog
    sleep 1
    xdotool key Return  # Confirm
fi

echo "Window handling complete"