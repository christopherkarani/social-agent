#!/bin/bash
set -e

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Create config directory if it doesn't exist
mkdir -p /app/config

# Set proper permissions
chown -R app:app /app/logs /app/config

# Load environment variables from .env file if it exists
if [ -f /app/.env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' /app/.env | xargs)
fi

# Validate required environment variables
if [ -z "$PERPLEXITY_API_KEY" ]; then
    echo "ERROR: PERPLEXITY_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$BLUESKY_USERNAME" ]; then
    echo "ERROR: BLUESKY_USERNAME environment variable is required"
    exit 1
fi

if [ -z "$BLUESKY_PASSWORD" ]; then
    echo "ERROR: BLUESKY_PASSWORD environment variable is required"
    exit 1
fi

echo "Starting Bluesky Crypto Agent..."
echo "Configuration:"
echo "  - Posting interval: ${POSTING_INTERVAL_MINUTES:-30} minutes"
echo "  - Max execution time: ${MAX_EXECUTION_TIME_MINUTES:-25} minutes"
echo "  - Log level: ${LOG_LEVEL:-INFO}"
echo "  - Content themes: ${CONTENT_THEMES:-Bitcoin,Ethereum,DeFi,NFT,Altcoins}"

# Execute the main command
exec "$@"