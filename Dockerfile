FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_production.py .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app_production:app --host 0.0.0.0 --port $PORT"]
