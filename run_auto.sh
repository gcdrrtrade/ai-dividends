#!/bin/bash

# Configuration
PROJECT_DIR="/Users/gonnsimss/Documents/BUSINESS/LLC/PROYECTOS/AI_DIVIDENDS"
GIT_MSG="Auto-update stock data $(date +'%Y-%m-%d')"
LOG_FILE="$PROJECT_DIR/update_log.txt"

# Navigate to project
cd "$PROJECT_DIR" || exit

# Log start
echo "----------------------------------------" >> "$LOG_FILE"
echo "Starting update: $(date)" >> "$LOG_FILE"

# Run Analyzer (using correct python environment)
# Trying venv first, then system python
if [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD analyzer.py >> "$LOG_FILE" 2>&1

# Check if stocks_data.json changed
if git diff --quiet stocks_data.json; then
    echo "No changes in data." >> "$LOG_FILE"
else
    echo "Data changed. Committing..." >> "$LOG_FILE"
    git add stocks_data.json
    git commit -m "$GIT_MSG"
    git push origin main >> "$LOG_FILE" 2>&1
    echo "Pushed to GitHub." >> "$LOG_FILE"
fi

echo "Finished update: $(date)" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"
