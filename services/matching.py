def match_buyers(deal: dict, buyers: list) -> list:
    matches = []

    for buyer in buyers:
        if buyer["asset_type"] != deal["asset_type"]:
            continue

        if buyer["max_price"] < deal["price"]:
            continue

        if buyer["city"].lower() not in deal["city"].lower():
            continue

        if buyer["role"] not in ["buyer_paid", "enterprise"]:
            continue

        if deal["ai_score"] < 60:
            continue

        matches.append({
            "deal_id": deal["id"],
            "buyer_id": buyer["id"]
        })

    return matches
