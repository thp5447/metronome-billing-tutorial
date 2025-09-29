# Metronome Usage-Based Billing Tutorial 

This repository accompanies the [YouTube usage-based billing tutorial](https://youtube.com/playlist?list=PLUG2zXfT80sy3LGcEE7Z0XMOAB9i_4pGH&si=9ETDVYJND3P4kNBl) that integrates with Metronome’s API. Each episode builds on the previous one by adding files and features. This code includes:
- Episode 2 (auth check) 
- Episode 3 (HTTP ingest endpoint)
- Episode 4 (Billable metrics endpoint)
- Episode 5 (Product and Rate Card endpoint)
- Episode 6 (Contract endpoint)
- Episode 7: One‑page UI + Create Customer (single metric with dimensional pricing)

## Prerequisites

- Python 3.9+ recommended
- A Metronome API bearer token
- Git

## Setup

1) Clone and enter the project:

```bash
git clone <your-repo-url>
cd <cloned-folder>  # replace with the folder name created by GitHub
```

2) Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# Windows (CMD):        .\.venv\Scripts\activate.bat
```

3) Install dependencies:

```bash
pip install -r requirements.txt
```

4) Configure environment variables:

```bash
cp .env.example .env
# Edit .env and set:
#   METRONOME_BEARER_TOKEN=<your_api_key>
#   DEMO_CUSTOMER_ALIAS=<your_ingest_alias>
```

5) Run the app and open the UI:

```bash
python app.py
# Visit http://localhost:5000
```

Quick flow in the browser (final episode):
- Click “Create Customer” to create a demo customer in your Metronome account.
- If you haven’t already, run pricing setup once in a terminal:
  - `curl -sS -X POST http://localhost:5000/api/metrics | jq`
  - `curl -sS -X POST http://localhost:5000/api/pricing | jq`
- Click “Create Contract” to bind pricing to the customer.
- Use the “Generate” buttons to send usage; the “Today’s Usage” panel updates automatically.


## Run the API check (Episode 2)

```bash
python test_connection.py
```

Expected outcomes:
- Success: prints a checkmark and (if present) the first customer’s name.
- Authentication error: instructs you to verify `METRONOME_BEARER_TOKEN`.
- Other error: prints the error and suggests next steps.

## Episode 3: Event Ingestion (HTTP endpoint)

This episode mirrors the reference demo by exposing a minimal HTTP endpoint
that sends a usage event to Metronome using a thin SDK wrapper.

What’s new:
- `app.py` — Flask app with `POST /api/generate`.
- `services/metronome_client.py` — Minimal wrapper around the Metronome SDK.
- `config.py` — Loads env vars (e.g., `METRONOME_BEARER_TOKEN`) and shared constants.

Before sending events (one-time, via Metronome dashboard):
- Create a demo customer and add an ingest alias (e.g., `jane@nova.com`).
- Or copy an existing `customer_id` if you prefer sending by ID.


Run the API:
```bash
python app.py
```

Send an event with curl:
```bash
# Uses DEMO_CUSTOMER_ALIAS from .env; include a deterministic transaction_id
curl -s -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"tier":"ultra","transaction_id":"ep3-demo-001"}'
```

Notes:
 - This app does not create customers. It always uses `DEMO_CUSTOMER_ALIAS` from `.env`. Create a customer in the
   dashboard and attach that alias before sending events.
 - Properties are strings per Metronome docs (e.g., `"num_images": "1"`).
 - The response includes a `transaction_id` you can search in Connections → Events.


## Episode 4: Billable Metrics

This episode defines a single billable metric for our `EVENT_TYPE` and segments
usage by tier (i.e image type), using group keys. We aggregate with `SUM` on the `num_images`
property, and group by `image_type` so one metric reports `standard`,
`high-res`, and `ultra` separately.

What’s new:
- `POST /api/metrics` — local-only setup route that creates the metric with safe defaults:
  - name: "Nova Image Generation"
  - aggregation_type: `SUM`, aggregation_key: `num_images`
  - group_keys: `[["image_type"]]`
  - property_filters: require `image_type` and `num_images` to exist

Run the setup (one time per environment):
```bash
python app.py
# in a separate terminal
curl -sS -X POST http://localhost:5000/api/metrics | jq
```

Then send a couple of events (reuse Episode 3 curl):
```bash
curl -s -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"tier":"ultra","transaction_id":"ep4-demo-001"}'
```

Notes:
- Properties are strings per Metronome docs (e.g., `"num_images": "1"`; categorical fields like `"image_type"` remain strings too).
- Timestamps are RFC3339 UTC with trailing `Z`.
- The setup route is not idempotent — calling it multiple times will create duplicate metrics.
- Verify:
- In Metronome → Billable metrics, confirm "Nova Image Generation" exists.
- Aggregation is `SUM`; group keys include `image_type`.
- Send a couple of test events:
  ```bash
  curl -s -X POST http://localhost:5000/api/generate -H 'Content-Type: application/json' -d '{"tier":"standard","transaction_id":"ep4-std-001"}'
  curl -s -X POST http://localhost:5000/api/generate -H 'Content-Type: application/json' -d '{"tier":"ultra","transaction_id":"ep4-ultra-001"}'
  ```
- In Connections → Events, search by `transaction_id` to confirm ingestion.



## Episode 5: Products & Pricing

In this episode, we attach pricing to the metric from Episode 4.
We use dimensional pricing: a single product tied to the metric and
three flat rates targeted to `image_type` values (standard, high-res, ultra).

What’s new:
- `POST /api/pricing` — local-only setup route that creates:
  - a product tied to the Ep4 metric (`PRODUCT_NAME`)
  - a rate card (`RATE_CARD_NAME`)
  - three FLAT rates (cents) for each `image_type`, using `BILLABLE_PRICES`
 
Run the pricing setup (one time per environment):
```bash
python app.py
# in a separate terminal
curl -sS -X POST http://localhost:5000/api/pricing | jq
```


Notes:
- Dimensional targeting uses pricing group values: each rate is scoped to `image_type=<tier>`.
- Prices are configured in `config.py` under `BILLABLE_PRICES` (cents).


Verify:
- In Metronome → Offering -> Products, confirm the product exists (name from `PRODUCT_NAME`).
- In Metronome → Offering -> Rate cards, confirm `RATE_CARD_NAME` exists.
- Open the rate card and verify three FLAT rates with `pricing_group_values` targeting:
  - `image_type=standard`, `image_type=high-res`, `image_type=ultra` with prices from `BILLABLE_PRICES`.


## Episode 6: Contracts

This episode binds the Episode 5 pricing to a real customer via a contract.

What’s new:
- `POST /api/contract` — creates a simple contract for the demo customer using the Episode 5 rate card.

Configuration in `config.py`:
- `CONTRACT_START_AT` — RFC3339 start timestamp (00:00:00Z).

Prerequisites:
- You’ve already run Episode 4 (`/api/metrics`) and Episode 5 (`/api/pricing`).
- In the Metronome dashboard, create a demo customer and attach an ingest alias matching `DEMO_CUSTOMER_ALIAS` in your `.env`.

Run the setup:
```bash
python app.py
# in a separate terminal
curl -sS -X POST http://localhost:5000/api/contract | jq
```

Notes:
- `/api/contract` expects `rate_card_id` from Episode 5 and looks up the customer by `DEMO_CUSTOMER_ALIAS`.
- Customer creation is explicit in the dashboard; the API does not auto-create customers.
- The state file `.metronome_config.json` tracks `customer_id` and `contract_id` for reuse.

## Episode 7: One‑page UI + Create Customer

What’s new:
- `GET /` — renders the demo page (no framework).
- `POST /api/customers` — creates (or reuses by alias) a demo customer in your Metronome account and stores the `customer_id` locally. Accepts `{ name?, ingest_alias? }`.
- `GET /api/status` — returns local IDs to enable/disable UI buttons.
- `GET /api/usage` — returns today’s usage grouped by `image_type` via the SDK’s `usage.list_with_groups`.

Flow:
1) Run Episode 4 + 5 setup once (`/api/metrics`, `/api/pricing`).
2) In the browser: Create Customer → Create Contract.
3) Generate images at Standard/High‑Res/Ultra; watch “Today’s Usage” update.

Implementation notes:
- One billable metric with `group_keys=[["image_type"]]` and dimensional pricing via `pricing_group_values`.
- Spend shown in the UI is computed as `usage_count × unit_price` for teaching purposes. For production, use invoice breakdowns (`customers.invoices.list_breakdowns`) to power spend‑over‑time with discounts/credits and non‑flat pricing reflected.


## Local State & Caching Behavior (Important)

This demo persists a few non‑secret IDs and small bits of metadata in a local file: `.metronome_config.json`. 

To fully reset the demo, delete the entire `.metronome_config.json` file. You’ll need to run the setup steps again (pricing, customer, contract).This file is local-only and safe to delete at any time.

What’s stored
- `metric_id`, `product_id`, `rate_card_id` — created by the setup routes
- `customer_id`, `contract_id` — created by the UI actions
- `prices_by_tier` — a cached map of `{tier: price_cents}` fetched once from the active rate card

Implications
- Idempotency: the setup routes reuse stored IDs when present, so runs are fast and repeatable.
- Pricing cache: `prices_by_tier` is fetched the first time the UI loads after pricing is created and then cached. It is NOT auto‑refreshed if you edit rates in the dashboard.
- Refreshing prices: delete the `prices_by_tier` key (or the entire `.metronome_config.json` file) and reload the page to fetch fresh prices from the rate card.
- Safety: `.metronome_config.json` is ignored by Git; it contains no credentials.


## Viewer Guide

Follow specific episode snapshots using Git tags. Episode snapshots correspond to Git tags. Note: Episode 1 had no code snapshot; the first tag with code is `ep02`. Create a branch from a tag to experiment without altering the snapshot.

```bash
# Fetch and list available episode tags
git fetch --tags
git tag --list   # see available episode tags

# Check out the first code snapshot (Episode 2)
git checkout tags/ep02

# Optional: create a working branch from the tag to avoid detached HEAD
git checkout -b ep02-playground tags/ep02

# Check out the Episode 3 snapshot
git checkout tags/ep03

# Optional: create a working branch for Episode 3
git checkout -b ep03-playground tags/ep03
```

Why branch from a tag? Checking out a tag puts you in a detached HEAD state (not on a branch). Creating a branch (e.g., `ep02-playground`) lets you make changes and commits without altering the tag, which remains an immutable snapshot.

Questions or suggestions? Open an issue or discussion in the repo.

## Resources

- Metronome Docs: https://docs.metronome.com/
- Metronome SDKs: https://docs.metronome.com/developer-resources/sdks/
