# Question Paper Studio - Production Dockerfile
FROM python:3.12-slim

# Install system dependencies: Chromium (for headless PDF generation) and Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    tesseract-ocr \
    tesseract-ocr-tam \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=5050 \
    CHROME_BIN=/usr/bin/chromium

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5050

# Run with Gunicorn production server
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "3", "--timeout", "120", "app:app"]
