#!/usr/bin/env bash
# Exit on any error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate


# Create superuser automatically or seed database if completely empty
python manage.py shell << 'PYEOF'
from django.contrib.auth import get_user_model
from django.core.management import call_command
import sys

User = get_user_model()
if User.objects.count() == 0:
    print("Brand new database detected. Running seed command to populate catalog and admin user...")
    try:
        call_command('seed')
        print("Database seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        sys.exit(1)
else:
    print("Database already populated. Skipping seed.")
PYEOF
