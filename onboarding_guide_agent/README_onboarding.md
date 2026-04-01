# Ndara.ai Onboarding Guide Agent - Enterprise Microservice

This directory contains the `onboarding_guide_agent` for Ndara.ai. It is an asynchronous, fault-tolerant, continuous-learning microservice capable of robust error handling and tracking enterprise-level Live Escalations to help African B2B businesses and creators onboard smoothly.

## What is the Onboarding Guide Agent meant for?
The Onboarding Guide Agent is an independent AI microservice designed to walk new business users through the 7-Step Ndara.ai Onboarding Process:
1. Welcome & Basic Details (Business Name)
2. WhatsApp Verification (OTP)
3. Industry Selection
4. Feature Mapping (Lead Management, Invoicing, etc.)
5. Paywall / Free Trial Selection
6. Dashboard Access & Walkthrough
7. Business Data Upload for AI Training

**Key Objectives:**
- **Provide Context-Aware Guidance**: Using Retrieval-Augmented Generation (RAG) via ChromaDB to instantly answer user FAQs.
- **Continuous Learning**: Stores past successful interactions and resolutions into a Vector Database to dynamically improve future agent performance via few-shot prompting.
- **Monitor Failure Rates & Automatic Escalation**: Tracks user failures natively in SQLite (`agent_state.db`). If a user struggles repeatedly (e.g., getting stuck on an OTP step for 3 attempts), it triggers a circuit-breaker and flags a `live_agent_bridge` escalation for human takeover.

---

## Testing Utilities: `test_onboarding.py` vs `test.py`

This codebase comes with two separate testing scripts serving different purposes:

### 1. `test_onboarding.py` (CLI Interactive Simulator)
**Function**: This is an interactive terminal-based chat simulator used to test the actual conversational flow, state memory, and RAG injection without needing a running server.
- **How it works**: It directly instantiates the `OnboardingGuideAgent` and allows you to chat with the LLM in your console.
- **Use case**: Great for testing prompts, seeing how the LLM reacts to getting stuck, observing state transitions, and verifying the RAG pipeline is actively matching FAQs.

### 2. `test.py` (Integration Endpoint Tester)
**Function**: This is an automated integration script designed to test the FastAPI endpoints concurrently.
- **How it works**: It pulls the OpenAPI specification (`/openapi.json`) from the running FastAPI server (expected at `localhost:8008`) and fires predefined JSON payloads to every exposed endpoint (e.g. `/chat`, `/log_interaction`).
- **Use case**: Used to ensure that the REST API server is routing requests properly, database commits are triggering smoothly through endpoints, and the app doesn't crash on standard HTTP methods.

---

## Step-by-Step Guide: How to Test Each Endpoint

**Prerequisites:**
1. Setup your virtual environment and install dependencies: `pip install -r requirements.txt`.
2. Ensure you have an `OPENAI_API_KEY` in your `.env` file.
3. Start the FastAPI server on port 8008:
```bash
uvicorn api:app --host 0.0.0.0 --port 8008 --reload
```

### Endpoint 1: Health Check (GET `/health`)
Verifies that the agent and vector DB are initialized.
- **Request:** `curl -X GET "http://localhost:8008/health"`
- **Response:**
  ```json
  {
    "status": "healthy",
    "service": "onboarding_guide_agent"
  }
  ```

### Endpoint 2: Chat Interaction (POST `/chat`)
Conversational endpoint connecting the user's message to the LLM agent.
- **Request Payload:**
  ```json
  {
    "user_id": "user_123",
    "session_id": "session_abc",
    "current_step": 2,
    "user_message": "My OTP isn't arriving!"
  }
  ```
- **Response:**
  ```json
  {
    "response": "I'm so sorry to hear that! Sometimes WhatsApp messages delay... (LLM Response)",
    "metadata": {
      "escalate_to": null
    }
  }
  ```
  *(Note: If a user fails repeatedly, `metadata.escalate_to` will change to `"live_agent_bridge"`).*

### Endpoint 3: Log Interaction (Continuous Learning) (POST `/log_interaction`)
Used when a user successfully completes a step so the Vector DB can memorize the resolution path. This runs on a background task.
- **Request Payload:**
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
    "resolution_path": ["initial_question", "success"]
  }
  ```
- **Response:**
  ```json
  {
    "status": "accepted",
    "message": "Interaction logging initiated to Vector Database"
  }
  ```

### Endpoint 4: Get Similar AI Resolutions (GET `/ai/similar_resolutions`)
Retrieves past successful resolutions from ChromaDB based on a user's prompt (Continuous Learning in action).
- **Request:** `curl -X GET "http://localhost:8008/ai/similar_resolutions?query=otp%20issues&step_id=2&limit=3"`
- **Response:**
  ```json
  {
    "similar_resolutions": [
      {
        "interaction_id": "interaction_abcd1234",
        "similarity_score": 0.85,
        "resolution_summary": "Retrieved successful resolution strategy.",
        "time_to_resolution": 60,
        "user_satisfaction": 5,
        "full_text": "Step: WhatsApp Optimization\nConversation:\n..."
      }
    ]
  }
  ```

### Endpoint 5: Admin Transcript Retrieval (GET `/admin/escalation/{escalation_id}/transcript`)
Provides chat transcripts to an administrator during an escalation.
- **Request:** `curl -X GET "http://localhost:8008/admin/escalation/1234/transcript"`
- **Response:**
  ```json
  {
    "escalation_id": "1234",
    "transcript": [
      {
        "role": "system",
        "content": "Transcript populated securely for admin context."
      }
    ]
  }
  ```

### Endpoint 6: Admin Accepts Escalation (POST `/admin/escalation/{escalation_id}/accept`)
Locks the AI from responding further and assigns ownership to a human agent.
- **Request:** `curl -X POST "http://localhost:8008/admin/escalation/user_123_esc/accept"`
- **Response:**
  ```json
  {
    "status": "success",
    "message": "Escalation accepted. AI auto-responses suspended."
  }
  ```

### Endpoint 7: Admin Messaging (POST `/admin/escalation/{escalation_id}/message`)
Allows an admin to manually insert a message into an escalated conversation.
- **Request URL:** `curl -X POST "http://localhost:8008/admin/escalation/user_123_esc/message?message=Hello+I+am+here+to+help"`
- **Response:**
  ```json
  {
    "status": "success",
    "delivered": true,
    "message": "Hello I am here to help"
  }
  ```
