import requests

events = [
    {"warehouse": "aws", "size": "medium", "hours": "592", "transaction_id": "ep3-demo-011"},
    {"warehouse": "aws", "size": "large", "hours": "128", "transaction_id": "ep3-demo-012"},
    {"warehouse": "gcp", "size": "small", "hours": "1298", "transaction_id": "ep3-demo-013"},
    {"warehouse": "gcp", "size": "medium", "hours": "394", "transaction_id": "ep3-demo-014"},
    {"warehouse": "gcp", "size": "large", "hours": "241", "transaction_id": "ep3-demo-015"},

]

url = "http://127.0.0.1:5050/api/ingress"
customer_id = "demo_mscott@dunder.com"

for e in events:
    payload = {
        "event_type": "computation",
        "properties": {
            "warehouse": e["warehouse"],
            "size": e["size"],
            "hours": e["hours"],
        },
        "transaction_id": e["transaction_id"],
        "customer_id": customer_id
    }
    r = requests.post(url, json=payload)
    print(r.json())
