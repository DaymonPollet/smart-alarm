#!/bin/bash

echo "Stopping Smart Alarm Edge Services..."

if [ -f /tmp/smart-alarm-api.pid ]; then
    API_PID=$(cat /tmp/smart-alarm-api.pid)
    kill $API_PID 2>/dev/null
    rm /tmp/smart-alarm-api.pid
    echo "API server stopped"
fi

if [ -f /tmp/smart-alarm-main.pid ]; then
    MAIN_PID=$(cat /tmp/smart-alarm-main.pid)
    kill $MAIN_PID 2>/dev/null
    rm /tmp/smart-alarm-main.pid
    echo "Edge application stopped"
fi

pkill -f "python.*api.py" 2>/dev/null
pkill -f "python.*main.py" 2>/dev/null

echo "All services stopped"
