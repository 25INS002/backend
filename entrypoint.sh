# exit immediately if a command fails
set -e

# Init logic removed as data is mounted fresh


exec "$@"

# Run migrations
python manage.py makemigrations
python manage.py migrate


# Start server
python manage.py runserver 0.0.0.0:8010
