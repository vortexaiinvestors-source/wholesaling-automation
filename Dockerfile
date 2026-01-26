FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ ADD THESE TWO LINES
COPY scrapers /app/scrapers
COPY sources.json /app/sources.json

# (keep this)
COPY . .

CMD ["uvicorn", "app_production:app", "--host", "0.0.0.0", "--port", "8080"]
