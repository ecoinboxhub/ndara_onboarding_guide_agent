# Customer AI - Business Logic

**Audience**: AI Engineers  
**Version**: 1.0  
**Last Updated**: 2025

## 1. Overview

The Customer AI system provides conversational AI for 15 industries. Each AI instance is scoped to one business and one industry. The AI obtains business context exclusively via the onboarding endpoint and stored knowledge base. Backend owns appointment booking, payments, notifications, and CRM.

---

## 2. Core Principles

| Principle | Description |
|-----------|-------------|
| **Single Data Source** | AI obtains business context exclusively via the onboarding endpoint and stored knowledge base (vector store). No direct DB or backend data access. |
| **Business Scoping** | Each AI instance is scoped to one business and one industry. An ecommerce AI does not answer real estate questions. |
| **Backend Boundary** | Backend owns: appointment booking (via its API), payment processing, inventory, notifications, CRM. AI returns structured data (intent, entities, escalation) for backend to act on. |
| **Escalation as First-Class** | Escalation to human/business owner is a first-class outcome with a dedicated endpoint and clear payload. |

---

## 3. Core Capabilities (AI Responsibility)

1. **Attend Customer** – Answer questions from knowledge base (products, services, FAQs, hours, policies).
2. **Close Sales** – Support purchase intent via product/service recommendations, upsell, and structured output for backend checkout.
3. **Book Appointment** – Extract booking entities and call backend appointment API; AI does not implement booking logic.
4. **Escalate to Human** – Detect when human intervention is needed; return structured escalation payload; backend can register via `POST /api/v1/escalate`.
5. **Meet Customer Needs** – Tailor tone, vocabulary, and escalation rules per industry.

---

## 4. AI/Backend Boundary

### AI Provides

- Response text
- Intent (e.g., `product_inquiry`, `appointment_booking`, `complaint`)
- Entities (dates, products, locations, etc.)
- Sentiment
- `escalation_required` (boolean)
- `escalation` payload (severity, context_summary, suggested_action)
- `structured_data` (e.g., booking params, product IDs)

### Backend Performs

- Actual appointment booking (via `APPOINTMENT_BOOKING_URL`)
- Payment link creation (via `PAYMENT_SERVICE_URL`) – AI detects `payment_intent`, calls backend, returns URL to user
- Payment processing
- Sending notifications (SMS, email)
- CRM updates
- Routing escalated conversations to humans

### Appointment Flow

1. AI extracts booking entities from customer message.
2. AI checks availability via backend: GET working hours + GET appointments for date; computes if slot is free.
3. If slot is booked: AI suggests alternative times from available slots.
4. If slot is free: AI calls POST `/api/bookings/appointments/` to create appointment.
5. AI returns booking result to customer.

Backend API: `APPOINTMENT_BOOKING_URL`. See ENV_TEMPLATE for `BOOKINGS_API_TOKEN`, `BOOKINGS_BUSINESS_ID_MAP`.

### Payment Flow

1. AI detects `payment_intent` from customer message.
2. AI extracts amount/reference if provided.
3. AI calls backend payment API (`PAYMENT_SERVICE_URL`): `POST /api/v1/create-payment-link` with `business_id`, `customer_id`, optional `amount`, `reference`.
4. Backend returns `{ success, payment_url }`.
5. AI returns payment URL to customer in response text and `structured_data`.

---

## 5. Escalation Flow

1. **Chat response** includes `escalation_required`, `escalation.severity`, `escalation.context_summary` when escalation is needed.
2. **Backend** decides to escalate and optionally calls `POST /api/v1/escalate` to register.
3. **Backend** routes to business owner or support; AI does not send notifications.

### Escalation Endpoint

**POST** `/api/v1/escalate?business_id={business_id}`

Request body: `conversation_id`, `customer_id`, `reason`, `severity`, `context_summary`, `conversation_history`, `customer_message`, `ai_response`.

Response: `escalation_id`, `recommended_action`, `context_for_agent`.

---

## 6. Industry Taxonomy

15 canonical industries: `ecommerce`, `healthcare`, `real_estate`, `restaurants`, `education`, `financial`, `travel`, `events`, `logistics`, `professional_services`, `beauty_wellness`, `telecoms`, `banking`, `manufacturing`, `retail_chains`.

See [docs/INDUSTRY_TAXONOMY.md](../docs/INDUSTRY_TAXONOMY.md) for aliases and mapping.

---

## 7. Industry-Specific Logic

Each industry defines:

- **Tone** (e.g., healthcare: calm, privacy-forward; ecommerce: quick, helpful)
- **Primary intents** (e.g., healthcare: appointments, results, billing; ecommerce: products, orders, returns)
- **Escalation triggers** (e.g., healthcare: medical advice, emergencies; finance: fraud, disputes)
- **Compliance** (e.g., healthcare: HIPAA; finance: audit trails)

Configuration: `customer_ai/src/domain/industries/config.py`

- `INDUSTRY_ESCALATION_TRIGGERS` – keywords per severity
- `INDUSTRY_ESCALATION_RECOMMENDATIONS` – recommended actions per severity
- `INDUSTRY_COMPLIANCE` – compliance flags and notes

---

## 8. Key Files

| File | Role |
|------|------|
| `src/api/inference_api.py` | API endpoints |
| `src/core/customer_ai_orchestrator.py` | Main coordinator |
| `src/core/business_specific_ai.py` | AI engines, RAG, response generation |
| `src/core/industry_classifier.py` | Industry classification |
| `src/core/knowledge_base.py` | RAG indexing and retrieval |
| `src/core/vector_store.py` | Vector storage |
| `src/core/appointment_booking_handler.py` | Calls backend appointment API |
| `src/domain/industries/taxonomy.py` | Industry taxonomy |
| `src/domain/industries/config.py` | Industry config, escalation, compliance |

---

## 9. Data Flow

```
Customer Message
    ↓
Chat API (/api/v1/chat)
    ↓
Orchestrator → Business AI
    ↓
Industry Engine + RAG (knowledge base)
    ↓
Intent, Sentiment, Escalation check
    ↓
OpenAI / Fine-tuned Model
    ↓
Response + structured_data + escalation (if any)
    ↓
Backend uses response; optionally calls /api/v1/escalate
```

---

## 10. Onboarding

Business data is provided via **POST /api/v1/onboard**. The AI:

1. Classifies industry
2. Validates data against industry requirements
3. Indexes in vector store (RAG)
4. Creates business-specific AI instance

No other mechanism feeds business data into the AI.
