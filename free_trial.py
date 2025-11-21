import requests
from config import METRONOME_BEARER_TOKEN


def get_credit_balance():
    url = "https://api.metronome.com/v1/contracts/customerBalances/list"

    payload = {
        "customer_id": "dda4254e-429c-4d1e-87f9-1c1134c16003",
        "include_ledgers": True
    }
    headers = {
        "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)


    credit=response.json()['data'][0]["ledger"][0]["amount"]
    consumed=response.json()['data'][0]["ledger"][1]["amount"]
    return ((credit+consumed)/100)

print(f'Remaining Credits: {get_credit_balance()}')



def new_contract():
    payload={  
        "customer_id": "dda4254e-429c-4d1e-87f9-1c1134c16003",
        "rate_card_alias": "compute_rate_alias",  
        "starting_at": "2025-11-19T00:00:00.000Z",
        "usage_statement_schedule": {  
        "frequency": "monthly",  
        "day": "contract_start"  
        }  
    }
    headers = {
            "Authorization": f"Bearer {METRONOME_BEARER_TOKEN}",
            "Content-Type": "application/json"
        }

    response=requests.post('https://api.metronome.com/v1/contracts/create',json=payload,headers=headers)
    return response

print(new_contract())