from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Revenue Recovery AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ALLOWED_ORIGINS: str = "*"

    # Database Configuration
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/revenue_recovery"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Optional[str]) -> str:
        if not v:
            return "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/revenue_recovery"
        val = str(v).strip()
        if val.startswith("postgres://"):
            return val.replace("postgres://", "postgresql+psycopg2://", 1)
        if val.startswith("postgresql://") and not val.startswith("postgresql+"):
            return val.replace("postgresql://", "postgresql+psycopg2://", 1)
        return val

    # Razorpay Test / Live Mode Credentials (Loaded from environment)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None

    # Execution Mode: "dry_run" (simulated provider) or "razorpay_test" (live Razorpay Test API)
    EXECUTION_MODE: str = "dry_run"

    # Communication & WhatsApp Configuration
    COMMUNICATION_MODE: str = "twilio"  # "dry_run", "development", or "twilio"
    WHATSAPP_MODE: str = "REAL"  # "REAL" or "DRY_RUN"
    TWILIO_WHATSAPP_MODE: str = "SANDBOX"  # "SANDBOX" or "PRODUCTION"
    MAX_WHATSAPP_ATTEMPTS: int = 3
    WHATSAPP_COOLDOWN_MINUTES: int = 1440  # 24 hours cooldown between messages
    DND_START_TIME: str = "20:00"
    DND_END_TIME: str = "08:00"
    WHATSAPP_DND_START_HOUR: int = 20  # 20:00 (8 PM)
    WHATSAPP_DND_END_HOUR: int = 8  # 08:00 (8 AM)
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # Twilio Voice & WhatsApp Credentials
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None  # e.g., "+14155552671"
    TWILIO_WEBHOOK_BASE_URL: Optional[str] = None  # Public tunnel or domain for Twilio webhooks
    TWILIO_API_KEY_SID: Optional[str] = None
    TWILIO_API_KEY_SECRET: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None  # e.g., "whatsapp:+14155238886"
    TWILIO_WHATSAPP_TO: Optional[str] = None    # e.g., "whatsapp:+919876543210"
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    TWILIO_STATUS_CALLBACK_URL: Optional[str] = None
    MAX_VOICE_ATTEMPTS: int = 3
    VOICE_COOLDOWN_MINUTES: int = 60

    # SMTP Email Recovery Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "RevenueShield Recovery"
    SMTP_USE_TLS: bool = True

    # Intelligent Recovery Sequencer Settings
    MAX_RECOVERY_STEPS: int = 3
    RECOVERY_REEVALUATION_HOURS: int = 24
    MAX_RECOVERY_DURATION_HOURS: int = 72

    # Self-Learning Feedback Loop Settings
    ATTRIBUTION_WINDOW_HOURS: int = 24
    RETRAINING_SCHEDULE_THRESHOLD: int = 100

    # Promise-to-Pay & Escalation Settings
    PROMISE_MIN_AMOUNT: float = 10000.0
    PROMISE_MIN_OVERDUE_HOURS: int = 24
    PROMISE_MAX_DAYS_AHEAD: int = 7
    PROMISE_EXPIRATION_GRACE_HOURS: int = 24

    # Internal Server-to-Server API Security
    INTERNAL_API_SECRET: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
