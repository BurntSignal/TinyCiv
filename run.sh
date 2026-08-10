#!/usr/bin/with-contenv bashio
set -e

echo "Starting TinyCiv..."
exec python3 /opt/tinyciv/server.py
