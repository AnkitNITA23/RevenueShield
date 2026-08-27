"""Seed script for development and demo environments.

=============================================================================
NOTICE: THIS SCRIPT GENERATES SYNTHETIC DEMO DATA FOR LOCAL DEVELOPMENT ONLY.
IT DOES NOT CONNECT TO REAL PAYMENT GATEWAYS OR EXECUTE LIVE RECOVERY ACTIONS.
=============================================================================
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.models import (
    Customer,
    Payment,
    Subscription,
    Invoice,
    Event,
    RecoveryCase,
    Diagnosis,
    RecoveryAction,
    ActionOutcome,
    PromiseToPay,
    CommunicationLog,
    AuditLog,
    ModelVersion,
)


def seed_database() -> None:
    """Populate local development database with realistic synthetic demo records."""
    db = SessionLocal()
    try:
        print("[SEED] Starting database demo data seeding...")
        now = datetime.now(timezone.utc)

        # 1. Customers (3 demo profiles across segments)
        customer_1 = Customer(
            external_customer_id="demo_cust_001",
            name="Apex Digital Labs",
            email="finance@apexdigital.io",
            phone="+14155552671",
            segment="ENTERPRISE",
            preferred_channel="EMAIL",
            dnd_enabled=False,
        )
        customer_2 = Customer(
            external_customer_id="demo_cust_002",
            name="Pinnacle Retail Inc",
            email="billing@pinnacleretail.com",
            phone="+14155558912",
            segment="MID_MARKET",
            preferred_channel="WHATSAPP",
            dnd_enabled=False,
        )
        customer_3 = Customer(
            external_customer_id="demo_cust_003",
            name="Sara Jenkins",
            email="sara.jenkins@example.com",
            phone="+14155559934",
            segment="CONSUMER",
            preferred_channel="SMS",
            dnd_enabled=False,
        )
        db.add_all([customer_1, customer_2, customer_3])
        db.flush()
        print(f"  [+] Inserted 3 demo customers (IDs: {customer_1.id}, {customer_2.id}, {customer_3.id})")

        # 2. Payments (Successful and Failed)
        payment_success = Payment(
            external_payment_id="demo_pay_success_101",
            customer_id=customer_1.id,
            amount=Decimal("1200.00"),
            currency="USD",
            status="SUCCESS",
            payment_method="CARD",
            paid_at=now - timedelta(days=30),
        )
        payment_failed = Payment(
            external_payment_id="demo_pay_failed_102",
            customer_id=customer_2.id,
            amount=Decimal("450.00"),
            currency="USD",
            status="FAILED",
            payment_method="CARD",
            failure_code="insufficient_funds",
            failure_description="Transaction declined: insufficient customer balance on account.",
        )
        db.add_all([payment_success, payment_failed])
        db.flush()
        print("  [+] Inserted 2 payments (1 successful, 1 failed)")

        # 3. Overdue Invoice
        invoice_overdue = Invoice(
            external_invoice_id="demo_inv_2026_001",
            customer_id=customer_2.id,
            amount=Decimal("450.00"),
            currency="USD",
            status="OVERDUE",
            due_date=now - timedelta(days=14),
        )
        db.add(invoice_overdue)
        db.flush()
        print("  [+] Inserted 1 overdue invoice")

        # 4. Incoming Gateway Event
        event_failed_payment = Event(
            external_event_id="demo_evt_webhook_pay_failed_901",
            event_type="payment.failed",
            source="GATEWAY_WEBHOOK",
            customer_id=customer_2.id,
            payment_id=payment_failed.id,
            invoice_id=invoice_overdue.id,
            payload={
                "event": "payment.failed",
                "simulated": True,
                "gateway_reference": "demo_pay_failed_102",
                "decline_details": {
                    "code": "insufficient_funds",
                    "category": "balance",
                    "retryable": True,
                },
                "amount": 45000,
                "currency": "USD",
            },
            occurred_at=now - timedelta(hours=6),
            processing_status="PROCESSED",
            processed_at=now - timedelta(hours=5, minutes=58),
        )
        db.add(event_failed_payment)
        db.flush()
        print("  [+] Inserted 1 idempotency-tracked gateway event with JSONB payload")

        # 5. Central Recovery Case
        recovery_case = RecoveryCase(
            customer_id=customer_2.id,
            event_id=event_failed_payment.id,
            payment_id=payment_failed.id,
            invoice_id=invoice_overdue.id,
            amount_at_risk=Decimal("450.00"),
            currency="USD",
            case_type="PAYMENT_FAILURE",
            status="IN_PROGRESS",
            risk_score=0.42,
            recovery_probability=0.79,
            recommended_channel="WHATSAPP",
            recommended_action="SEND_PAYMENT_LINK",
            retry_count=1,
        )
        db.add(recovery_case)
        db.flush()
        print(f"  [+] Inserted 1 central RecoveryCase (ID: {recovery_case.id})")

        # 6. Diagnosis Record
        diagnosis = Diagnosis(
            recovery_case_id=recovery_case.id,
            category="INSUFFICIENT_FUNDS",
            failure_code="INSUFFICIENT_BALANCE",
            explanation="Recurring billing attempt failed due to temporary account balance deficit. High historical lifetime value indicates high recovery propensity.",
            confidence=0.89,
        )
        db.add(diagnosis)
        db.flush()
        print("  [+] Inserted 1 failure diagnosis record")

        # 7. Planned / Executed Recovery Action & Outcome
        recovery_action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            action_type="SEND_WHATSAPP",
            channel="WHATSAPP",
            status="EXECUTED",
            reason="High recovery probability on WhatsApp channel for Mid-Market customer contact.",
            confidence=0.88,
            scheduled_at=now - timedelta(hours=5),
            executed_at=now - timedelta(hours=4, minutes=55),
        )
        db.add(recovery_action)
        db.flush()

        action_outcome = ActionOutcome(
            action_id=recovery_action.id,
            recovery_case_id=recovery_case.id,
            outcome_type="PROMISE_TO_PAY",
            recovered_amount=Decimal("0.00"),
            response_data={
                "channel": "whatsapp",
                "customer_response": "Thanks for reminding us. We will clear the balance by Friday.",
                "engagement_score": 0.95,
            },
            occurred_at=now - timedelta(hours=3),
        )
        db.add(action_outcome)
        db.flush()
        print("  [+] Inserted 1 recovery action and 1 action outcome record")

        # 8. Promise To Pay
        ptp = PromiseToPay(
            recovery_case_id=recovery_case.id,
            customer_id=customer_2.id,
            promised_amount=Decimal("450.00"),
            promised_date=now + timedelta(days=3),
            status="ACTIVE",
        )
        db.add(ptp)

        # 9. Communication Log
        comm_log = CommunicationLog(
            customer_id=customer_2.id,
            recovery_case_id=recovery_case.id,
            channel="WHATSAPP",
            direction="OUTBOUND",
            provider_message_id="demo_msg_wa_772183",
            content="Hello Pinnacle Retail, payment of $450.00 could not be processed. Tap here to retry or update your payment method.",
            status="DELIVERED",
            sent_at=now - timedelta(hours=4, minutes=55),
            delivered_at=now - timedelta(hours=4, minutes=54),
        )
        db.add(comm_log)

        # 10. Audit Log
        audit_record = AuditLog(
            recovery_case_id=recovery_case.id,
            actor_type="AI",
            actor_id="recovery_orchestrator_agent",
            action="TRIGGER_RECOVERY_ACTION",
            entity_type="RecoveryAction",
            entity_id=str(recovery_action.id),
            audit_metadata={
                "trigger": "automated_recovery_policy",
                "policy_version": "v1.0.4",
                "channel_selected": "WHATSAPP",
                "confidence": 0.88,
            },
            timestamp=now - timedelta(hours=4, minutes=55),
        )
        db.add(audit_record)

        # 11. Model Version (ML Registry)
        model_version = ModelVersion(
            model_name="recovery_propensity_model",
            version="v1.0.0",
            algorithm="LightGBM_Classifier",
            metrics={
                "auc_roc": 0.884,
                "precision": 0.812,
                "recall": 0.795,
                "f1": 0.803,
            },
            training_dataset_version="ds_synthetic_2026_q1",
            status="ACTIVE",
            deployed_at=now - timedelta(days=7),
        )
        db.add(model_version)

        db.commit()
        print("[SEED] Successfully seeded demo data!")

    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] Seeding failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
