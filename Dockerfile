FROM python:3.11
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "uvicorn", "app_production:app", "--host", "0.0.0.0", "--port", "8080"]
