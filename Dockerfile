FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 🔥 FORCE install multipart (even if pip cache fails)
RUN pip install --no-cache-dir python-multipart

COPY scrapers /app/scrapers
COPY sources.json /app/sources.json
COPY . .

CMD ["uvicorn", "app_production:app", "--host", "0.0.0.0", "--port", "8080"]
