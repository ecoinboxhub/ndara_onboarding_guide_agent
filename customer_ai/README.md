# ndara.ai Customer AI

AI-powered customer service system built on **LangGraph** (stateful agent graph with tool calling). Each onboarded business gets a compiled agent graph whose LLM decides which tools to call — knowledge search, product lookup, appointment booking, payment links — instead of hard-coded if/else branches.

## Architecture

```
POST /api/v1/chat
  → Orchestrator (greeting logic, conversation manager)
    → LangGraph StateGraph
        ┌─────────────────────────────────────────┐
        │  agent (LLM + bound tools)              │
        │    ↕ tool_calls? → ToolNode → agent     │
        │    ↓ no tool_calls                      │
        │  post-process (human behaviour sim)     │
        └─────────────────────────────────────────┘
    → CustomerResponse (Pydantic)
```

## Features

- **LangGraph Agent Loop**: The model decides which tools to call; no hard-coded intent routing
- **RAG (Retrieval Augmented Generation)**: Vector-search tool the agent calls when it needs business facts
- **Tool Calling**: `search_knowledge`, `get_product_info`, `calculate_order_total`, `check_appointment_availability`, `book_appointment`, `create_payment_link`
- **Business-Specific Training**: Each business gets a compiled agent with its own tools and system prompt
- **Industry Classification**: Automatic industry detection and specialised personality
- **Greeting Logic**: Introduction (first-time), day-greeting (new day), or no-greeting — driven by backend context flags
- **Human Behaviour Simulation**: Ultra-concise Nigerian style, AI-phrase removal
- **Escalation Detection**: Agent output + sentiment trigger escalation payloads
- **Backward-Compatible API**: Same POST `/api/v1/chat` contract; response shape unchanged

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd customer_ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp ENV_TEMPLATE.txt .env

# Edit .env and set your OpenAI API key
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run

```bash
# Development mode
python main.py

# Production mode (Linux/Mac)
./start_production.sh

# Production mode (Windows)
start_production.bat
```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

## API Endpoints

### Onboard Business
```bash
POST /api/v1/onboard?business_id=1
Content-Type: application/json

{
  "business_info": {
    "name": "My Business",
    "description": "Business description",
    "phone": "+1234567890",
    "email": "contact@business.com",
    "address": "123 Main St",
    "timezone": "Africa/Lagos",
    "whatsapp_number": "+1234567890"
  },
  "products": [...],
  "services": [...],
  "faqs": [...],
  "policies": {...},
  "business_hours": {...},
  "ai_settings": {...}
}
```

### Chat
```bash
POST /api/v1/chat?business_id=1
Content-Type: application/json

{
  "message": "What products do you have?",
  "customer_id": "customer_123",
  "context": {}
}
```

### Extract Intent
```bash
POST /api/v1/extract-intent?business_id=1
Content-Type: application/json

{
  "message": "I want to book an appointment"
}
```

## Environment Variables

See `ENV_TEMPLATE.txt` for all available configuration options.

**Required:**
- `OPENAI_API_KEY`: Your OpenAI API key

**Optional:**
- `API_HOST`: Server host (default: 0.0.0.0)
- `API_PORT`: Server port (default: 8000)
- `VECTOR_STORAGE_MODE`: "local" (ChromaDB) or "pgvector" (PostgreSQL with pgvector, recommended for production)
- `LOG_LEVEL`: Logging level (default: INFO)

## Project Structure

```
customer_ai/
├── src/
│   ├── api/
│   │   └── inference_api.py      # FastAPI endpoints (v3)
│   └── core/
│       ├── customer_agent.py     # LangGraph StateGraph (agent loop)
│       ├── agent_tools.py        # Tools the agent can call
│       ├── agent_output.py       # Pydantic response models
│       ├── customer_ai_orchestrator.py  # Greeting logic, escalation, routing
│       ├── business_specific_ai.py      # Data holder + onboarding utilities
│       ├── knowledge_base.py     # RAG indexing and retrieval
│       ├── prompts.py            # System prompt library + personalities
│       ├── human_behavior_simulator.py  # Post-processing (concise, natural)
│       ├── appointment_booking_handler.py
│       ├── payment_handler.py
│       ├── conversation_manager.py      # Escalation tracking
│       └── ...
├── schemas/           # Data schemas
├── main.py           # Entry point
├── requirements.txt  # Dependencies (langgraph, langchain-openai, ...)
├── ENV_TEMPLATE.txt  # Environment template
└── PRODUCTION.md     # Production deployment guide
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
```

### Linting
```bash
flake8 .
```

## Production Deployment

See [PRODUCTION.md](./PRODUCTION.md) for detailed production deployment instructions.

**Key caveats:**
- All runtime state (onboarded businesses, agent graphs) is **in-memory** — a restart requires re-onboarding. Plan automated re-onboarding from the backend after deploys.
- The API has **no built-in authentication or rate limiting** — deploy behind an API gateway that enforces both.

## Documentation

- API Documentation: Available at `/docs` when server is running
- Production Guide: See [PRODUCTION.md](./PRODUCTION.md)
- Business Logic: See [BUSINESS_LOGIC.md](./BUSINESS_LOGIC.md) for AI scope, backend boundary, and escalation flow
- Industry Taxonomy: See [docs/INDUSTRY_TAXONOMY.md](../docs/INDUSTRY_TAXONOMY.md) for canonical industry keys and aliases
- Schema Documentation: See `schemas/data_schemas.json`

