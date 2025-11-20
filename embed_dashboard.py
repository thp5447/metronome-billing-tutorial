import requests
url = "https://api.metronome.com/v1/dashboards/getEmbeddableUrl"
from config import METRONOME_BEARER_TOKEN
payload = {
    "customer_id": "343793d8-79b6-4b8e-9a37-4664605dd2b3",
    "dashboard": "invoices",
}

headers = {
    "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json()["data"]["url"])


payload = {
    "customer_id": "343793d8-79b6-4b8e-9a37-4664605dd2b3",
    "dashboard": "commits_and_credits",
    
}
headers = {
    "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json()["data"]["url"])