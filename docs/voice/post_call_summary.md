## Post-Call Summary (Owner-Facing)

The agent must produce a concise summary and action items after each call, delivered to the business owner via webhook.

### Summary Prompt Pattern
“Provide a short summary for the business owner about this call with {first_name}. Include: purpose, key facts, decisions/commitments, follow‑ups, and any risks. Keep it concise.”

### Webhook Payload Schema
```
{
  "call_id": "string",
  "business_id": "string",
  "customer_id": "string",
  "summary": "string",
  "action_items": ["string"],
  "tags": ["string"],
  "transcript_url": "string",
  "confidence": 0.0
}
```

### Examples
Booking
“Caller booked consultation for Tue 10am. Needs pricing email. Please confirm consultant availability.”

Complaint
“Delivery delay reported. Promised owner follow‑up today before 4pm. Risk: churn if not resolved.”

### Delivery and Retries
- Owner webhook endpoint receives payload within 5 seconds after call end
- Retry with exponential backoff for up to 3 attempts


