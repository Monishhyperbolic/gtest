#!/bin/bash
set -o errexit

# Install dependencies from root
pip install -r requirements.txt

# Move into project directory to run commands
cd filesharing

# Django commands
python manage.py collectstatic --no-input
python manage.py migrate