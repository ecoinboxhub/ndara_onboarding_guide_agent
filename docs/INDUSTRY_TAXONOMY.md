# Industry Taxonomy - Customer AI

## Overview

The Customer AI system supports **15 canonical industries**. A single taxonomy ensures consistent industry identifiers across the classifier, prompts, AI engines, model registry, and documentation.

## Canonical Industries

| Key | Description |
|-----|-------------|
| `ecommerce` | Online stores, retail, product sales |
| `healthcare` | Clinics, hospitals, medical practices |
| `real_estate` | Property sales, rentals, agents |
| `restaurants` | Dining, cafes, food service |
| `education` | Schools, courses, training |
| `financial` | Financial services, loans, insurance |
| `travel` | Hotels, tourism, travel agencies |
| `events` | Event planning, venues, entertainment |
| `logistics` | Shipping, delivery, supply chain |
| `professional_services` | Consulting, legal, accounting |
| `beauty_wellness` | Salons, spas, fitness |
| `telecoms` | Telecommunications, internet, mobile |
| `banking` | Banks, credit unions |
| `manufacturing` | Production, factories, industrial |
| `retail_chains` | Franchises, multi-location retail |

## Alias Mapping

The following aliases resolve to canonical keys. Use these when integrating with external systems or documentation.

| Alias | Canonical |
|-------|-----------|
| `ecommerce_retail` | `ecommerce` |
| `travel_hospitality` | `travel` |
| `events_entertainment` | `events` |
| `logistics_delivery` | `logistics` |
| `manufacturing_fmcg` | `manufacturing` |
| `enterprise_banking` | `banking` |
| `enterprise_telecoms` | `telecoms` |
| `restaurant` | `restaurants` |
| `financial_services` | `financial` |
| `finance` | `financial` |

## Niche Playbooks Mapping

The voice agent playbooks in `docs/voice/niche_playbooks/` use the following filenames. Map them to canonical keys as shown:

| Playbook File | Canonical Key |
|---------------|---------------|
| `ecommerce_retail.md` | `ecommerce` |
| `healthcare.md` | `healthcare` |
| `real_estate.md` | `real_estate` |
| `restaurant.md` | `restaurants` |
| `education.md` | `education` |
| `finance.md` | `financial` |
| `travel_hospitality.md` | `travel` |
| `events_entertainment.md` | `events` |
| `logistics_delivery.md` | `logistics` |
| `professional_services.md` | `professional_services` |
| `beauty_wellness.md` | `beauty_wellness` |
| `enterprise_telecoms.md` | `telecoms` |
| `enterprise_banking.md` | `banking` |
| `manufacturing_fmcg.md` | `manufacturing` |
| `retail_chains.md` | `retail_chains` |

## Usage in Code

```python
from src.domain.industries.taxonomy import (
    resolve_industry,   # Returns canonical or None
    normalize_industry, # Returns canonical or "general"
    is_valid_industry,
    get_all_industries,
)

# Resolve alias to canonical
resolve_industry("travel_hospitality")  # -> "travel"

# Normalize with fallback (for required industry)
normalize_industry("unknown")  # -> "general"

# Check validity
is_valid_industry("ecommerce")  # -> True
```

## Escalation and Compliance

Per-industry escalation triggers and compliance are defined in `customer_ai/src/domain/industries/config.py`:

- **INDUSTRY_ESCALATION_TRIGGERS** – keywords per severity (critical, high, medium)
- **INDUSTRY_ESCALATION_RECOMMENDATIONS** – recommended actions for human handoff
- **INDUSTRY_COMPLIANCE** – compliance flags (e.g., HIPAA for healthcare, audit for finance)

See [BUSINESS_LOGIC.md](../customer_ai/BUSINESS_LOGIC.md) for escalation flow and [customer_ai_api.md](api/customer_ai_api.md) for the `POST /api/v1/escalate` endpoint.

## Fallback

When an industry cannot be resolved, the system uses `general`, which maps to `GenericAIEngine` and default prompts.
