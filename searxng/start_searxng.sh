#!/bin/bash
# Script to run SearXNG locally

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
if [ -f "$DIR/local/py3/bin/activate" ]; then
  source "$DIR/local/py3/bin/activate"
elif [ -f "$DIR/venv/bin/activate" ]; then
  source "$DIR/venv/bin/activate"
else
  echo "Error: Virtual environment not found. Please run 'make install' first."
  exit 1
fi


# Set a random secret key for the local instance if you want to modify settings
export SEARXNG_SECRET="$(openssl rand -hex 32)"

# Run the local server
echo "Starting SearXNG local server. It should be available at http://127.0.0.1:8888"
exec searxng-run
