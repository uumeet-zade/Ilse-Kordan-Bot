#!/bin/bash
echo "Starting Ilse Kordan Bot in the background..."

# Stop existing instances if they are running
pkill -f "python3 bot.py"

# Start the Discord Bot
nohup python3 bot.py > bot.log 2>&1 &
echo "Discord Bot started. Logs at bot.log"

echo "Bot is live! You can safely close your terminal."
