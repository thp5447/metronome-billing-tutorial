import requests

events = [
    {"warehouse": "aws", "size": "small", "hours": "744", "transaction_id": "raindrop-demo-041"},
    {"warehouse": "aws", "size": "medium", "hours": "592", "transaction_id": "raindrop-demo-042"},
    {"warehouse": "aws", "size": "large", "hours": "128", "transaction_id": "raindrop-demo-043"},
    {"warehouse": "gcp", "size": "small", "hours": "1298", "transaction_id": "raindrop-demo-044"},
    {"warehouse": "gcp", "size": "medium", "hours": "394", "transaction_id": "raindrop-demo-045"},
    {"warehouse": "gcp", "size": "large", "hours": "241", "transaction_id": "raindrop-demo-046"}
]

url = "http://127.0.0.1:5050/api/ingress"
ingest_alias = "tpackard@dunder.com"
customer_id = "747d48ef-5e5e-46ec-8033-55546c7fd743"
for event in events:
    payload = {
        "event_type": "computation",
        "properties": {
            "warehouse": event["warehouse"],
            "size": event["size"],
            "hours": event["hours"],
        },
        "transaction_id": event["transaction_id"],
        "ingest_alias": ingest_alias,
        "customer_id": customer_id
    }
    r = requests.post(url, json=payload)
    print(r.json())
