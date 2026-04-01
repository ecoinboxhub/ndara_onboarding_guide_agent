# OpenAI Integration for Business Owner AI

## Overview

The Business Owner AI now integrates OpenAI to generate natural language responses for all business intelligence queries. Previously, the system only returned structured guidance without NLP processing. Now every query response is processed through OpenAI for intelligent, context-aware answers.

## Architecture

### Knowledge Base → Structured Data → OpenAI Processing → Natural Language Response

```
User Query
    ↓
Intent Classification
    ↓
Extract Data from Knowledge Base
    ↓
OpenAI NLP Processing
    ↓
Natural Language Response + Token Usage
```

## Implementation Details

### Components Created

1. **OpenAI Service** (`src/services/openai_service.py`)
   - Centralized OpenAI API integration
   - Specialized response generators for each query type
   - Token usage tracking
   - Error handling with fallback responses

2. **Integration Points** (`src/core/business_intelligence.py`)
   - All query handlers now call OpenAI service
   - Responses include `tokens_used` tracking
   - Fallback messages only used when OpenAI fails

### Query Handlers with OpenAI Integration

| Intent | Handler | OpenAI Method | Use Case |
|--------|---------|---------------|----------|
| Sales Analysis | `_handle_sales_query` | `generate_sales_analysis_response` | Analyze sales performance data |
| Customer Segmentation | `_handle_segmentation_query` | `generate_response` (custom) | Provide segment insights |
| Inventory | `_handle_inventory_query` | `generate_inventory_response` | Search/retrieve inventory |
| Invoice | `_handle_invoice_query` | `generate_invoice_response` | Find invoices by criteria |
| Appointment | `_handle_appointment_query` | `generate_appointment_response` | Retrieve/manage appointments |
| Broadcast | `_handle_broadcast_query` | `generate_response` (custom) | Prepare broadcast messages |
| General | `_handle_general_query` | `generate_general_response` | Handle unknown queries |

## API Response Format

All `/api/v1/chat` responses now include:

```json
{
  "success": true,
  "intent": "inventory_retrieval",
  "query": "Show me low stock items",
  "message": "<NLP-generated response from OpenAI>",
  "response": "<NLP-generated response from OpenAI>",
  "parsed_query": {...},
  "search_filters": {...},
  "guidance": "...",
  "tokens_used": {
    "prompt_tokens": 45,
    "completion_tokens": 120,
    "total_tokens": 165
  }
}
```

## Configuration

### Environment Variables Required

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
```

### Default Values

- **Model**: `gpt-4o` (can be overridden with `OPENAI_MODEL`)
- **Temperature**: `0.7` (can be overridden with `OPENAI_TEMPERATURE`)
- **Max Tokens**: 500 (varies by query type, up to 500)

## Testing the Integration

### 1. Test Inventory Query

**Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat?business_id=test_biz&industry=retail" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me low stock items in the electronics category",
    "context": {
      "predict_demand": false
    }
  }'
```

**Expected Response**:
- `tokens_used` should show non-zero token consumption
- `response` should be natural language (not just guidance)
- No "fallback" indicator

### 2. Test Sales Query

**Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat?business_id=test_biz&industry=retail" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How are my sales performing?",
    "context": {
      "conversations": [],
      "sales_data": [
        {"date": "2025-01-15", "amount": 5000, "items": 10},
        {"date": "2025-01-16", "amount": 7500, "items": 15}
      ]
    }
  }'
```

**Expected Response**:
- `tokens_used` should show token consumption
- `response` should include sales insights

### 3. Test General Query

**Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat?business_id=test_biz&industry=retail" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What can you help me with?"
  }'
```

**Expected Response**:
- Intelligent, context-aware response (not hardcoded)
- Should ask clarifying questions if needed
- Tokens consumed

## Logging

Enable debug logging to see OpenAI calls:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Log messages:
- `DEBUG`: API call details and prompt preview
- `INFO`: Token usage and response summaries
- `ERROR`: API failures and exceptions

Example logs:
```
DEBUG - Calling OpenAI API with model=gpt-4o, max_tokens=500
DEBUG - Prompt preview: The user asked: "Show me low stock items"...
INFO - OpenAI response received - Tokens used: 165
DEBUG - Response preview: Based on your query about low stock items...
```

## Token Usage Tracking

All responses include `tokens_used`:

```json
"tokens_used": {
  "prompt_tokens": 45,
  "completion_tokens": 120,
  "total_tokens": 165
}
```

- **prompt_tokens**: Tokens in the system message + user query
- **completion_tokens**: Tokens in OpenAI's response
- **total_tokens**: Sum of prompt + completion

Monitor this across your system to:
- Track API costs
- Optimize prompt lengths
- Identify expensive query patterns

## Error Handling

### When OpenAI Fails

If OpenAI API call fails:
1. Error is logged with full traceback
2. Fallback response is returned
3. Response includes `error` field
4. `tokens_used` is null

Example error response:
```json
{
  "success": false,
  "intent": "inventory_retrieval",
  "error": "API rate limit exceeded",
  "query": "..."
}
```

## Performance Characteristics

### Latency
- OpenAI API call: ~1-3 seconds typically
- Total response time: 1-4 seconds

### Token Efficiency
- Typical inventory query: 150-200 tokens
- Typical sales analysis: 200-300 tokens
- Typical general query: 100-150 tokens

## Upgrading Models

To use a different OpenAI model:

```bash
export OPENAI_MODEL=gpt-4-turbo
# or
export OPENAI_MODEL=gpt-3.5-turbo
```

Recommended models:
- `gpt-4o` (current default, best quality)
- `gpt-4-turbo` (cost-effective)
- `gpt-3.5-turbo` (budget option)

## Troubleshooting

### No Tokens Consumed

**Symptom**: `tokens_used` is null or 0, responses seem generic

**Cause**: OpenAI API key not set or invalid

**Solution**:
1. Verify `OPENAI_API_KEY` is set
2. Check logs for OpenAI connection errors
3. Test API key: `openai api models.list`

### Slow Responses

**Symptom**: Responses take >5 seconds

**Cause**: OpenAI API latency or network issues

**Solution**:
1. Check OpenAI status page
2. Monitor network latency
3. Consider using faster model (`gpt-3.5-turbo`)

### Generic Responses

**Symptom**: Responses don't reflect business context

**Cause**: Insufficient context in request

**Solution**:
1. Provide more data in context (sales_data, customer_data, etc.)
2. Use specific queries
3. Check logs to see what data was passed to OpenAI

## Future Enhancements

- [ ] Response caching to reduce redundant API calls
- [ ] Streaming responses for long analyses
- [ ] Multi-language support
- [ ] Custom system prompts per industry
- [ ] Response quality metrics
- [ ] Token budget management per business

## References

- OpenAI API Documentation: https://platform.openai.com/docs/api-reference
- Chat Completions: https://platform.openai.com/docs/api-reference/chat/create
- Token Pricing: https://openai.com/api/pricing/
