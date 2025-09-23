#!/bin/bash

# FundLink Web Setup Script

echo "🚀 Setting up FundLink Web Backend..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser (skip if already exists)..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@fundlink.org', 'admin')
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
"

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd fundlink_web"
echo "  source .venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "Admin interface: http://localhost:8000/admin/"
echo "API endpoints: http://localhost:8000/api/"
echo "Username: admin, Password: admin"