# AI-PROJECT: Dual AI Platform for Business Intelligence

## Overview

A comprehensive AI platform featuring four core systems:
- **Customer AI**: Business-specific AI for serving end customers
- **Business Owner AI**: Strategic intelligence AI for business optimization
- **Invoice Generator**: Automatic invoice generation for products and services
- **Inventory Management**: Automatic inventory operations for products and services

## Core Concept

### Business-Specific AI Architecture
Each business owner gets their own personalized AI trained exclusively on their business data. The AI only answers questions about that specific business - no general information.

**Example:**
- Dr. Smith's Clinic AI → Only knows Dr. Smith's services, doctors, prices
- Mario's Restaurant AI → Only knows Mario's menu, hours, location
- ABC Real Estate AI → Only knows ABC's property listings, agents

### Two Distinct Systems

| Aspect | Customer AI | Business Owner AI |
|--------|-------------|-------------------|
| **User** | End customers | Business owners |
| **Purpose** | Sales, support, bookings | Strategy, analytics, optimization |
| **Conversations** | Short, transactional | Long, analytical |
| **Data Input** | Business info, products, services | Financial metrics, operational data |
| **Output** | Customer responses, bookings | Strategic insights, business intelligence |

## Supported Industries

All 15+ industries with equal emphasis:

1. E-commerce & Retail
2. Healthcare
3. Real Estate
4. Restaurants & Food
5. Education
6. Financial Services
7. Travel & Hospitality
8. Events & Entertainment
9. Logistics & Delivery
10. Professional Services
11. Beauty & Wellness
12. Enterprise Telecoms
13. Enterprise Banking
14. Manufacturing & FMCG
15. Retail Chains

## Key Features

### Minimal Data Approach
- Business owners provide only: name, industry, products/services, contact info
- AI auto-generates: FAQs, customer personas, conversation strategies, industry context

### Industry-Specific Intelligence
- Each industry has dedicated AI engines
- Industry-specific personalities and expertise
- Tailored conversation flows and responses

### Production Ready
- FastAPI REST APIs
- SQLAlchemy database integration
- Google Cloud integrations (Maps, Calendar, OCR)
- Security middleware and authentication
- Budget optimization and token tracking

## Quick Start

### Customer AI
```bash
cd customer_ai
pip install -r requirements.txt
python main.py
```

## Documentation

- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Customer AI API**: See [api/customer_ai_api.md](api/customer_ai_api.md)
- **Business Owner AI API**: See [api/business_owner_ai_api.md](api/business_owner_ai_api.md)
- **Integration Guide**: See [api/integration_guide.md](api/integration_guide.md)

## Technology Stack

- **AI/ML**: OpenAI GPT-3.5-turbo/GPT-4
- **Backend**: FastAPI, Python 3.8+
- **Database**: PostgreSQL/SQLite with SQLAlchemy
- **Cloud**: Google Cloud Platform (Maps, Calendar, Vision APIs)





## Support

For questions and support:
- Review documentation in `docs/` folder
- Check API guides for integration
- See development guides for contributing

