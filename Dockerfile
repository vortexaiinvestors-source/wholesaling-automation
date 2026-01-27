FROM python:3.11-slim

WORKDIR /app

# Clear pip cache and upgrade pip
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY scrapers /app/scrapers
COPY sources.json /app/sources.json
COPY . .

CMD ["uvicorn", "app_production:app", "--host", "0.0.0.0", "--port", "8080"]
