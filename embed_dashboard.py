import requests
import os
url = "https://api.metronome.com/v1/dashboards/getEmbeddableUrl"
from config import METRONOME_BEARER_TOKEN
payload = {
    "customer_id": "7df46c71-45e4-43bd-9a14-c898a2b02efc",
    "dashboard": "commits_and_credits",
    # "dashboard_options": [
    #     {
    #         "key": "show_zero_usage_line_items",
    #         "value": "false"
    #     },
    #     {
    #         "key": "hide_voided_invoices",
    #         "value": "true"
    #     }
    # ],
    
}
headers = {
    "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json())