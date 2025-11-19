import requests
from config import METRONOME_BEARER_TOKEN
import json
# url = "https://api.metronome.com/v2/contracts/get"

# payload = {
#     "customer_id": "1bdadc42-83a0-4f95-bde4-ed9c1fef200d",
#     "contract_id": "f2c00742-0474-41e9-a5d1-68c2abb64aa7",
# }
# headers = {
#     "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
#     "Content-Type": "application/json"
# }

# response = requests.post(url, json=payload, headers=headers)

# print(json.dumps(response.json(), indent=4))
# customer_id= "1bdadc42-83a0-4f95-bde4-ed9c1fef200d"
# invoice_id="20de3058-4d13-5970-8621-2fa79c48da87"

# url = "https://api.metronome.com/v1/customers/{customer_id}/invoices/commits-and-credits"

# headers = {"Authorization": f"Bearer {METRONOME_BEARER_TOKEN}"}

# response = requests.get(url, headers=headers)

# print(response.json())


import requests

url = "https://api.metronome.com/v1/contracts/customerBalances/list"

payload = {
    "customer_id": "1bdadc42-83a0-4f95-bde4-ed9c1fef200d",
    "id": "36d43e41-90d4-4e6c-a2fc-07d2e657df76",
    "include_ledgers": True
}
headers = {
    "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)


credit=response.json()['data'][0]["ledger"][0]["amount"]
consumed=response.json()['data'][0]["ledger"][1]["amount"]
print(f'Remaining Credits: {(credit+consumed)/100}')
#print(json.dumps(response.json(), indent=4))
