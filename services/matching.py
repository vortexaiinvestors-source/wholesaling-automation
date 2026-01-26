def match_buyers(deal: dict, buyers: list) -> list:
    matches = []

    for buyer in buyers:

        # Asset type check
        if buyer.get("asset_types") != deal.get("asset_type"):
            continue

        # Budget check
        if buyer.get("max_budget", 0) < deal.get("price", 0):
            continue

        # Location check (optional)
        buyer_loc = (buyer.get("location") or "").lower()
        deal_loc = (deal.get("location") or "").lower()
        if buyer_loc and buyer_loc not in deal_loc:
            continue

        # AI quality gate
        if deal.get("ai_score", 0) < 60:
            continue

        matches.append({
            "deal_id": deal.get("id"),
            "buyer_id": buyer.get("id")
        })

    return matches
