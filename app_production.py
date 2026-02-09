#!/usr/bin/env python3
from fastapi import FastAPI

app = FastAPI(title="VortexAI", version="1.0")

@app.get("/health")
async def health():
      return {"status": "ok", "service": "vortexai"}

@app.get("/")
async def root():
      return {"message": "VortexAI API Running"}

if __name__ == "__main__":
      import uvicorn
      uvicorn.run(app, host="0.0.0.0", port=8080)
