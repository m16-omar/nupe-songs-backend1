#!/usr/bin/env bash
# Exit on any error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate


# Force database seed to guarantee admin user and catalog creation
echo "Running database seed..."
python manage.py seed
echo "Database seed complete."
