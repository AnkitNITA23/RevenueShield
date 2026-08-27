"""Event Processing Service.

Decoupled core processing service for incoming payment & billing events.
Handles idempotency, entity reconciliation, RecoveryCase state transitions,
and compliance audit logging.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.payment import Payment
from app.models.event import Event
from app.models.recovery_case import RecoveryCase
from app.models.audit_log import AuditLog
from app.schemas.event import NormalizedEvent, WebhookProcessingResult
from app.services.customer_service import CustomerService
from app.diagnosis.service import DiagnosisService
from app.decision.service import DecisionService
from app.outcomes.engine import OutcomeEngine
from app.learning.service import LearningDataService
from app.integrations.razorpay.payment_normalizer import PaymentNormalizer, NormalizedPaymentData
from app.repositories.payment_repository import PaymentRepository


class EventProcessor:
    """Core domain service for ingesting and processing normalized events."""

    @classmethod
    def process_normalized_event(
        cls, db: Session, event: NormalizedEvent
    ) -> WebhookProcessingResult:
        """Process a normalized event idempotently and transition recovery workflows.

        Args:
            db: Database session.
            event: Normalized incoming event.

        Returns:
            WebhookProcessingResult with execution status.
        """
        # 1. Idempotency Check: Prevent duplicate event processing
        existing_event = db.scalar(
            select(Event).where(Event.external_event_id == event.event_id)
        )
        if existing_event:
            # Find associated recovery case if any
            existing_case = db.scalar(
                select(RecoveryCase).where(RecoveryCase.event_id == existing_event.id)
            )
            return WebhookProcessingResult(
                status="duplicate",
                event_id=event.event_id,
                internal_event_id=str(existing_event.id),
                recovery_case_id=str(existing_case.id) if existing_case else None,
                message="Duplicate event detected; skipped processing.",
            )

        try:
            # 2. Resolve or provision customer
            customer: Customer = CustomerService.resolve_or_create_customer(db, event)

            # 3. Resolve or create Payment record via unified PaymentRepository
            payment: Optional[Payment] = None
            if event.external_payment_id:
                if event.raw_payload:
                    try:
                        norm_payment = PaymentNormalizer.normalize_webhook(event.raw_payload)
                    except Exception:
                        norm_payment = None
                else:
                    norm_payment = None

                if not norm_payment:
                    # Construct fallback normalized payment from event fields
                    norm_payment = NormalizedPaymentData(
                        external_payment_id=event.external_payment_id,
                        razorpay_order_id=None,
                        amount=event.amount,
                        currency=event.currency,
                        status="CAPTURED" if event.event_type == "payment.captured" else ("FAILED" if event.event_type == "payment.failed" else "UNKNOWN"),
                        payment_method=event.payment_method or "CARD",
                        bank=None,
                        wallet=None,
                        vpa=None,
                        international=False,
                        captured=(event.event_type == "payment.captured"),
                        amount_refunded=event.amount if event.event_type == "refund.processed" else Decimal("0.00"),
                        refund_status=None,
                        description=None,
                        error_code=event.failure_code,
                        error_description=event.failure_description,
                        error_source=None,
                        error_step=None,
                        error_reason=event.failure_reason,
                        paid_at=event.occurred_at if event.event_type == "payment.captured" else None,
                        razorpay_created_at=event.occurred_at or datetime.now(timezone.utc),
                        customer_id_ext=event.external_customer_id,
                        customer_email=event.customer_email,
                        customer_phone=event.customer_phone,
                        customer_name=event.customer_name,
                        raw_payload=event.raw_payload or {},
                    )

                payment, _ = PaymentRepository.upsert_payment(db=db, data=norm_payment, customer_id=customer.id)

            # 4. Store Event record with raw payload
            db_event = Event(
                external_event_id=event.event_id,
                event_type=event.event_type,
                source=event.source,
                customer_id=customer.id,
                payment_id=payment.id if payment else None,
                payload=event.raw_payload,
                occurred_at=event.occurred_at,
                processing_status="PROCESSED",
                processed_at=datetime.now(timezone.utc),
            )
            db.add(db_event)
            db.flush()

            # 5. RecoveryCase State Machine & Lifecycle Transitions
            recovery_case: Optional[RecoveryCase] = None

            if event.event_type == "payment.failed":
                # Create or reopen RecoveryCase for failed transaction
                recovery_case = RecoveryCase(
                    customer_id=customer.id,
                    event_id=db_event.id,
                    payment_id=payment.id if payment else None,
                    amount_at_risk=event.amount,
                    currency=event.currency,
                    case_type="PAYMENT_FAILURE",
                    status="OPEN",
                )
                db.add(recovery_case)
                db.flush()

                # Record immutable audit log
                audit = AuditLog(
                    recovery_case_id=recovery_case.id,
                    actor_type="SYSTEM",
                    actor_id="razorpay_webhook_processor",
                    action="RECOVERY_CASE_OPENED",
                    entity_type="RecoveryCase",
                    entity_id=str(recovery_case.id),
                    audit_metadata={
                        "event_id": event.event_id,
                        "failure_code": event.failure_code,
                        "failure_description": event.failure_description,
                        "amount_at_risk": str(event.amount),
                        "currency": event.currency,
                    },
                )
                db.add(audit)
                db.flush()

                # Automatically trigger Diagnosis Engine for failed payments
                diagnosis = DiagnosisService.diagnose_case(
                    db=db,
                    recovery_case=recovery_case,
                    event=event,
                )

                # Automatically trigger Recovery Decision Engine
                action = DecisionService.generate_recommendation(
                    db=db,
                    recovery_case=recovery_case,
                    diagnosis=diagnosis,
                )

                # Automatically create pending point-in-time LearningExample
                if action:
                    LearningDataService.create_initial_example(
                        db=db,
                        recovery_case=recovery_case,
                        action=action,
                        diagnosis=diagnosis,
                    )

                # Initialize Intelligent Recovery Plan for the case
                from app.services.recovery_scheduler import RecoveryScheduler
                RecoveryScheduler.create_or_get_plan(
                    db=db,
                    case_id=recovery_case.id,
                )

            elif event.event_type == "payment.captured":
                # Locate open recovery case associated with this payment or customer
                if payment:
                    recovery_case = db.scalar(
                        select(RecoveryCase).where(
                            RecoveryCase.payment_id == payment.id,
                            RecoveryCase.status.in_(["OPEN", "IN_PROGRESS", "PTP"]),
                        )
                    )

                if not recovery_case:
                    # Fallback match by customer and amount if payment reference was decoupled
                    recovery_case = db.scalar(
                        select(RecoveryCase).where(
                            RecoveryCase.customer_id == customer.id,
                            RecoveryCase.status.in_(["OPEN", "IN_PROGRESS", "PTP"]),
                            RecoveryCase.amount_at_risk == event.amount,
                        )
                    )

                if recovery_case:
                    OutcomeEngine.process_payment_capture(
                        db=db,
                        recovery_case=recovery_case,
                        captured_amount=event.amount,
                        captured_at=event.occurred_at or datetime.now(timezone.utc),
                        provider_event_id=event.event_id,
                    )

            db.commit()

            return WebhookProcessingResult(
                status="processed",
                event_id=event.event_id,
                internal_event_id=str(db_event.id),
                recovery_case_id=str(recovery_case.id) if recovery_case else None,
                message=f"Event {event.event_type} successfully processed.",
            )

        except IntegrityError:
            db.rollback()
            # Handle concurrent race conditions on external_event_id database uniqueness
            existing_event = db.scalar(
                select(Event).where(Event.external_event_id == event.event_id)
            )
            return WebhookProcessingResult(
                status="duplicate",
                event_id=event.event_id,
                internal_event_id=str(existing_event.id) if existing_event else None,
                message="Duplicate event caught by database constraint; safely skipped.",
            )
        except Exception:
            db.rollback()
            raise
