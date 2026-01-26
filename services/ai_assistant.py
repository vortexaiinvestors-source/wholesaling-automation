from datetime import datetime

GOOD_TAGS = [
    "underpriced", "motivated_seller", "fast_flip", "high_demand", "rare_item"
]

RISK_TAGS = [
    "scam_risk", "low_info", "too_good_to_be_true", "payment_risk"
]


def analyze_deal(deal: dict) -> dict:
    """
    Level 4 AI Assistant (no external AI needed yet).
    Produces:
    - summary
    - recommendation
    - tags
    - buyer_message template
    - seller_message template
    - confidence (0-100)
    """

    asset_type = (deal.get("asset_type") or "").lower()
    location = deal.get("location") or ""
    price = deal.get("price") or 0
    name = deal.get("name") or ""
    desc = (deal.get("description") or "")
    ai_score = int(deal.get("ai_score") or deal.get("score") or 0)
    profit_score = int(deal.get("profit_score") or 0)
    urgency_score = int(deal.get("urgency_score") or 0)
    risk_score = int(deal.get("risk_score") or 0)

    text = f"{name} {desc}".lower()

    tags = []

    # Tag logic
    if urgency_score >= 20:
        tags.append("motivated_seller")
    if profit_score >= 35:
        tags.append("underpriced")
    if risk_score >= 40:
        tags.append("scam_risk")
    if len(name.strip()) < 5 or len(desc.strip()) < 15:
        tags.append("low_info")

    # Asset-specific tags
    if asset_type in ["luxury_items"] and ("rolex" in text or "omega" in text):
        tags.append("rare_item")
    if asset_type in ["real_estate"] and ("foreclosure" in text or "as-is" in text):
        tags.append("fast_flip")

    # Build summary
    summary = (
        f"{asset_type.upper()} deal in {location} for ${price:,.0f}. "
        f"AI Score={ai_score} (Profit={profit_score}, Urgency={urgency_score}, Risk={risk_score}). "
        f"Title: {name}"
    )

    # Recommendation logic
    confidence = 70

    if ai_score >= 80 and risk_score < 30:
        recommendation = "HIGH PRIORITY: Contact buyer(s) immediately and request proof + availability."
        confidence = 85
    elif ai_score >= 60 and risk_score < 40:
        recommendation = "GOOD: Worth sending to matching buyers. Ask for more details and verify listing."
        confidence = 75
    elif risk_score >= 40:
        recommendation = "CAUTION: High risk signals. Verify hard before engaging (avoid wire/crypto-only)."
        confidence = 65
    else:
        recommendation = "LOW: Not strong enough. Keep in inventory but do not prioritize."
        confidence = 55

    # Templates
    buyer_message = (
        f"🔥 New {asset_type.replace('_',' ')} deal found!\n"
        f"📍 {location}\n"
        f"💲 Price: ${price:,.0f}\n"
        f"⭐ Score: {ai_score}/100\n\n"
        f"Summary: {name}\n"
        f"Reply YES for details / hold request."
    )

    seller_message = (
        "Hi! I saw your listing and I’m interested.\n"
        "Is it still available?\n"
        "Can you share:\n"
        "- more photos\n"
        "- reason for sale\n"
        "- best time to view\n"
        "- any issues to disclose\n"
    )

    return {
        "summary": summary,
        "recommendation": recommendation,
        "tags": ",".join(tags),
        "buyer_message": buyer_message,
        "seller_message": seller_message,
        "confidence": confidence,
        "created_at": datetime.utcnow().isoformat()
    }
