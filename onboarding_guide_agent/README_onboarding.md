# Onboarding Guide Agent - Enterprise Microservice

This directory contains the completely refactored `onboarding_guide_agent` for Ndara.ai. It has been completely upgraded into an asynchronous, fault-tolerant, continuous-learning microservice capable of robust error handling and tracking enterprise-level Live Escalations.

## Overview and Key Features

- **Asynchronous Fault Tolerance**: Built on `openai.AsyncOpenAI` using `tenacity` exponential backoffs. It gracefully handles API limits, temporarily triggering a strict Circuit Breaker if limits are breached concurrently.
- **Live Escalation Database State**: Utilizes local `SQLAlchemy/aiosqlite` schema to aggressively track individual `FailureLogs`. The agent monitors user interaction locally. Repeated failures trigger Admin Live Agent escalations naturally.  
- **Advanced Continuous Learning (RAG)**: Relies on `ChromaDB` configured with dynamic indexes (`step_resolutions`, `user_segments`). When users successfully pass onboarding hurdles, their conversation paths are natively embedded into the DB. The LLM explicitly searches these successful logs dynamically to apply "few-shot" prompting fixes to new struggling users.

---

## 🏗️ 1. Environment & Setup

Since the agent operates as an independent microservice within the broader `AI-PROJECT`, you can utilize the root virtual environment or deploy it standalone.

### Local Virtual Environment
Ensure you are inside the `AI-PROJECT` root folder on Windows:
```bash
# Activate the root virtual environment
.venv\Scripts\activate

# Navigate into the agent module
cd onboarding_guide_agent

# Install dependencies (FastAPI, SQLAlchemy, Tenacity, ChromaDB, etc.)
pip install -r requirements.txt
```

### Essential `.env` Configurations
Ensure your `.env` file (located in `onboarding_guide_agent/.env` or root folder) contains your external LLM keys:
```env
OPENAI_API_KEY=sk-your-real-key-here
```

### Standalone Docker Deployment (DevOps)
Mount the port `8008` and persist the `/app/vectordb` volume to ensure learning databases survive restarts.
```bash
docker build -t ndara_onboarding_agent .
docker run -p 8008:8008 -v $(pwd)/vectordb:/app/vectordb --env-file .env ndara_onboarding_agent
```

---

## 💻 2. Interactive Terminal Testing

Before hooking into standard frontend UI pathways, you can vigorously test the Chatflow, the Learning Logic, and the Failure Escalations intuitively via the CLI:
```bash
python test_onboarding.py
```

**How the Simulator Works:**
1. The Terminal operates via synchronous `asyncio.run()` wrappers.
2. It interacts natively with the asynchronous Database, injecting `test_user_001` natively.
3. **Escalation Trigger**: Try entering invalid inputs over and over! After 3 unsuccessful inputs on the exact same numeric step, the agent's internal backend will automatically flag `live_agent_bridge` via metadata tracking and notify you.

---

## 📡 3. Microservice API Architecture

To integrate this properly with Next.js, Flutter, or Node endpoints, spin up the server:
```bash
uvicorn api:app --host 0.0.0.0 --port 8008 --reload
```

Interactive OpenAPI documentation is dynamically available at `http://localhost:8008/docs`.

### A. Core Chat Endpoint
**`POST /chat`**
Takes user input and runs it against the Circuit-breakers, the Database State Machine, and the Few-Shot RAG injection.
```json
{
  "user_id": "user_123",
  "session_id": "session_abc",
  "current_step": 2,
  "user_message": "My OTP isn't arriving!"
}
```
**Escalation Logic**: If the database dictates the user has failed 3 times, the response `metadata` dictionary will include:
```json
{
  "escalate_to": "live_agent_bridge",
  "locked": false
}
```
*Frontend Action Required*: When `escalate_to` triggers, gracefully inform the user and pass the ticket to the Human Admin system. If `locked: true`, this means a Human has formally accepted the Chat from the admin panel and the AI refuses to answer automatically.

---

### B. Admin & Escalation Routes
Once an escalation happens, WebSockets/Emails ping the humans (Mocked via Terminal Logs natively). Humans can hook up to the chat via API hooks:
- **`GET /admin/escalation/{id}/transcript`**: Pulls formatted JSON chat history for the admin dash.
- **`POST /admin/escalation/{id}/accept`**: A human formally accepts the ticket. The specific `Escalation` database status shifts to `accepted`, which physically locks the generative AI off the chat flow for `user_123` via server-side checks.
- **`POST /admin/escalation/{id}/message`**: Admins inject raw system payloads into the user chat session seamlessly.

---

### C. Continuous Learning Loop Routes
To ensure the LLM improves natively without manual intervention, you must instruct your Frontend/Backend orchestrators to send success markers to the agent.

**`POST /log_interaction`**
When the user clicks "Step 2 Processed Correctly" on their UI, submit the entire chat history for that step to the `/log_interaction` API.
```json
{
  "user_id": "user_123",
  "session_id": "session_001",
  "step_id": "2",
  "step_name": "WhatsApp Optimization",
  "success": true,
  "conversation_turns": [
    {"role": "user", "content": "How do I trigger OTP?", "timestamp": "2026-03-30T10:00:00Z"},
    {"role": "assistant", "content": "Click the big blue button.", "timestamp": "2026-03-30T10:01:00Z"}
  ],
  "resolution_path": ["initial_question", "success"],
  "time_to_resolution_seconds": 60,
  "user_satisfaction_score": 5,
  "metadata": {
    "issue_category": "whatsapp_otp"
  }
}
```
*Processing Check*: This endpoint returns a `202 Accepted` immediately and strictly processes ChromaDB embeddings in an isolated Background Task to prevent REST blocking.

**`GET /ai/similar_resolutions`**
Natively triggered by the agent physically internally, but exposed via REST for manual frontend inspection. Pulls dynamic resolutions matched geographically or structurally to historical issues.

## Notes on File Structure and State
- The default setup initiates SQLite instances targeting `./vectordb/agent_state.db` via `aiosqlite`. This couples natively with the embedded ChromeDB storage seamlessly. 
- *Note*: You can aggressively scale this microservice into `asyncpg` or `aiomysql` by swapping the `DATABASE_URL` structure within `database.py`. No queries need syntax updating thanks to high-level `SQLAlchemy` ORM mapping.
