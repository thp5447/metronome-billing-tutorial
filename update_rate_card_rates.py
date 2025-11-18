from services.metronome_client import MetronomeClient
from config import METRONOME_BEARER_TOKEN
import argparse
import pandas as pd

rate_card_id='860a0416-72c4-41c6-a588-cf0427655a82'
client=MetronomeClient(METRONOME_BEARER_TOKEN)

#python update_rate_card_rates.py --csv dunder_rates.csv --rate_card_name API_Integration --effective_at 2024-11-01T00:00:00Z
parser=argparse.ArgumentParser()
parser.add_argument("--csv", required=True)
parser.add_argument("--rate_card_name",required=True)
parser.add_argument("--effective_at")
args=parser.parse_args()
rates=pd.read_csv(args.csv)
rate_card=args.rate_card_name
product_id='84b5ae00-0a84-479b-a7df-2a60bb6b728c'
effective_date=args.effective_at
for index, rate in rates.iterrows():
    client.add_flat_rate(
                        rate_card_id=rate_card_id,
                        product_id=product_id,
                        price_cents=rate["price_cents"],
                        starting_at=effective_date,
                        pricing_group_values={"size":rate["Size"],"warehouse":rate["Warehouse"]},
                    )