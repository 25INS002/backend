# exit immediately if a command fails
set -e

# Run migrations
python manage.py makemigrations
python manage.py migrate


# Start server
python manage.py runserver 0.0.0.0:8000
