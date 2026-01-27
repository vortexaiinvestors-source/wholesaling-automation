from fastapi import FastAPI
app = FastAPI()
@app.get('/api/health')
async def health():
    return {"status": "ok", "message": "VortexAI backend is running"}
@app.get('/')
async def root():
    return {"message": "VortexAI Real Estate Scraper API"}
