"""Razorpay payload normalization adapter.

Transforms provider-specific Razorpay webhook JSON structures into the system's
canonical internal NormalizedEvent model.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from app.schemas.event import NormalizedEvent


class RazorpayAdapter:
    """Adapter for parsing and normalizing Razorpay webhook payloads."""

    @classmethod
    def normalize(
        cls,
        payload: Dict[str, Any],
        event_id_header: Optional[str] = None,
    ) -> NormalizedEvent:
        """Convert a raw Razorpay webhook payload dictionary to NormalizedEvent.

        Args:
            payload: Parsed JSON dictionary from Razorpay webhook.
            event_id_header: Value of the 'x-razorpay-event-id' HTTP header if present.

        Returns:
            A canonical NormalizedEvent instance.
        """
        event_type = payload.get("event", "unknown")
        payload_container = payload.get("payload", {})
        payment_container = payload_container.get("payment", {})
        payment_entity = payment_container.get("entity", {}) if isinstance(payment_container, dict) else {}

        # 1. Resolve Event ID for idempotency
        # Prefer x-razorpay-event-id header, fallback to payload-level identifiers
        event_id = (
            event_id_header
            or payload.get("event_id")
            or payload.get("id")
        )
        if not event_id:
            # Fallback composite key if gateway did not supply event ID
            pay_id = payment_entity.get("id", "unknown_pay")
            created_ts = payload.get("created_at", int(datetime.now(timezone.utc).timestamp()))
            event_id = f"rzp_evt_{event_type}_{pay_id}_{created_ts}"

        # 2. Timestamp extraction
        epoch_ts = payment_entity.get("created_at") or payload.get("created_at")
        if epoch_ts:
            occurred_at = datetime.fromtimestamp(epoch_ts, tz=timezone.utc)
        else:
            occurred_at = datetime.now(timezone.utc)

        # 3. Financial normalization (Razorpay amounts are in subunits/paise)
        raw_amount = payment_entity.get("amount", 0)
        try:
            amount_decimal = (Decimal(str(raw_amount)) / Decimal("100")).quantize(Decimal("0.01"))
        except Exception:
            amount_decimal = Decimal("0.00")

        currency = (payment_entity.get("currency") or "INR").upper()

        # 4. Customer mapping signals
        notes = payment_entity.get("notes", {}) or {}
        external_customer_id = (
            notes.get("customer_id")
            or notes.get("external_customer_id")
            or payment_entity.get("customer_id")
        )
        customer_email = payment_entity.get("email") or notes.get("customer_email")
        customer_phone = payment_entity.get("contact") or notes.get("customer_phone")
        customer_name = notes.get("customer_name") or payment_entity.get("name")

        # 5. Entity references
        external_payment_id = payment_entity.get("id")
        external_order_id = payment_entity.get("order_id") or notes.get("order_id")
        external_invoice_id = payment_entity.get("invoice_id") or notes.get("invoice_id")
        external_subscription_id = notes.get("subscription_id") or payment_entity.get("subscription_id")

        # 6. Payment status & method
        raw_method = payment_entity.get("method")
        payment_method = raw_method.upper() if raw_method else "CARD"

        raw_status = payment_entity.get("status", "").lower()
        if raw_status in ("captured", "success"):
            payment_status = "SUCCESS"
        elif raw_status == "failed":
            payment_status = "FAILED"
        elif raw_status == "authorized":
            payment_status = "AUTHORIZED"
        else:
            payment_status = raw_status.upper() if raw_status else "UNKNOWN"

        # 7. Failure diagnostics
        failure_code = payment_entity.get("error_code") or payment_entity.get("error_reason")
        failure_description = payment_entity.get("error_description")
        failure_source = payment_entity.get("error_source")
        failure_step = payment_entity.get("error_step")
        failure_reason = payment_entity.get("error_reason")

        # 8. Filtered metadata (without sensitive credential info)
        metadata = {
            "account_id": payload.get("account_id"),
            "bank": payment_entity.get("bank"),
            "wallet": payment_entity.get("wallet"),
            "vpa": payment_entity.get("vpa"),
            "international": payment_entity.get("international", False),
            "order_id": external_order_id,
            "invoice_id": external_invoice_id,
            "notes": notes,
        }

        return NormalizedEvent(
            event_id=str(event_id),
            event_type=str(event_type),
            source="RAZORPAY",
            occurred_at=occurred_at,
            amount=amount_decimal,
            currency=currency,
            external_customer_id=str(external_customer_id) if external_customer_id else None,
            customer_email=str(customer_email).strip().lower() if customer_email else None,
            customer_phone=str(customer_phone).strip() if customer_phone else None,
            customer_name=str(customer_name).strip() if customer_name else None,
            external_payment_id=str(external_payment_id) if external_payment_id else None,
            external_order_id=str(external_order_id) if external_order_id else None,
            external_invoice_id=str(external_invoice_id) if external_invoice_id else None,
            external_subscription_id=str(external_subscription_id) if external_subscription_id else None,
            payment_method=payment_method,
            payment_status=payment_status,
            failure_code=str(failure_code) if failure_code else None,
            failure_description=str(failure_description) if failure_description else None,
            failure_source=str(failure_source) if failure_source else None,
            failure_step=str(failure_step) if failure_step else None,
            failure_reason=str(failure_reason) if failure_reason else None,
            metadata=metadata,
            raw_payload=payload,
        )
