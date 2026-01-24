from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
from scrapers.database_connector import DatabaseConnector
from scrapers.email_automation import EmailAutomation

logger = logging.getLogger(__name__)
app = FastAPI(title="Real Estate Wholesaling API")

db = DatabaseConnector()
email = EmailAutomation()

@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "vortexai-api"
    })

@app.post("/api/properties/store")
async def store_property(property_data: dict):
    success = db.store_property(property_data)
    return JSONResponse({
        "success": success,
        "address": property_data.get('address')
    })

@app.get("/api/properties/pending")
async def get_pending_properties():
    properties = db.get_pending_properties()
    return JSONResponse({
        "count": len(properties),
        "properties": properties
    })

@app.post("/api/email/alert")
async def send_alert(buyer_email: str, property_data: dict):
    success = email.send_property_alert(buyer_email, property_data)
    return JSONResponse({
        "success": success,
        "recipient": buyer_email
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
