#!/bin/sh
set -e

pip install --no-cache-dir -r /app/requirements.txt
exec python /app/app.py
