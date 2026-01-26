URGENT_WORDS = [
    "urgent", "must sell", "asap", "reduced",
    "moving", "divorce", "estate", "quick sale"
]

def score_deal(deal: dict) -> dict:
    price = deal.get("price", 0) or 0
    title = (deal.get("title") or "").lower()
    description = (deal.get("description") or "").lower()
    text = f"{title} {description}"

    # Profit score
    if price < 10000:
        profit_score = 40
    elif price < 50000:
        profit_score = 30
    elif price < 200000:
        profit_score = 20
    else:
        profit_score = 10

    # Urgency score
    urgency_score = 0
    for word in URGENT_WORDS:
        if word in text:
            urgency_score += 10
    urgency_score = min(urgency_score, 40)

    # Risk score
    risk_score = 0
    if price < 500:
        risk_score += 40
    if len(title) < 5:
        risk_score += 20
    if "wire transfer" in text or "crypto only" in text:
        risk_score += 50

    # Final AI score
    ai_score = profit_score + urgency_score - risk_score

    return {
        "profit_score": profit_score,
        "urgency_score": urgency_score,
        "risk_score": risk_score,
        "ai_score": ai_score
    }
