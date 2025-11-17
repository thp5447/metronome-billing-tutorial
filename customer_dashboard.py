from services.metronome_client import MetronomeClient
import os
import requests

METRONOME_BEARER_TOKEN = os.environ.get("METRONOME_BEARER_TOKEN")

url = "https://api.metronome.com/v1/contracts/customerBalances/list"

payload = {
    "customer_id": "7df46c71-45e4-43bd-9a14-c898a2b02efc",
    "include_ledgers": True,
    "include_balance": True
}

headers = {
    "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
resp = response.json()

item = resp["data"][0]

total_commit_cents = item["access_schedule"]["schedule_items"][0]["amount"]

remaining_balance_cents = item["balance"]

# Convert to dollars
total_commit_usd = total_commit_cents / 100
remaining_balance_usd = remaining_balance_cents / 100

print("Total Commit (USD):", total_commit_usd)
print("Remaining Balance (USD):", remaining_balance_usd)
