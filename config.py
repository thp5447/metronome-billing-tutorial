import os
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

# Metronome API bearer token
METRONOME_BEARER_TOKEN = os.environ.get("METRONOME_BEARER_TOKEN")

# Ingest alias for episode 3
DEMO_CUSTOMER_ALIAS = os.environ.get("DEMO_CUSTOMER_ALIAS")

# Default event name for Nova
EVENT_TYPE = "Computing"

# Billable metric display name
BILLABLE_METRIC_NAME = "Computing"

# Default group keys for dimensional pricing
# SDK shape: list-of-lists (one inner list per dimension), e.g., [["image_type"], ["region"]]
BILLABLE_GROUP_KEYS = (("size","warehouse",),)

# Flat per-image prices in cents by image_type
BILLABLE_PRICES = {
    ("small","aws"):54,
    ("medium","aws"):199,
    ("large","aws"):382,
    ("small","gcp"):49,
    ("medium","gcp"):89,
    ("large","gcp"):178,
}

# Product and rate card display names
PRODUCT_NAME = "Computing"
RATE_CARD_NAME = "Compute Rates"

# Effective start timestamp for rates 
RATE_EFFECTIVE_AT = "2025-09-01T00:00:00Z"

# Contract start date
CONTRACT_START_AT = "2025-09-01T00:00:00Z"