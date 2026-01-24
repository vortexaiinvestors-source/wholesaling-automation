# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app_production.py .
COPY scrapers/ scrapers/ || true
COPY config/ config/ || true

# Create .env file if not exists
RUN touch .env

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run production FastAPI app (NOT the stub app.py)
CMD ["python", "-m", "uvicorn", "app_production:app", "--host", "0.0.0.0", "--port", "8000"]