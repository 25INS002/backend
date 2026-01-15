# exit immediately if a command fails
set -e

INIT_CONTENT="/app/data-init/content"
CONTENT_DIR="/app/server/content"

INIT_MEDIA="/app/data-init/media"
MEDIA_DIR="/app/server/media"

# Ensure dirs exist (Coolify mounts them)
mkdir -p "$CONTENT_DIR" "$MEDIA_DIR"

# Init content
if [ -z "$(ls -A "$CONTENT_DIR" 2>/dev/null)" ]; then
  echo "Initializing content..."
  cp -r "$INIT_CONTENT"/* "$CONTENT_DIR"/
fi

# Init media
if [ -z "$(ls -A "$MEDIA_DIR" 2>/dev/null)" ]; then
  echo "Initializing media..."
  cp -r "$INIT_MEDIA"/* "$MEDIA_DIR"/
fi

exec "$@"

# Run migrations
python manage.py makemigrations
python manage.py migrate


# Start server
python manage.py runserver 0.0.0.0:8010
