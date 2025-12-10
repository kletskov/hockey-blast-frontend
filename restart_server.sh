#!/bin/zsh

# Define the port
PORT=5001

echo "Checking for process on port $PORT..."
PID=$(lsof -ti:$PORT)

if [ -n "$PID" ]; then
  echo "Killing process $PID on port $PORT..."
  kill -9 $PID
  echo "Process killed."
else
  echo "No process found on port $PORT."
fi

# Navigate to the frontend directory
cd /Users/pavelkletskov/hockey-blast-prod/hockey-blast-frontend

# Activate virtual environment and start app
echo "Starting Flask application..."
source .venv/bin/activate
python app.py
