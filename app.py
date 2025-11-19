"""
Metronome Billing Demo (single page, single metric)

- Earlier episodes focused on backend only. Episode 7 introduces a minimal
  frontend (vanilla HTML/CSS/JS) served by Flask (GET / + static/) to interact
  with these endpoints. Keep tokens server-side; the browser never talks to
  Metronome directly.

What this showcases (SDK-first):
- Create a customer (POST /api/customers) and persist its ID locally
- Create pricing (POST /api/pricing) and a contract (POST /api/contract)
- Ingest usage events with idempotency (POST /api/generate)
- Retrieve grouped usage for one billable metric via `usage.list_with_groups`

UI endpoints:
- GET /              → renders the demo page
- GET /api/usage     → today's usage grouped by image_type
- GET /api/status    → local IDs to gate UI buttons

"""
import logging
from datetime import datetime, timezone, timedelta
from collections import Counter

from flask import Flask, jsonify, request, render_template
import json
import os

from config import (
    METRONOME_BEARER_TOKEN,
    EVENT_TYPE,
    BILLABLE_METRIC_NAME,
    BILLABLE_GROUP_KEYS,
    BILLABLE_PRICES,
    PRODUCT_NAME,
    RATE_CARD_NAME,
    RATE_EFFECTIVE_AT,
    CONTRACT_START_AT,
)
from services.metronome_client import MetronomeClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

if not METRONOME_BEARER_TOKEN:
    raise RuntimeError("METRONOME_BEARER_TOKEN is not set. Configure it in .env")

# Final episode uses create-customer flow and stored customer_id.

client = MetronomeClient(METRONOME_BEARER_TOKEN)


# ---- Local state helpers (ids only; never committed) ----
# Local demo state file (ids only). Delete to reset demo state.
STATE_PATH = ".metronome_config.json"

def _load_state() -> dict:
    """Load local IDs/state persisted between runs (if present)."""
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

 
def _save_state(state: dict) -> None:
    """Persist local IDs/state to disk for idempotent setup."""
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        logger.warning("Failed to save state file %s", STATE_PATH)


 

def _next_tx_id(customer_id: str, tier: str) -> str:
    """Return a deterministic transaction_id for this customer/tier/day.

    Rationale
    - Server owns idempotency and generates predictable IDs 
    - We keep a simple counter per (customer_id, tier, UTC day) in the local
      state file. 

    Format
      nova-<tier>-<YYYYMMDD>-<shortCustomer>-<seq4>

    Examples
      nova-standard-20250928-ab0be-0001
      nova-standard-20250928-ab0be-0002
    """

    # Compute the UTC day bucket we scope the counter to.
    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Load state and walk/create the nested counter structure using setdefault:
    # state["tx_seq"][customer_id][YYYYMMDD][tier] -> int
    state = _load_state()
    tx_seq = state.setdefault("tx_seq", {})
    by_customer = tx_seq.setdefault(customer_id, {})
    by_day = by_customer.setdefault(today, {})

    # Increment the sequence for this (customer, day, tier)
    seq = int(by_day.get(tier, 0)) + 1
    by_day[tier] = seq

    # Persist the updated counter
    _save_state(state)

    # Short, human‑readable suffix from the customer_id to aid searching
    short_cust = "".join(c for c in str(customer_id)[-8:] if c.isalnum())[-5:]
    return f"nova-{tier}-{today}-{short_cust}-{seq:04d}"


@app.get("/")
def index():
    """Render the single-page demo UI."""
    state = _load_state()
    prices_map = state.get("prices_by_tier")
    if not prices_map and state.get("rate_card_id") and state.get("product_id"):
        try:
            prices_map = client.get_rate_card_prices_by_tier(
                rate_card_id=state["rate_card_id"],
                product_id=state["product_id"],
                at=RATE_EFFECTIVE_AT,
            ) or None
            if prices_map:
                state["prices_by_tier"] = prices_map
                _save_state(state)
        except Exception:
            pass
    if prices_map:
        prices = {t: f"${int(c)/100:.2f}" for t, c in prices_map.items()}
    else:
        # Pricing not configured yet → show placeholders
        prices = {t: "—" for t in BILLABLE_PRICES.keys()}
    return render_template("index.html", prices=prices)

def _ensure_metric(
    name: str,
    event_type: str = None,
    aggregation_type: str = None,
    aggregation_key: str = None,
    group_keys: list = None,
    property_filters: list = None
) -> dict:
    # 2) Try to find by name (non-archived)
    metrics = client.list_billable_metrics()
    matches = [m for m in metrics if m.get("name") == name]
    if matches:
        m = matches[0]
        logger.info("Linked existing metric by name: %s -> %s", name, m.get("id"))
        return m
    if all([event_type, aggregation_type, aggregation_key, group_keys, property_filters]):
        created = client.create_billable_metric(
            name=name,
            event_type=event_type,
            aggregation_type=aggregation_type,
            aggregation_key=aggregation_key,
            group_keys=[list(x) for x in group_keys],
            property_filters=property_filters,
        )
    logger.info("Created metric: %s", created.get("id"))
    return created


def _ensure_product_and_rate_card(
        metric: dict,
        product_name: str,
        rate_name: str):
    """
    Returns (product_id, rate_card_id, created_product, created_rate_card).
    """
    created_product = False
    created_rate_card = False
    # Create missing pieces only
    #if not product_id:
    pricing_group_key = metric['group_keys'][0]
    product = client.create_product(
        name=product_name,
        billable_metric_id=metric['id'],
        pricing_group_key=pricing_group_key,
        presentation_group_key=pricing_group_key,
    )

    product_id = product.get("id")
    if not product_id:
        raise RuntimeError("Failed to create product")
    logger.info("Created product: %s", product_id)
    created_product = True

   # if not rate_card_id:
    rate_card = client.create_rate_card(name=rate_name)
    rate_card_id = rate_card.get("id") or rate_card.get("rate_card_id")
    if not rate_card_id:
        raise RuntimeError("Failed to create rate card")
    logger.info("Created rate card: %s", rate_card_id)
    created_rate_card = True

    return product_id, rate_card_id, created_product, created_rate_card



@app.post("/api/ingress")
def data_ingress():
    """Accepts JSON and emits a usage event.


    Quick curl:
      curl -sS -X POST http://localhost:5000/api/ingress \
        -H 'Content-Type: application/json' \
        -d '{"tier":"ultra","transaction_id":"ep3-demo-001","model":"nova-v2","region":"us-west-2"}'

    MY CURL
    
    """
    data = request.get_json(silent=True) or {}

    # Validate tier against configured taxonomy (no state dependency)
    prop=data.get("properties",{})
    size=(prop.get("size") or "").strip().lower()
    warehouse = (prop.get("warehouse") or "").strip().lower()
    hours=(prop.get("hours") or 1).strip().lower()
    allowed = set(BILLABLE_PRICES.keys())
    tier = (size,warehouse)
    if tier not in allowed:
        return jsonify({
            "error": "Invalid or missing 'tier'",
            "allowed": sorted(allowed),
        }), 400

   

    properties = {
        "size": size,
        "warehouse": warehouse,
        "hours": hours,  
    }
    
    customer_id=(data.get("customer_id") or "").strip()
    identifier=customer_id
    transaction_id = (data.get("transaction_id") or "").strip()


    timestamp = datetime.now(timezone.utc)
    ts_str = timestamp.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        client.send_usage_event(
            customer_id=identifier,
            event_type=EVENT_TYPE,
            properties=properties,
            timestamp=timestamp,
            transaction_id=transaction_id,
        )
        id_type = "customer_id" if customer_id else "ingest_alias"
        logger.info(
            "Sent usage event | event_type=%s | tier=%s | tx=%s | %s=%s",
            EVENT_TYPE,
            tier,
            transaction_id,
            id_type,
            identifier,
        )
        return jsonify({
            "success": True,
            "event_type": EVENT_TYPE,
            "tier": tier,
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "timestamp": ts_str,
        })
    except Exception as e:
        logger.exception("Failed to send usage event")
        return jsonify({"error": f"Failed to send usage: {e}"}), 500


# Create a billable metric by passing in data rather than hard coded
@app.post("/api/metrics")
def setup_metric():
    """
    Create a billable metric with user-provided parameters.

    Example curl with data ingress:
      curl -sS -X POST http://localhost:5050/api/metrics \
        -H "Content-Type: application/json" \
        -d '{
              "name": "Raindrop Data Ingress2",
              "event_type": "data_ingress",
              "aggregation": {"type": "sum", "field": "bytes_ingested"},
              "group_keys": [["region", "provider"]],
              "property_filters": [{"name": "bytes_ingested", "exists": true},
                                    {"name": "region", "exists": true},
                                    {"name": "provider", "exists": true}
                                    ]
            }'
    """

    try:
        body = request.get_json(force=True)

        # Extract user-provided parameters
        name = body.get("name")
        event_type = body.get("event_type")
        aggregation = body.get("aggregation")
        group_keys = body.get("group_keys", [])
        property_filters = body.get("property_filters", [])

        if not name or not event_type or not aggregation:
            return jsonify({
                "error": "Missing required fields: name, event_type, aggregation"
            }), 400

        # Create/ensure metric using the supplied values
        metric = _ensure_metric(
            name=name,
            event_type=event_type,
            aggregation_type=aggregation.get("type", "SUM"),
            aggregation_key=aggregation.get("field", ""),
            group_keys=group_keys,
            property_filters=property_filters,
        )

        return jsonify({
            "success": True,
            "metric_name": name,
            "metric": metric,
        }), 200

    except Exception as e:
        logger.exception("Failed to create billable metric")
        return jsonify({"error": f"Failed to create metric: {e}"}), 500

@app.post("/api/pricing")
def setup_pricing():
    """Create product + rate card + flat rates.
    Quick Curl:
      curl -sS -X POST http://localhost:5050/api/pricing \
        -H "Content-Type: application/json" \
        -d @extended_rates.json
    """
    try:
        body = request.get_json(force=True)
        name=body.get("metric_name")
        # Ensure we have a metric and its ID

        metric = _ensure_metric(name)
        billable_metric_id = metric.get("id")
        product_name=body.get("product").get("name")
        rate_name=body.get('rate_card').get('name')
        # Ensure product + rate card (reuse from state when possible)
        product_id, rate_card_id, created_product, created_rate_card = _ensure_product_and_rate_card(metric,product_name,rate_name)

        # Add per-tier rates only when we just created either the product or rate card
        created_rates = {}
        if created_product or created_rate_card:
            rate_card=body.get("rate_card")
            rates=rate_card.get("rates")
            effective_date=rate_card.get("effective_at")
            for rate in rates:
                r = client.add_flat_rate(
                    rate_card_id=rate_card_id,
                    product_id=product_id,
                    price_cents=rate["price_cents"],
                    starting_at=effective_date,
                    pricing_group_values={"region":rate["region"],"provider":rate["provider"]},
                )
                rid = r.get("id") or r.get("rate_id")
                created_rates[str(rate["region"])+', '+rate["provider"]] = {"id": rid, "price_cents": int(rate["price_cents"])}

 
        payload = {
            "success": True,
            "product": {"id": product_id, "name": product_name},
            "rate_card": {"id": rate_card_id, "name": rate_name},
            # Only includes rates created in this call (empty on reuse)
            "rates": created_rates,
        }

        return jsonify(payload), 200
    except Exception as e:
        logger.exception("Failed to create pricing")
        return jsonify({"error": f"Failed to create pricing: {e}"}), 500


# ---- Episode 6: Customers, Contracts, and Preview ----

@app.post("/api/customers")
def create_customer():
    """Create a demo customer and persist its ID locally.
    curl -i -X POST http://127.0.0.1:5050/api/customers \
  -H 'Content-Type: application/json' \
  -d '{
        "name":"Sabre Inc.", 
        "ingest_alias": "rcalif@sabre.com"
        }'
    
        
    Body: {"name": "Optional display name", "ingest_alias": "Optional alias"}
    Returns: {"id": customer_id, "name": name, "ingest_alias": alias?}
    """
    try:
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "Nova Demo Customer").strip() or "Nova Demo Customer"
        alias = (body.get("ingest_alias") or "").strip() or None

        # Get-or-create by alias if provided; else create by name only
        if alias:
            customer = (
                client.get_customer_by_ingest_alias(alias)
                or client.create_customer(name=name, ingest_alias=alias)
            )
        else:
            customer = client.create_customer(name=name)

        cid = customer.get("id")
        if not cid:
            return jsonify({"error": "Failed to create customer"}), 500

        state = _load_state()
        prev_cid = state.get("customer_id")
        state["customer_id"] = cid
        state["customer_name"] = customer.get("name", name)
        state["ingest_alias"] = alias
        # If switching to a different customer, drop prior contract context
        if cid != prev_cid:
            state.pop("contract_id", None)
            state.pop("contract_start_at", None)
        _save_state(state)

        return jsonify({
            "success": True,
            "customer": {"id": cid, "name": state["customer_name"], "ingest_alias": alias},
        }), 200
    except Exception as e:
        logger.exception("Failed to create customer")
        return jsonify({"error": f"Failed to create customer: {e}"}), 500

@app.post("/api/contract")
def setup_contract():
    """Create a simple contract for the demo customer using the Episode 5 rate card.

    Requires that /api/pricing has been run (to populate rate card ID in local state).

    Quick curl:
      curl -sS -X POST http://localhost:5000/api/contract | jq
    """
    try:
        state = _load_state()
        # Use customer created via /api/customers
        customer_id = state.get("customer_id")
        if not customer_id:
            return jsonify({
                "error": "No customer configured. Create a customer first via POST /api/customers.",
            }), 400

        # Require rate card id from Episode 5
        rate_card_id = state.get("rate_card_id")
        if not rate_card_id:
            return jsonify({
                "error": "Missing rate_card_id. Run /api/pricing first to create pricing.",
            }), 400

        # Create a simple contract referencing the rate card
        contract = client.create_contract(
            customer_id=customer_id,
            rate_card_id=rate_card_id,
            starting_at=CONTRACT_START_AT,
        )
        
        contract_id = contract.get("id")
        if not contract_id:
            return jsonify({"error": "Failed to create contract"}), 500

        # Persist contract in local state
        state.update({
            "customer_id": customer_id,
            "contract_id": contract_id,
            "contract_start_at": CONTRACT_START_AT,
        })
        _save_state(state)

        return jsonify({
            "success": True,
            "contract": {
                "id": contract_id,
                "customer_id": customer_id,
                "rate_card_id": rate_card_id,
                "starting_at": CONTRACT_START_AT,
            },
        }), 200
    except Exception as e:
        logger.exception("Failed to create contract")
        return jsonify({"error": f"Failed to create contract: {e}"}), 500


@app.get("/api/status")
def status():
    """Return local demo state (ids only)."""
    state = _load_state()
    return jsonify({
        "metric_id": state.get("metric_id"),
        "product_id": state.get("product_id"),
        "rate_card_id": state.get("rate_card_id"),
        "customer_id": state.get("customer_id"),
        "contract_id": state.get("contract_id"),
    })


@app.get("/api/usage")
def get_usage():
    """Return today's usage per image_type for the configured customer.

    Advanced
    - For authoritative billed dollars in production, prefer invoice breakdowns
      via `customers.invoices.list_breakdowns`.

    Notes
    - Window: UTC midnight → midnight (today only).
    - Grouping: server-side via SDK (`usage.list_with_groups`) on `image_type`.
    - Amounts: derived from cached `prices_by_tier` (rate card) only. If pricing
      hasn't been created/fetched yet, amounts are 0.00 but counts are still
      returned so the UI can show activity.
    """
    s = _load_state()
    if not (cid := s.get("customer_id")):
        return jsonify({})
    # No contract yet → don't show usage for a prior session's customer
    if not s.get("contract_id"):
        return jsonify({})

    # Ensure we have a billable metric ID; 
    metric_id = s.get("metric_id") or (_ensure_metric() or {}).get("id")
    if not metric_id:
        return jsonify({})

    # Compute today's UTC window
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    try:
        # Retrieve grouped usage rows for the window, grouped by `image_type`.
        rows = client.get_usage_grouped(
            customer_id=cid,
            billable_metric_id=metric_id,
            start_time=start,
            end_time=end,
            group_key=["warehouse","size"],
            window_size="DAY",
        )
    except Exception:
        logger.exception("usage.list_with_groups failed")
        return jsonify({})

    # Aggregate counts per tier from grouped rows. Values are numeric
    # (Decimal via the SDK); cast to int before summing. Using float(...) keeps
    # this tolerant if a value happens to arrive as a string.
    counts = Counter()
    for r in rows:
        if t := r.get("group_value"):
            try:
                counts[t] += int(float(r.get("value") or 0))
            except Exception:
                pass

    # Only use cached real prices from rate card
    prices = s.get("prices_by_tier")
    tiers = tuple(BILLABLE_PRICES.keys())

    return jsonify({
        t: {
            "count": (n := counts.get(t, 0)),
            # amount = count × unit_price_cents ÷ 100.0; zero when prices unknown.
            # Note: For authoritative billed dollars in production, prefer
            # customers.invoices.list_breakdowns (invoice breakdowns) instead of
            # computing count × unit price. This demo keeps it simple for teaching.
            "amount": (n * int(prices.get(t, 0)) / 100.0) if prices else 0.0,
        }
        for t in tiers
    })

 

if __name__ == "__main__":
    logger.info("Starting Metronome Demo API on http://localhost:5050")
    app.run(debug=True, port=5050)
'''
curl -i -X POST http://127.0.0.1:5050/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
        "event_type": "Computing",
        "properties": {
          "warehouse": "aws",
          "size": "small",
          "hours": 744
        },
        "transaction_id": "ep3-demo-004",
        "customer_id": "demo_mscott@dunder.com",
        "timestamp": "2025-11-14T19:49:35.605Z"
      }'
'''