"""Script to trigger an instant live Twilio Voice Call to your phone (+917991142735)."""
import os
import sys
from twilio.rest import Client

# Twilio Credentials (loaded exclusively from environment variables)
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_number = os.getenv("TWILIO_PHONE_NUMBER")
to_number = "+917991142735"

print("=" * 70)
print("📞 REVENUESHIELD — TRIGGER LIVE VOICE RECOVERY CALL")
print("=" * 70)
print(f"From (Twilio AI Agent): {from_number}")
print(f"To (Recipient Phone):   {to_number}")
print("Connecting to Twilio Voice API...")

twiml_speech = """<Response>
    <Say voice="Polly.Aditi" language="en-IN">Namaste Ankit! This is RevenueShield's Autonomous AI Recovery Assistant calling on behalf of ByteScale Software. We noticed an outstanding payment of 12,500 Rupees for invoice number INV-9821 was recently declined by your bank due to temporary insufficient funds. Would you like to schedule an arrangement or receive a payment link?</Say>
    <Gather input="speech" timeout="5" speechTimeout="auto" action="https://revenueshield-backend.onrender.com/webhooks/twilio/status">
        <Say voice="Polly.Aditi" language="en-IN">Please speak your response now.</Say>
    </Gather>
</Response>"""

try:
    if not account_sid or not auth_token:
        raise ValueError("TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is not set in environment.")
    client = Client(account_sid, auth_token)
    call = client.calls.create(
        to=to_number,
        from_=from_number,
        twiml=twiml_speech
    )
    print("\n" + "=" * 70)
    print("🎉 SUCCESS! LIVE CALL HAS BEEN INITIATED!")
    print(f"Call SID: {call.sid}")
    print(f"Call Status: {call.status}")
    print("Your phone +917991142735 will ring right now!")
    print("=" * 70)
except Exception as e:
    print(f"\nNote: {e}")
