FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app_production.py .

# Create empty directories
RUN mkdir -p scrapers config logs

EXPOSE 8000

# Simple health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Start app
CMD ["uvicorn", "app_production:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]