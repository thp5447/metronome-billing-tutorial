import csv
import json
from io import StringIO

def csv_to_pricing_payload(csv_file_path: str,
                           metric_name: str,
                           product_name: str,
                           rate_card_name: str,
                           effective_at: str):

    with open(csv_file_path, "r") as f:
        csv_text = f.read()

    f = StringIO(csv_text)
    reader = csv.DictReader(f)
    rates = []
    for row in reader:
        rates.append({
            "region": row["region"],
            "provider": row["provider"],
            "price_cents": int(row["price_cents"])
        })

    payload = {
        "metric_name": metric_name,
        "group_keys": ["region", "provider"],
        "property_filters": [
            {"name": "region", "exists": True},
            {"name": "provider", "exists": True}
        ],
        "product": {
            "name": product_name,
            "type": "USAGE"
        },
        "rate_card": {
            "name": rate_card_name,
            "effective_at": effective_at,
            "rates": rates
        }
    }
    with open("extended_rates.json", "w") as f:
        json.dump(payload, f, indent=2)

    return payload


payload = csv_to_pricing_payload(
    csv_file_path="proposed_rates.csv",  
    metric_name="Raindrop Data Ingress2",
    product_name="Data Ingress Product",
    rate_card_name="Data Ingress Rate Card",
    effective_at="2025-11-16T00:00:00Z"
)

