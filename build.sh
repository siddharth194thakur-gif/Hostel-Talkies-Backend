#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate --noinput || echo "[build.sh Warning] Migrations skipped or encountered an error."

# Auto-seed initial admin superuser and default hostels if database is fresh
python manage.py setup_initial_data || echo "[build.sh Warning] setup_initial_data skipped or encountered an error."

# Safely import and normalize authentic VBSPU academic study resources
python manage.py import_vbspu_resources
python manage.py normalize_study_resources

