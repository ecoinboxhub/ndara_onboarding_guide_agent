# System Architecture

## System Design Philosophy

### Three Core Systems

**Customer AI** and **Business Owner AI** are the core AI services in this repository. **Invoice Generator** and **Inventory Management** are handled by backend services (moved to backend repo):

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AI-PROJECT Platform                          │
├──────────────┬──────────────────┬──────────────────┬────────────────┤
│ Customer AI  │ Business Owner AI│ Invoice Generator│Inventory Mgmt  │
│              │                  │                  │                │
│ End Customers│ Business Owners  │  Backend Service │ Backend Service│
│ Sales/Support│ Business Intel   │  Auto Generation │ Auto Operations│
│ Products/Serv│ Analytics        │  Products/Serv   │ Products/Serv  │
│ Customer Help│ Strategic Insights│  Invoice Docs    │ Stock/Resources│
└──────────────┴──────────────────┴──────────────────┴────────────────┘
```

### Business-Specific Training

Each business gets its own AI instance trained only on their data:

```
Business Owner → Provides Minimal Data → AI Training
                                           ↓
                           Business-Specific AI Instance
                                           ↓
                  Only Answers Questions About THAT Business
```

## Customer AI Architecture

### Core Components

```python
customer_ai/
├── src/
│   ├── core/                  # Core AI logic
│   │   ├── prompts.py                      # All prompts + management
│   │   ├── business_specific_ai.py         # Main AI engine
│   │   ├── customer_ai_orchestrator.py     # System coordinator
│   │   ├── conversation_manager.py         # Conversation tracking
│   │   ├── industry_classifier.py          # Industry classification
│   │   ├── data_ingestion.py               # Data processing
│   │   ├── budget_optimizer.py             # Cost optimization
│   │   └── [integrations].py               # Google Maps, Calendar, OCR
│   │
│   ├── api/                   # REST API
│   │   └── customer_ai_api.py              # FastAPI endpoints
│   │
│   ├── models/                # Data models
│   │   ├── database_models.py              # SQLAlchemy models
│   │   ├── conversation_models.py          # Conversation data
│   │   └── ai_response_models.py           # Response models
│   │
│   ├── services/              # Business logic
│   │   ├── database_service.py             # Database operations
│   │   └── openai_service.py               # OpenAI integration
│   │
│   └── utils/                 # Utilities
│       ├── config.py                       # Configuration
│       └── error_handler.py                # Error handling
│
├── requirements.txt           # Dependencies
└── main.py                    # Application entry
```

### Data Flow

```
Customer Message
    ↓
Industry Classification
    ↓
Sentiment & Intent Analysis
    ↓
Prompt Selection (from 150+ prompts)
    ↓
Business-Specific Context Injection
    ↓
OpenAI API Call
    ↓
Response to Customer
```

### Industry Engines

15+ industry-specific AI engines, each with:
- Custom intent analysis
- Industry-specific response patterns
- Specialized personalities
- Compliance requirements (e.g., HIPAA for healthcare)

## Business Owner AI Architecture

### Core Components

```python
business_owner_ai/
├── src/
│   ├── core/                  # Core business intelligence
│   │   ├── prompts.py                      # All business prompts + management
│   │   ├── business_intelligence.py        # Main orchestrator
│   │   ├── strategic_advisor.py            # Strategic planning
│   │   ├── financial_analyzer.py           # Financial intelligence
│   │   ├── operations_optimizer.py         # Operations optimization
│   │   ├── marketing_intelligence.py       # Marketing analytics
│   │   ├── risk_manager.py                 # Risk management
│   │   └── growth_strategist.py            # Growth strategies
│   │
│   ├── api/                   # REST API
│   │   └── business_owner_api.py           # FastAPI endpoints
│   │
│   ├── models/                # Data models
│   │   ├── business_models.py              # Business data models
│   │   └── analysis_models.py              # Analysis results
│   │
│   ├── services/              # Business logic
│   │   ├── data_analysis_service.py        # Data analysis
│   │   └── openai_service.py               # OpenAI integration
│   │
│   └── utils/                 # Utilities
│       ├── config.py                       # Configuration
│       └── report_generator.py             # Reporting
│
├── requirements.txt           # Dependencies
└── main.py                    # Application entry
```

### Data Flow

```
Business Owner Query
    ↓
Query Type Classification
    ↓
Data Aggregation (Financial, Operational, Market)
    ↓
Prompt Selection (from 100+ business prompts)
    ↓
Analysis & Intelligence Generation
    ↓
Strategic Recommendations
    ↓
Insights to Business Owner
```

## Backend Services (Separate Repository)

**Note**: Invoice Generator and Inventory Management have been moved to the backend repository. They are backend services that integrate with Customer AI and Business Owner AI.

### Invoice Generator (Backend Service)
- Handles automatic invoice generation when sales close
- Port 8004
- Auto-detects invoice type (Product vs Service) based on industry
- Generates invoices for products and services

### Inventory Management (Backend Service)
- Handles automatic inventory operations
- Port 8005
- Manages stock levels, reorder points, and inventory tracking

## Key Architectural Principles

### 1. Separation of Concerns
- Customer AI handles customer interactions
- Business Owner AI handles business intelligence
- Invoice Generator and Inventory Management are backend services (separate repository)
- No overlap in functionality

### 2. Business-Specific Training
- Each business gets isolated AI instance
- No cross-business data sharing
- AI trained only on that business's data

### 3. Minimal Data Approach
- Business owners provide minimal information
- AI generates comprehensive context automatically
- Leverages OpenAI's knowledge base

### 4. Industry-Specific Optimization
- Each industry has dedicated engine
- Industry-specific prompts and personalities
- Compliance and regulatory awareness

### 5. Scalability
- Stateless API design
- Database-backed persistence
- Horizontal scaling capable
- Multi-tenant architecture

## Database Schema

### Customer AI Database

```sql
businesses
  - business_id (PK)
  - business_name
  - industry
  - business_data (JSON)
  - ai_trained (boolean)
  - generated_faqs (JSON)
  - ai_context (JSON)

products
  - id (PK)
  - business_id (FK)
  - name, description, price
  - availability

conversations
  - conversation_id (PK)
  - business_id (FK)
  - customer_id
  - conversation_stage

conversation_messages
  - id (PK)
  - conversation_id (FK)
  - role (customer/ai)
  - message
  - metadata (JSON)

token_usage
  - id (PK)
  - business_id (FK)
  - prompt_tokens, completion_tokens
  - cost_usd
```

### Business Owner AI Database

```sql
business_profiles
  - business_id (PK)
  - financial_data (JSON)
  - operational_metrics (JSON)
  - market_data (JSON)

analyses
  - id (PK)
  - business_id (FK)
  - analysis_type
  - results (JSON)
  - recommendations (JSON)

strategic_plans
  - id (PK)
  - business_id (FK)
  - goals, swot_analysis
  - action_plan (JSON)
```

## Security Architecture

### Authentication
- API key-based authentication
- Business-specific access control
- Rate limiting per business

### Data Protection
- Business data isolation
- Encrypted data transmission
- GDPR/CCPA compliance
- Industry-specific compliance (HIPAA, SOX, etc.)

### Budget Control
- Token usage tracking
- Monthly budget limits
- Automatic fallback responses
- Cost optimization

## Integration Points

### Customer AI Integrations
- Google Maps API (location services)
- Google Calendar API (appointment booking)
- Google Cloud Vision API (OCR processing)
- OpenAI API (conversational AI)

### Business Owner AI Integrations (Planned)
- QuickBooks/Xero (financial data)
- Salesforce/HubSpot (CRM data)
- Google Analytics (web analytics)
- Industry-specific data sources
- Invoice Generator API (for invoice retrieval/search)

### Invoice Generator Integrations
- Backend Systems (automatic invoice generation)
- Database Storage (invoice persistence)
- Email/SMS Services (invoice delivery)
- Business Owner AI (for invoice retrieval queries)

## Performance Targets

### Customer AI
- Response Time: <2 seconds
- Availability: 99.9%
- Accuracy: 95%+
- Concurrent Users: 10,000+ per industry

### Business Owner AI
- Analysis Time: <20 seconds
- Availability: 99.9%
- Insight Accuracy: 90%+
- Concurrent Analyses: 1,000+ per industry

### Invoice Generator
- Generation Time: <1 second
- Availability: 99.9%
- Accuracy: 100% (deterministic)
- Concurrent Generations: 10,000+ per hour

## Deployment Architecture

### Development
```
Local Development
├── SQLite database
├── Mock integrations
└── Debug logging
```

### Production
```
Google Cloud Platform
├── Cloud SQL (PostgreSQL)
├── Cloud Run (containerized apps)
├── Cloud Storage (documents)
├── Load Balancer
└── Monitoring & Logging
```


## Scalability

### Horizontal Scaling
- Stateless API design enables multiple instances
- Database connection pooling
- Caching layer (Redis)
- Load balancing

### Vertical Scaling
- Optimized prompts reduce token usage
- Efficient database queries
- Minimal memory footprint
- Fast response generation

## Future Enhancements

### Customer AI
- Multi-language support
- Voice integration
- Advanced analytics dashboard
- CRM integration

### Business Owner AI
- Predictive analytics
- Automated reporting
- Industry benchmarking
- Partnership recommendations

## Contributing

1. Review documentation in `docs/` folder
2. Follow code organization patterns
3. Maintain separation between Customer AI and Business Owner AI
4. Ensure all 15 industries are equally supported
5. Write tests for new features


