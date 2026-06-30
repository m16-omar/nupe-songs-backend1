#!/usr/bin/env bash
# Exit on any error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate


# Create superuser automatically from environment variables (if not exists)
python manage.py shell << 'PYEOF'
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully.")
else:
    print(f"Superuser '{username}' already exists or no password set, skipping.")
PYEOF
