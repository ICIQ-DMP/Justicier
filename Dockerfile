# Use official lightweight Python image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (optional, common ones)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    locales && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i '/es_ES.UTF-8/s/^# //' /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=es_ES.UTF-8

ENV LANG=es_ES.UTF-8
ENV LANGUAGE=es_ES:es
ENV LC_ALL=es_ES.UTF-8

# Install Python dependencies
COPY pyproject.toml .
RUN pip install .

COPY version.txt .

# Copy application code
COPY src ./src

# Run the application
ENTRYPOINT ["python", "src/main.py"]
