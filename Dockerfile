#Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy only requirements first (for caching)
COPY requirements.txt ./requirements.txt

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the Django project
COPY server/ ./server/

WORKDIR /app/server

# Expose port
EXPOSE 8010

# Copy entrypoint script
COPY entrypoint.sh /app/server/entrypoint.sh
RUN chmod +x /app/server/entrypoint.sh
RUN mkdir -p /app/server && chmod -R 777 /app/server
# Run entrypoint script
CMD ["sh","./entrypoint.sh"]