#!/bin/bash
# ------------------------------------------
# Auto update dailyInsight repo and log time
# Runs from cron
# ------------------------------------------

LOG_FILE=~/ProjectsLog/cron_dailyInsight_update.log
PROJECT_DIR=~/dailyInsight

{
    echo "$(date '+%Y-%m-%d %H:%M:%S') --- Start git pull ---"
    cd "$PROJECT_DIR" || { echo "Error: cannot enter $PROJECT_DIR"; exit 1; }
    git pull
    echo "$(date '+%Y-%m-%d %H:%M:%S') --- End git pull ---"
    echo
} >> "$LOG_FILE" 2>&1
