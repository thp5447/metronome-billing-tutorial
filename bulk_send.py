import requests

events = [
    {"warehouse": "aws", "size": "small", "hours": "744", "transaction_id": "raindrop-demo-066"},
    {"warehouse": "aws", "size": "medium", "hours": "592", "transaction_id": "raindrop-demo-067"},
    {"warehouse": "aws", "size": "large", "hours": "128", "transaction_id": "raindrop-demo-068"},
    {"warehouse": "gcp", "size": "small", "hours": "1298", "transaction_id": "raindrop-demo-069"},
    {"warehouse": "gcp", "size": "medium", "hours": "394", "transaction_id": "raindrop-demo-070"},
    {"warehouse": "gcp", "size": "large", "hours": "241", "transaction_id": "raindrop-demo-071"}
]

url = "http://127.0.0.1:5050/api/ingress"
ingest_alias = "michaelscott@dunder.com"
customer_id = "88ed0956-d480-4c63-864b-2150354f6b23"
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
