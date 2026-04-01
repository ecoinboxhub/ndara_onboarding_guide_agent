# Business Owner AI - API Reference

## Overview

The Business Owner AI API provides business intelligence, analytics, and strategic insights for business owners. It enables sales analysis, customer segmentation, inventory predictions, and competitive intelligence.

**Base URL (Development)**: `http://localhost:8001`  
**Base URL (Production)**: `https://api.ndara.ai/business-owner-ai`  
**API Version**: `v1`  
**Authentication**: API Key + Business Owner Token

---

## Authentication

Requires both API key and business owner authentication token:

```http
X-API-Key: your_api_key
Authorization: Bearer business_owner_token
```

---

## Endpoints

### 1. Chat (General Business Intelligence)

**POST** `/api/v1/chat?business_id={business_id}&industry={industry}`

Ask natural language questions about your business.

**Request:**
```json
{
  "query": "How are my sales performing this month?",
  "context": {
    "time_period": "last_30_days",
    "include_recommendations": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "intent": "sales_analysis",
  "analysis": {
    "key_metrics": {
      "total_revenue": 2500000,
      "total_transactions": 145,
      "avg_order_value": 17241.38,
      "growth_rate": 0.15
    },
    "insights": [
      "Revenue increased by 15% compared to last month",
      "Average order value improved by ₦2,500",
      "Weekend sales show strongest performance"
    ],
    "recommendations": [
      "Focus marketing on weekends for maximum impact",
      "Consider premium product promotion to increase AOV",
      "Monitor inventory for best-selling items"
    ]
  }
}
```

---

### 2. Analyze Sales Performance

**POST** `/api/v1/analyze-sales?business_id={business_id}`

Comprehensive sales performance analysis.

**Request:**
```json
{
  "conversations": [
    {
      "conversation_id": "conv_001",
      "messages": [...],
      "created_at": "2025-10-01T10:00:00Z"
    }
  ],
  "sales_data": [
    {
      "transaction_id": "txn_001",
      "date": "2025-10-05",
      "amount": 15000,
      "items": [
        {"name": "Product A", "quantity": 2, "price": 7500}
      ]
    }
  ],
  "time_period": "last_30_days"
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "key_metrics": {
      "total_revenue": 2500000,
      "total_transactions": 145,
      "avg_order_value": 17241.38,
      "conversion_rate": 0.23,
      "customer_satisfaction_score": 4.3
    },
    "conversation_insights": {
      "total_conversations": 630,
      "top_intents": [
        ["product_inquiry", 245],
        ["pricing_inquiry", 120],
        ["booking", 95]
      ],
      "sentiment_distribution": {
        "positive": 0.68,
        "neutral": 0.24,
        "negative": 0.08
      },
      "complaint_rate": 0.08,
      "purchase_intent_rate": 0.39
    },
    "sales_insights": {
      "top_products_by_revenue": [
        ["Premium Package", 850000],
        ["Standard Package", 620000]
      ],
      "top_products_by_volume": [
        ["Basic Service", 85],
        ["Consultation", 45]
      ]
    },
    "trends": {
      "conversation_volume_trend": "increasing",
      "sentiment_trend": "improving",
      "sales_trend": "increasing"
    },
    "insights": [
      "⚠️ High complaint rate (8%). Consider investigating common issues.",
      "📈 Strong purchase intent (39%). Good opportunity for conversion optimization.",
      "💰 Average order value: ₦17,241. Consider upselling strategies.",
      "⭐ Best performer: Premium Package. Consider promoting similar products."
    ],
    "recommendations": [
      "1. Conduct customer feedback survey to identify pain points",
      "2. Implement automated responses for common queries",
      "3. Monitor top-performing products and ensure adequate stock",
      "4. Analyze customer feedback to improve products/services",
      "5. Implement loyalty program for repeat customers"
    ]
  }
}
```

---

### 3. Segment Customers

**POST** `/api/v1/segment-customers?business_id={business_id}`

ML-based customer segmentation.

**Request:**
```json
{
  "customer_data": [
    {
      "customer_id": "cust_001",
      "total_spent": 125000,
      "purchase_count": 8,
      "conversation_count": 12,
      "days_since_last_purchase": 5,
      "days_since_last_activity": 2,
      "purchased_products": ["Product A", "Product B"],
      "interested_categories": ["electronics", "accessories"]
    }
  ],
  "method": "rfm"
}
```

**Method Options:**
- `behavior`: Segment by purchase behavior
- `value`: Segment by customer lifetime value
- `engagement`: Segment by engagement level
- `rfm`: RFM (Recency, Frequency, Monetary) analysis

**Response:**
```json
{
  "success": true,
  "segmentation": {
    "segments": {
      "champions": ["cust_001", "cust_045"],
      "loyal_customers": ["cust_023", "cust_067"],
      "potential_loyalists": ["cust_012"],
      "at_risk": ["cust_034"],
      "hibernating": ["cust_089"],
      "lost": ["cust_091"]
    },
    "segment_profiles": {
      "champions": {
        "count": 25,
        "total_value": 3500000,
        "avg_value": 140000,
        "revenue_contribution": 0.28,
        "priority": "retain",
        "characteristics": "High recency, frequency, and monetary value"
      }
    },
    "recommendations": {
      "champions": "Reward, request reviews/referrals, exclusive previews",
      "at_risk": "Personalized outreach, special discounts, feedback surveys"
    },
    "total_customers": 250,
    "segmentation_method": "rfm"
  }
}
```

---

### 4. Invoice & Inventory Retrieval (via Chat Endpoint)

**POST** `/api/v1/chat?business_id={business_id}&industry={industry}`

The main chat endpoint handles all business intelligence queries, including **invoice retrieval** and **inventory retrieval** using natural language. Invoice generation and inventory management operations are handled automatically by backend services.

**Note**: 
- Invoice generation: Handled by backend Invoice Generator service (Port 8004)
- Inventory management: Handled by backend Inventory Management service (Port 8005)
- Business Owner AI only provides AI-powered search and retrieval through this chat endpoint

#### Invoice Retrieval Examples

**Request:**
```json
{
  "query": "Show me unpaid invoices from last month",
  "context": {}
}
```

**Example Invoice Queries:**
- "Show me unpaid invoices from last month"
- "Find invoice INV-20250101-1234"
- "What invoices are overdue?"
- "Show all invoices for customer John Doe"
- "List top 10 highest invoices this month"

**Response:**
```json
{
  "success": true,
  "intent": "invoice_retrieval",
  "parsed_query": {
    "action": "list",
    "filters": {
      "payment_status": "pending",
      "date_range": "last_30_days"
    },
    "sort_by": "date_desc",
    "limit": null
  },
  "search_filters": {
    "payment_status": "pending",
    "date_range": "last_30_days"
  },
  "guidance": "Retrieve invoices with payment status: PENDING created in the last 30 days. sorted by date (newest first).",
  "message": "I'll help you list invoices. Retrieve invoices with payment_status: PENDING created in the last 30 days. sorted by date (newest first).",
  "query": "Show me unpaid invoices from last month"
}
```

#### Inventory Retrieval Examples

**Request:**
```json
{
  "query": "Show me low stock items",
  "context": {
    "predict_demand": false
  }
}
```

**Example Inventory Queries (Product-based):**
- "Show me low stock items"
- "What products are out of stock?"
- "Find inventory for product ABC-123"
- "Show items that need reordering"

**Example Inventory Queries (Service-based):**
- "Show available staff slots for tomorrow"
- "What services are available this week?"
- "Find available rooms for booking"
- "Show staff availability for consultation"

**Response:**
```json
{
  "success": true,
  "intent": "inventory_retrieval",
  "parsed_query": {
    "action": "list",
    "filters": {
      "stock_level": "low"
    },
    "sort_by": null,
    "limit": null
  },
  "search_filters": {
    "stock_level": "low"
  },
  "guidance": "Retrieve inventory items with low stock (below reorder point).",
  "message": "I'll help you list inventory. Retrieve inventory items with low stock (below reorder point).",
  "query": "Show me low stock items"
}
```

**What to do with the response:**
1. Use `search_filters` to query your database (invoices or inventory)
2. Apply `sort_by` for ordering results
3. Apply `limit` if specified
4. Return matching results to the business owner

**Backend Integration Example:**
```python
# After getting search_filters from Business Owner AI chat endpoint
result = response.json()

if result['intent'] == 'invoice_retrieval':
    invoices = db.query_invoices(
        business_id=business_id,
        filters=result['search_filters'],
        sort_by=result['parsed_query']['sort_by'],
        limit=result['parsed_query']['limit']
    )
elif result['intent'] == 'inventory_retrieval':
    inventory_items = db.query_inventory(
        business_id=business_id,
        filters=result['search_filters'],
        sort_by=result['parsed_query']['sort_by'],
        limit=result['parsed_query']['limit']
    )
```

---

### 5. Prepare Broadcast Message

**POST** `/api/v1/prepare-broadcast?business_id={business_id}`

Prepare broadcast message for customer segments.

**Request:**
```json
{
  "message_intent": "promotion",
  "target_segment": "loyal_customers",
  "business_data": {
    "business_name": "My Business",
    "industry": "restaurants"
  },
  "personalization_data": {
    "customer_name": "John",
    "discount_percent": 15
  }
}
```

**Response:**
```json
{
  "success": true,
  "broadcast": {
    "primary_message": "Hi John! 🎉 Exclusive 15% off for our loyal customers...",
    "variants": [
      "Hey John! As a valued customer, enjoy 15% off...",
      "Special offer just for you, John! 15% discount..."
    ],
    "call_to_action": "Visit us today or order online!",
    "recommended_send_time": "2025-01-10T10:00:00Z",
    "personalization_placeholders": ["customer_name", "discount_percent"]
  }
}
```

---

### 6. Competitive Insights

**POST** `/api/v1/competitive-insights?business_id={business_id}&industry={industry}`

Generate competitive intelligence and market positioning analysis.

**Request:**
```json
{
  "business_data": {
    "business_name": "My Restaurant",
    "industry": "restaurants",
    "location": "Lagos, Nigeria",
    "target_market": "middle-class families",
    "key_offerings": ["Nigerian cuisine", "Fast delivery", "Affordable prices"]
  },
  "similar_businesses": [
    {
      "name": "Competitor A",
      "key_strengths": ["Large menu", "Premium location"],
      "pricing": "high"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "swot_analysis": {
      "strengths": ["Affordable pricing", "Fast delivery"],
      "weaknesses": ["Limited marketing reach", "Smaller menu"],
      "opportunities": ["Online ordering growth", "Delivery partnerships"],
      "threats": ["Competitor expansion", "Rising ingredient costs"]
    },
    "market_trends": [
      "Growing demand for online ordering",
      "Increased focus on delivery speed",
      "Price sensitivity among target market"
    ],
    "competitive_advantages": [
      "Price competitive advantage",
      "Fast delivery differentiator",
      "Local market knowledge"
    ],
    "recommendations": [
      "1. Expand online presence and social media marketing",
      "2. Consider menu expansion for higher-value items",
      "3. Partner with delivery platforms for reach",
      "4. Leverage speed as key differentiator in marketing"
    ]
  }
}
```

---

## Error Handling

**POST** `/api/v1/prepare-broadcast?business_id={business_id}`

Compose engaging broadcast messages for customer segments.

**Request:**
```json
{
  "message_intent": "promotion",
  "target_segment": "frequent_buyers",
  "business_data": {
    "business_profile": {
      "business_name": "Tech Store Plus"
    }
  },
  "personalization_data": {
    "offer_details": "20% off all laptops",
    "validity": "This weekend only"
  }
}
```

**Message Intent Options:**
- `promotion`: Special offers and discounts
- `announcement`: Business updates
- `discount`: Discount alerts
- `new_product`: New arrivals
- `reminder`: Friendly reminders
- `appreciation`: Thank you messages

**Response:**
```json
{
  "success": true,
  "primary_message": "As one of our valued regulars, exciting news from Tech Store Plus! We have a special offer just for you. 20% off all laptops this weekend only!",
  "variants": [
    {
      "variant": "A",
      "message": "As one of our valued regulars, exciting news from Tech Store Plus! We have a special offer just for you. 20% off all laptops this weekend only!",
      "style": "standard"
    },
    {
      "variant": "B",
      "message": "As one of our valued regulars, exciting news from Tech Store Plus! We have a special offer just for you. 20% off all laptops this weekend only! Don't miss out!",
      "style": "urgent"
    },
    {
      "variant": "C",
      "message": "As one of our valued regulars, exciting news from Tech Store Plus. We have a special offer just for you. 20% off all laptops this weekend only.",
      "style": "calm"
    }
  ],
  "call_to_action": "Shop Now",
  "recommended_send_time": "Weekday mornings 10AM-12PM for best engagement",
  "estimated_reach": {
    "estimated_recipients": 0,
    "expected_open_rate": 0.65,
    "expected_click_rate": 0.15
  }
}
```

---

### 6. Predict Inventory

**POST** `/api/v1/predict-inventory?business_id={business_id}`

Natural language inventory queries and demand prediction.

**Request:**
```json
{
  "query": "Show me low stock items under 10000 naira",
  "predict_demand": true,
  "conversations": [
    {
      "conversation_id": "conv_001",
      "messages": [...]
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "parsed_query": {
    "query_type": "list",
    "filters": {
      "stock_level": "low",
      "price_max": 10000
    },
    "sort_by": "name",
    "sort_order": "asc",
    "limit": 100
  },
  "sql_equivalent": "SELECT * FROM inventory WHERE stock_quantity < reorder_point AND price <= 10000 ORDER BY name ASC LIMIT 100",
  "explanation": "Query type: list\nFilters:\n  - stock_level: low\n  - price_max: 10000\nSort by: name (asc)\nLimit: 100 results",
  "demand_prediction": {
    "demand_predictions": [
      {
        "product": "Product A",
        "mention_count": 15,
        "demand_level": "high",
        "predicted_weekly_demand": 22.5
      }
    ],
    "restocking_recommendations": [
      {
        "product": "Product A",
        "action": "restock",
        "urgency": "high",
        "suggested_quantity": 90
      }
    ],
    "trends": {
      "overall_trend": "increasing",
      "top_category": "general",
      "seasonal_pattern": "analyzing"
    }
  }
}
```

---

### 7. Competitive Insights

**POST** `/api/v1/competitive-insights?business_id={business_id}&industry={industry}`

Strategic competitive intelligence and market positioning.

**Request:**
```json
{
  "business_data": {
    "business_profile": {
      "business_name": "My Restaurant",
      "industry": "restaurants"
    },
    "products_services": [
      {"name": "Jollof Rice", "price": 3000},
      {"name": "Fried Rice", "price": 3500}
    ]
  },
  "similar_businesses": [
    {
      "business_name": "Competitor A",
      "products_services": [
        {"name": "Jollof Rice", "price": 3500}
      ]
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "swot_analysis": {
      "strengths": [
        "Wide product/service range",
        "Competitive pricing"
      ],
      "weaknesses": [],
      "opportunities": [
        "Digital transformation and online presence",
        "Customer loyalty programs",
        "Strategic partnerships"
      ],
      "threats": []
    },
    "market_trends": [
      {
        "trend": "Digital Engagement",
        "description": "Increasing customer preference for digital interactions",
        "relevance": "high",
        "action": "Strengthen online presence and digital channels"
      }
    ],
    "competitive_advantages": [
      "Diverse product/service portfolio",
      "AI-powered customer service",
      "Fast response times"
    ],
    "recommendations": [
      {
        "priority": "high",
        "category": "differentiation",
        "recommendation": "Leverage AI-powered service as key differentiator",
        "expected_impact": "Attract tech-savvy customers and improve efficiency"
      }
    ],
    "industry": "restaurants"
  }
}
```

---

## Code Examples

### Python

```python
import requests

API_KEY = "your_api_key"
OWNER_TOKEN = "business_owner_token"
BASE_URL = "http://localhost:8001"

headers = {
    "X-API-Key": API_KEY,
    "Authorization": f"Bearer {OWNER_TOKEN}",
    "Content-Type": "application/json"
}

# Analyze Sales
response = requests.post(
    f"{BASE_URL}/api/v1/analyze-sales",
    params={"business_id": "biz_12345"},
    headers=headers,
    json={
        "conversations": conversations_data,
        "sales_data": sales_data,
        "time_period": "last_30_days"
    }
)

analysis = response.json()
print(f"Revenue: ₦{analysis['analysis']['key_metrics']['total_revenue']:,.2f}")
```

### JavaScript

```javascript
const axios = require('axios');

const headers = {
  'X-API-Key': 'your_api_key',
  'Authorization': 'Bearer business_owner_token',
  'Content-Type': 'application/json'
};

// Retrieve Invoices (AI-Powered Search)
async function retrieveInvoices(businessId, industry, query) {
  const response = await axios.post(
    `http://localhost:8001/api/v1/retrieve-invoices?business_id=${businessId}&industry=${industry}`,
    { query, context: {} },
    { headers }
  );
  
  return response.data;
}
```

---

## Best Practices

1. **Batch Requests**: Combine multiple analyses in single requests
2. **Cache Results**: Cache analysis results for 1-hour periods
3. **Async Processing**: Use webhooks for long-running analyses
4. **Data Quality**: Ensure complete conversation and sales data
5. **Regular Analysis**: Run weekly analyses for trends
6. **Action Items**: Implement top 3 recommendations
7. **Monitor Segments**: Re-segment customers monthly

---

**Version**: 1.0.0  
**Last Updated**: October 10, 2025

