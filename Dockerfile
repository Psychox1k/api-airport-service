FROM python:3.12-slim
LABEL maintainer="zhyharevk777.official@gmail.com"

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
# netcat-openbsd is required for the wait-for-db.sh script to check port availability
RUN apt-get update && apt-get install -y \
    bash \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy executable scripts to a system path to avoid volume overwrite issues
# and grant execution permissions
COPY entrypoint.sh wait-for-db.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/wait-for-db.sh

# Create directories for static and media files, and set up a non-root user
RUN mkdir -p /files/media /files/static \
    && adduser --disabled-password --no-create-home my_user \
    && chown -R my_user:my_user /app /files/media /files/static \
    && chmod -R 755 /files/media /files/static

# Switch to non-root user for security
USER my_user

# Execute the entrypoint script (now located in /usr/local/bin/)
ENTRYPOINT ["entrypoint.sh"]