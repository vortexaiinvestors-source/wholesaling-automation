URGENT_WORDS = [
    "urgent", "must sell", "asap", "reduced",
    "moving", "divorce", "estate", "quick sale",
    "motivated", "need gone", "price reduced"
]

def score_deal(deal: dict) -> dict:
    price = deal.get("price", 0) or 0

    # Your system uses "name", not "title"
    title = (deal.get("name") or "").lower()
    description = (deal.get("description") or "").lower()
    asset_type = (deal.get("asset_type") or "").lower()

    text = f"{title} {description}"

    # --------------------
    # PROFIT SCORE
    # --------------------
    if asset_type in ["cars", "luxury_items", "wholesale_products"]:
        if price < 8000:
            profit_score = 45
        elif price < 20000:
            profit_score = 35
        elif price < 50000:
            profit_score = 25
        else:
            profit_score = 10

    elif asset_type in ["real_estate", "business_assets"]:
        if price < 120000:
            profit_score = 45
        elif price < 250000:
            profit_score = 35
        elif price < 500000:
            profit_score = 25
        else:
            profit_score = 10

    else:
        if price < 10000:
            profit_score = 35
        elif price < 50000:
            profit_score = 25
        else:
            profit_score = 10

    # --------------------
    # URGENCY SCORE
    # --------------------
    urgency_score = 0
    for word in URGENT_WORDS:
        if word in text:
            urgency_score += 10

    urgency_score = min(urgency_score, 40)

    # --------------------
    # RISK SCORE
    # --------------------
    risk_score = 0

    if price <= 0:
        risk_score += 30

    if len(title) < 4:
        risk_score += 15

    if "wire transfer" in text or "crypto only" in text or "gift cards" in text:
        risk_score += 60

    if price < 500:
        risk_score += 25

    # --------------------
    # FINAL SCORE
    # --------------------
    ai_score = profit_score + urgency_score - risk_score

    # clamp
    if ai_score < 0:
        ai_score = 0
    if ai_score > 100:
        ai_score = 100

    return {
        "profit_score": profit_score,
        "urgency_score": urgency_score,
        "risk_score": risk_score,
        "ai_score": ai_score
    }
