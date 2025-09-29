"""
Metronome SDK wrapper

Centralizes calls to the Metronome SDK so the Flask app
can stay thin and consistent. 


Notes
- Per Metronome guidance, event property keys and values should be strings
  (even numeric-looking values like "1"). Metronome parses numeric strings
  with arbitrary-precision decimals for aggregation.
- Timestamps must be RFC3339 strings in UTC with a trailing "Z".
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List

from metronome import Metronome
from config import BILLABLE_GROUP_KEYS


class MetronomeClient:
    def __init__(self, bearer_token: str) -> None:
        """Initialize the official Metronome SDK client."""
        self.client = Metronome(bearer_token=bearer_token)

    # ---- Usage ingestion (single-event convenience) ----
    def send_usage_event(
        self,
        *,
        customer_id: str,
        event_type: str,
        properties: Optional[Dict] = None,
        timestamp: datetime,
        transaction_id: str,
    ) -> None:
        """Send a single usage event.

        Required
        - customer_id: Metronome customer ID or attached ingest alias
        - event_type: stable event name
        - timestamp: timezone-aware datetime for the event occurrence
        - transaction_id: unique idempotency key (enables safe retries)

        Optional
        - properties: dict of string values (per Metronome guidelines)
        """

        def _to_rfc3339(dt: datetime) -> str:
            """Serialize to RFC3339 (UTC, seconds, trailing Z).

            Expects an aware datetime. If a naive datetime is supplied,
            Python will raise when converting timezones. Callers should pass
            `datetime.now(timezone.utc)` or otherwise ensure tz-aware values.
            """
            return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


        event = {
            # Identify the customer (ID or ingest alias)
            "customer_id": customer_id,
            # Stable event name; metrics target this via event_type_filter
            "event_type": event_type,
            # RFC3339 UTC timestamp with trailing Z
            "timestamp": _to_rfc3339(timestamp),
            # Idempotency key to deduplicate retries
            "transaction_id": transaction_id
        }
        if properties:
            # Forward properties as provided. Per docs, keys/values should be strings.
            event["properties"] = properties
        
        # Ingest a single Nova event
        self.client.v1.usage.ingest(usage=[event])

    # ---- Customers ----
    def create_customer(self, *, name: str, ingest_alias: Optional[str] = None) -> Dict:
        """Create a new customer.

        - If `ingest_alias` is provided, attach it.
        - Otherwise, create the customer without aliases.
        """
        payload: Dict = {"name": name}
        if ingest_alias:
            payload["ingest_aliases"] = [ingest_alias]

        resp = self.client.v1.customers.create(**payload)
        return resp.data.model_dump() if hasattr(resp, "data") else {}

    def get_customer_by_ingest_alias(self, ingest_alias: str) -> Optional[Dict]:
        """Retrieve a customer by ingest alias (None if not found)."""
        resp = self.client.v1.customers.list(ingest_alias=ingest_alias)
        items = getattr(resp, "data", []) or []
        if items:
            return items[0].model_dump()
        return None

    # ---- Billable metrics ----
    def create_billable_metric(
        self,
        *,
        name: str,
        event_type: str,
        aggregation_type: str = "SUM",
        aggregation_key: Optional[str] = "num_images",
        group_keys: Optional[List[List[str]]] = None,
        property_filters: Optional[List[Dict]] = None,
    ) -> Dict:
        """Create a billable metric for the given event type.

        Defaults target the demo's dimensional pricing setup:
        - aggregation_type: "SUM"
        - aggregation_key: "num_images" (sent as a numeric string in events)
        - group_keys: defaults to config.BILLABLE_GROUP_KEYS (segment by image type)

        Parameters
        - name: display name for the metric
        - event_type: the event this metric aggregates ("image_generation" for our demo)
        - aggregation_type: SUM for our demo
        - aggregation_key: required for numeric aggregations ("num_images" for our demo)
        - group_keys: list of lists of property names for dimensional breakdowns
                      (shape must be e.g., [["image_type"], ["region"]])
        - property_filters: optional filters; e.g., require fields to exist
          [{"name": "image_type", "exists": True}, {"name": "num_images", "exists": True}]
        """

        params: Dict = {
            "name": name,
            "aggregation_type": aggregation_type,
            "event_type_filter": {"in_values": [event_type]},
        }
        if aggregation_key:
            params["aggregation_key"] = aggregation_key
        # Use provided group_keys or fall back to immutable config default
        keys = group_keys if group_keys is not None else BILLABLE_GROUP_KEYS
        params["group_keys"] = [list(x) for x in keys]
        if property_filters:
            params["property_filters"] = property_filters

        resp = self.client.v1.billable_metrics.create(**params)
        return resp.data.model_dump() if hasattr(resp, "data") else {}

    def list_billable_metrics(self) -> List[Dict]:
        """List all billable metrics (as plain dicts)."""
        resp = self.client.v1.billable_metrics.list()
        return [m.model_dump() for m in getattr(resp, "data", [])]

    def retrieve_billable_metric(self, billable_metric_id: str) -> Optional[Dict]:
        """Retrieve a billable metric by ID (None if not found)."""
        try:
            resp = self.client.v1.billable_metrics.retrieve(billable_metric_id=billable_metric_id)
            return resp.data.model_dump()
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise

    # ---- Products & pricing ----
    def create_product(
        self,
        *,
        name: str,
        billable_metric_id: str,
        pricing_group_key: Optional[List[str]] = None,
        presentation_group_key: Optional[List[str]] = None,
    ) -> Dict:
        """Create a USAGE product tied to a billable metric.

        - `pricing_group_key` to enable dimensional pricing on the product
          (e.g., ["image_type"]).
        - `presentation_group_key` to split invoice presentation by dimension
          (e.g., ["image_type"]).
        """
        payload = {
            "name": name,
            "type": "USAGE",
            "billable_metric_id": billable_metric_id,
        }
        if pricing_group_key:
            payload["pricing_group_key"] = pricing_group_key
        if presentation_group_key:
            payload["presentation_group_key"] = presentation_group_key

        resp = self.client.v1.contracts.products.create(**payload)
        return resp.data.model_dump() if hasattr(resp, "data") else {}

    def create_rate_card(self, *, name: str, description: str = "") -> Dict:
        """Create a rate card for prices."""
        resp = self.client.v1.contracts.rate_cards.create(
            name=name,
            description=description or f"Pricing for {name}",
        )
      
        return resp.data.model_dump() if hasattr(resp, "data") else {}

    def add_flat_rate(
        self,
        *,
        rate_card_id: str,
        product_id: str,
        price_cents: int,
        starting_at: str,
        pricing_group_values: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Add a single FLAT rate to a rate card for a product.

        Supports dimensional pricing via `pricing_group_values`, which should map
        group key -> value (e.g., {"image_type": "ultra"}).
        """
        payload = {
            "rate_card_id": rate_card_id,
            "product_id": product_id,
            "entitled": True,
            "rate_type": "FLAT",
            "price": price_cents,
            "starting_at": starting_at,
        }
        if pricing_group_values:
            payload["pricing_group_values"] = pricing_group_values

        resp = self.client.v1.contracts.rate_cards.rates.add(**payload)
       
        if hasattr(resp, "data"):
            return resp.data.model_dump()
        return resp.model_dump() if hasattr(resp, "model_dump") else {}

    # ---- Contracts ----
    def create_contract(
        self,
        *,
        customer_id: str,
        rate_card_id: str,
        starting_at: str,
        name: Optional[str] = None,
        net_payment_terms_days: Optional[int] = None,
    ) -> Dict:
        """Create a simple contract referencing a rate card."""
        payload: Dict = {
            "customer_id": customer_id,
            "rate_card_id": rate_card_id,
            "starting_at": starting_at,
        }
        if name is not None:
            payload["name"] = name
        if net_payment_terms_days is not None:
            payload["net_payment_terms_days"] = net_payment_terms_days

        resp = self.client.v1.contracts.create(**payload)
        return resp.data.model_dump() if hasattr(resp, "data") else {}

    # ---- Usage ----
    

    def get_usage_grouped(
        self,
        *,
        customer_id: str,
        billable_metric_id: str,
        start_time: datetime,
        end_time: datetime,
        group_key: str,
        window_size: str = "DAY",
    ) -> List[Dict]:
        """Return grouped usage for a metric by the provided group key.

        Uses the `/v1/usage/groups` endpoint via SDK `usage.list_with_groups`.
        Items contain `group_key`, `group_value`, and `value`.
        """
        def _fmt(dt: datetime) -> str:
            return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

        page = self.client.v1.usage.list_with_groups(
            billable_metric_id=billable_metric_id,
            customer_id=customer_id,
            window_size=window_size,
            starting_on=_fmt(start_time),
            ending_before=_fmt(end_time),
            group_by={"key": group_key},
        )
        data = getattr(page, "data", []) or []
        # SDK returns Pydantic models; convert to plain dicts
        return [item.model_dump() for item in data]

    # ---- Pricing / Rates ----
    def get_rate_card_prices_by_tier(
        self,
        *,
        rate_card_id: str,
        product_id: str,
        at: str,
        group_key: str = "image_type",
    ) -> Dict[str, int]:
        """Return {tier: price_cents} for entitled FLAT rates on the card.

        price lives at `rate.price` and
        group value at `pricing_group_values[group_key]`.
        """
        items = (
            self.client.v1.contracts.rate_cards.rates.list(
                at=at,
                rate_card_id=rate_card_id,
                selectors=[{"product_id": product_id}],
            ).data
            or []
        )
        return {r.pricing_group_values[group_key]: int(r.rate.price) for r in items if r.entitled}

    # For production-grade spend dashboards, prefer
    # customers.invoices.list_breakdowns. See README for guidance.


    











































       
