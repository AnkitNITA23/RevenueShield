"""Realistic demonstration data seeder for production and staging demo walkthroughs."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
from typing import Any, Dict, List
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.payment import Payment
from app.models.invoice import Invoice
from app.models.event import Event
from app.models.recovery_case import RecoveryCase
from app.models.diagnosis import Diagnosis
from app.models.recovery_action import RecoveryAction
from app.models.outcome import RecoveryOutcome
from app.models.promise_to_pay import PromiseToPay
from app.models.audit_log import AuditLog
from app.models.recovery_attribution import RecoveryAttribution


def run_demo_seeder(db: Session) -> Dict[str, Any]:
    """Populates realistic multi-segment recovery cases, 30-day recovery trend, and live demo targets."""
    now = datetime.now(timezone.utc)

    # 1. Target Customer for live demo (Ankit Kumar / ByteScale Software)
    target_cust = db.scalar(select(Customer).where(Customer.email == "kdmspokharahan@gmail.com"))
    if not target_cust:
        target_cust = Customer(
            id=uuid.uuid4(),
            external_customer_id="cust_bytescale_live",
            name="ByteScale Software Pvt Ltd",
            email="kdmspokharahan@gmail.com",
            phone="+917991142735",
            segment="MID_MARKET",
            preferred_channel="VOICE",
            dnd_enabled=False,
            timezone="Asia/Kolkata",
        )
        db.add(target_cust)
        db.flush()
    else:
        target_cust.phone = "+917991142735"
        target_cust.name = "ByteScale Software Pvt Ltd"
        target_cust.segment = "MID_MARKET"
        target_cust.preferred_channel = "VOICE"
        target_cust.dnd_enabled = False
        db.flush()

    # 2. Other realistic enterprise & SMB customers
    demo_profiles = [
        ("Apex Digital Labs", "finance@apexdigital.io", "+14155552671", "ENTERPRISE", "VOICE"),
        ("CloudMatrix SaaS", "ops@cloudmatrix.io", "+14155557733", "ENTERPRISE", "WHATSAPP"),
        ("Pinnacle Retail Corp", "billing@pinnacleretail.com", "+14155558912", "MID_MARKET", "EMAIL"),
        ("Vanguard Fintech Ltd", "accounts@vanguardfintech.com", "+14155554422", "ENTERPRISE", "PAYMENT_RETRY"),
        ("Solaria Energy Systems", "admin@solariaenergy.co", "+14155559988", "SMB", "EMAIL"),
        ("Nexura Media Group", "pay@nexuramedia.com", "+14155553311", "SMB", "WHATSAPP"),
    ]

    customers = [target_cust]
    for name, email, phone, seg, chan in demo_profiles:
        c = db.scalar(select(Customer).where(Customer.email == email))
        if not c:
            c = Customer(
                id=uuid.uuid4(),
                external_customer_id=f"cust_{email.split('@')[0]}",
                name=name,
                email=email,
                phone=phone,
                segment=seg,
                preferred_channel=chan,
                dnd_enabled=False,
                timezone="UTC",
            )
            db.add(c)
            db.flush()
        customers.append(c)

    # 3. Create rich recovery cases with diagnoses and ML NBA actions
    cases_data = [
        (target_cust, Decimal("12500.00"), "IN_PROGRESS", "INSUFFICIENT_FUNDS", "VOICE", 0.78, Decimal("9750.00")),
        (customers[1], Decimal("45000.00"), "IN_PROGRESS", "CARD_LIMIT_EXCEEDED", "VOICE", 0.85, Decimal("38250.00")),
        (customers[2], Decimal("28000.00"), "RECOVERED", "AUTHENTICATION_FAILED", "WHATSAPP", 0.92, Decimal("25760.00")),
        (customers[3], Decimal("18500.00"), "RECOVERED", "EXPIRED_CARD", "EMAIL", 0.88, Decimal("16280.00")),
        (customers[4], Decimal("65000.00"), "RECOVERED", "BANK_SYSTEM_ERROR", "PAYMENT_RETRY", 0.95, Decimal("61750.00")),
        (customers[5], Decimal("9800.00"), "OPEN", "DO_NOT_HONOR", "EMAIL", 0.62, Decimal("6076.00")),
        (customers[6], Decimal("15200.00"), "IN_PROGRESS", "INSUFFICIENT_FUNDS", "WHATSAPP", 0.74, Decimal("11248.00")),
    ]

    created_cases = 0
    for cust, amt, status, diag_code, rec_act, prob, erv in cases_data:
        existing_case = db.scalar(select(RecoveryCase).where(RecoveryCase.customer_id == cust.id))
        if existing_case:
            existing_case.status = status
            existing_case.amount_at_risk = amt
            existing_case.currency = "INR"
            case = existing_case
        else:
            evt = Event(
                id=uuid.uuid4(),
                external_event_id=f"evt_seed_{uuid.uuid4().hex[:8]}",
                event_type="payment.failed",
                source="RAZORPAY",
                payload={"amount": int(amt * 100)},
            )
            db.add(evt)
            db.flush()

            case = RecoveryCase(
                id=uuid.uuid4(),
                customer_id=cust.id,
                event_id=evt.id,
                amount_at_risk=amt,
                currency="INR",
                case_type="PAYMENT_FAILURE",
                status=status,
                attempt_count=1,
                priority="HIGH" if amt > Decimal("20000.00") else "NORMAL",
            )
            db.add(case)
            db.flush()
            created_cases += 1

            # Diagnosis
            diag = Diagnosis(
                id=uuid.uuid4(),
                case_id=case.id,
                primary_root_cause=diag_code,
                confidence_score=prob,
                is_recoverable=True,
                explanation=f"Autonomous diagnostic engine classified payment decline as {diag_code}.",
            )
            db.add(diag)

            # Recovery Action
            act = RecoveryAction(
                id=uuid.uuid4(),
                case_id=case.id,
                action_type=rec_act,
                status="COMPLETED" if status == "RECOVERED" else "EXECUTED",
                ranking_score=prob,
                channel=rec_act,
            )
            db.add(act)

            # Audit Log
            audit = AuditLog(
                id=uuid.uuid4(),
                case_id=case.id,
                action="AUTONOMOUS_NBA_ORCHESTRATED",
                details={"action_type": rec_act, "probability": prob, "erv": float(erv)},
            )
            db.add(audit)

    # 4. Create Active Promise-to-Pay agreements
    ptp_1 = db.scalar(select(PromiseToPay).where(PromiseToPay.customer_id == target_cust.id))
    if not ptp_1:
        ptp_1 = PromiseToPay(
            id=uuid.uuid4(),
            customer_id=target_cust.id,
            promised_amount=Decimal("12500.00"),
            currency="INR",
            promised_date=now + timedelta(days=2),
            status="ACTIVE",
            source="TWILIO_VOICE",
            confidence_score=0.90,
            notes="Customer confirmed invoice payment during Twilio AI Voice call.",
        )
        db.add(ptp_1)

    ptp_2 = db.scalar(select(PromiseToPay).where(PromiseToPay.customer_id == customers[1].id))
    if not ptp_2:
        ptp_2 = PromiseToPay(
            id=uuid.uuid4(),
            customer_id=customers[1].id,
            promised_amount=Decimal("45000.00"),
            currency="INR",
            promised_date=now + timedelta(days=1),
            status="ACTIVE",
            source="TWILIO_VOICE",
            confidence_score=0.95,
            notes="Finance director scheduled card limit increase for tomorrow morning.",
        )
        db.add(ptp_2)

    # 5. Populate 30 Days of Historical Recovery Outcomes for rich charts
    # Generates a continuous daily and cumulative recovery progression
    daily_recoveries = [
        (28, Decimal("8500.00"), "EMAIL"),
        (26, Decimal("14000.00"), "VOICE"),
        (24, Decimal("6200.00"), "PAYMENT_RETRY"),
        (21, Decimal("22000.00"), "WHATSAPP"),
        (19, Decimal("9500.00"), "EMAIL"),
        (16, Decimal("18500.00"), "VOICE"),
        (14, Decimal("11000.00"), "PAYMENT_RETRY"),
        (11, Decimal("15500.00"), "WHATSAPP"),
        (8, Decimal("28000.00"), "VOICE"),
        (5, Decimal("18500.00"), "EMAIL"),
        (2, Decimal("65000.00"), "PAYMENT_RETRY"),
    ]

    for days_ago, amt, chan in daily_recoveries:
        outcome_time = now - timedelta(days=days_ago)
        existing_outcome = db.scalar(
            select(RecoveryOutcome).where(RecoveryOutcome.amount_recovered == amt)
        )
        if not existing_outcome:
            outc = RecoveryOutcome(
                id=uuid.uuid4(),
                case_id=customers[2].id,
                amount_recovered=amt,
                currency="INR",
                channel_used=chan,
                occurred_at=outcome_time,
                verified=True,
                attribution_window_hours=72,
            )
            db.add(outc)

            attr = RecoveryAttribution(
                id=uuid.uuid4(),
                outcome_id=outc.id,
                channel=chan,
                attribution_weight=1.0,
            )
            db.add(attr)

    db.commit()

    return {
        "customers_seeded": len(customers),
        "cases_seeded": len(cases_data),
        "target_customer": "ByteScale Software (kdmspokharahan@gmail.com / +917991142735)",
        "active_ptp_volume": "₹57,500.00",
        "historical_recovered_total": "₹2,16,700.00",
    }
