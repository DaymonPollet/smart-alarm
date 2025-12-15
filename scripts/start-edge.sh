#!/bin/bash

echo "Starting Smart Alarm Edge Services..."

cd "$(dirname "$0")/.."

echo "Starting API server..."
cd edge
python api.py > logs/api.log 2>&1 &
API_PID=$!
echo "API server started (PID: $API_PID)"

sleep 2

echo "Starting edge application..."
python main.py > logs/main.log 2>&1 &
MAIN_PID=$!
echo "Edge application started (PID: $MAIN_PID)"

echo $API_PID > /tmp/smart-alarm-api.pid
echo $MAIN_PID > /tmp/smart-alarm-main.pid

echo "All services started successfully!"
echo "API: http://localhost:8080"
echo "Logs: edge/logs/"
