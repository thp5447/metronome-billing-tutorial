import os
import requests
import json
from datetime import datetime

METRONOME_TOKEN = os.environ["METRONOME_BEARER_TOKEN"]

# --- CONFIG ---
CUSTOMER_ID = "7df46c71-45e4-43bd-9a14-c898a2b02efc"
CONTRACT_ID = "e344e1d7-c43e-458b-a673-6d6d7f6db207"

# Example rate cents per unit
UNIT_PRICE_CENTS = 2500  # $25.00 per unit usage event


def get_remaining_prepaid_balance(customer_id: str):
    """
    Returns remaining prepaid balance (in cents) for the given customer.
    """

    url = "https://api.metronome.com/v1/contracts/customerBalances/list"
    headers = {
        "Authorization": f"Bearer {METRONOME_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "customer_id": customer_id,
        "include_balance": True,
        "include_ledgers": False
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()["data"]

    # Filter only prepaid commits
    prepaid = [entry for entry in data if entry.get("type") == "PREPAID"]

    if not prepaid:
        return 0

    # Assume only one prepaid commit for simplicity
    return prepaid[0].get("balance", 0)


def calculate_usage_cost(units: int) -> int:
    """
    Computes the price of a usage event in cents.
    """
    return units * UNIT_PRICE_CENTS


def send_usage_event(customer_id: str, units: int):
    """
    Attempts to send a usage event. Declines if cost exceeds remaining prepaid balance.
    """

    # Step 1 — Check balance
    remaining = get_remaining_prepaid_balance(customer_id)
    cost = calculate_usage_cost(units)

    print(f"Remaining credit: {remaining} cents")
    print(f"Cost of this usage: {cost} cents")

    if cost > remaining:
        print("❌ Declining usage: exceeds remaining credit.")
        return False

    # Step 2 — Send usage event to Metronome
    url = "https://api.metronome.com/v1/ingest"
    headers = {
        "Authorization": f"Bearer {METRONOME_TOKEN}",
        "Content-Type": "application/json"
    }

    usage_event = {
        "event_type": "compute_hours",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "customer_id": customer_id,
        "properties": {
            "units": units
        }
    }

    response = requests.post(url, json={"events": [usage_event]}, headers=headers)
    response.raise_for_status()

    print("✅ Usage event accepted and sent.")
    return True


# --- Example run ---
if __name__ == "__main__":
    send_usage_event(CUSTOMER_ID, units=2)
