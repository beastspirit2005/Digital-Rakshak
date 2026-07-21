# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies required for OpenCV, psycopg2, ffmpeg for Whisper AI, and building certain Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.docker.txt /app/requirements.txt
RUN pip install --upgrade pip
# We use --default-timeout=1000 to prevent connection drops on heavy AI packages
RUN pip install --default-timeout=1000 -r requirements.txt

# Copy the massive PyTorch models directly into the image
# (This bypasses GitHub size limits as the models live permanently inside this Docker layer)
COPY models/ /app/models/

# Copy the rest of the application
COPY . /app/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
