# ndara.ai Customer AI - Production Deployment Guide


## Prerequisites

### System Requirements
- Python 3.11.4+ or 3.12+ (for PEP 706 pip tar/symlink fix; see [SECURITY.md](../SECURITY.md))
- 4GB+ RAM (8GB+ recommended)
- PostgreSQL 12+ with pgvector extension (recommended for production)
- Network access to OpenAI API

### Required Services
- OpenAI API account with API key
- PostgreSQL database (same as backend, recommended) or ChromaDB for local development
- (Optional) Appointment booking service URL

---

## Environment Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd customer_ai
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip   # Required for pip tar/symlink fix (see SECURITY.md)
pip install -r requirements.txt
```

---

## Configuration

### 1. Environment Variables

Copy the example environment file and configure it:
```bash
cp ENV_TEMPLATE.txt .env
```

Edit `.env` with your production values:

#### Required Variables
```bash
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-...

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

#### Optional Variables
```bash
# Vector Database (REQUIRED: pgvector for production)
VECTOR_STORAGE_MODE=pgvector  # ⚠️ MUST be 'pgvector' for production. 'local' (ChromaDB) is for development only and will cause issues in production.

# PostgreSQL Configuration (required if VECTOR_STORAGE_MODE=pgvector)
# pgvector typically runs on port 5433 (main PostgreSQL often uses 5432)
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5433
POSTGRES_DB=your-database-name
POSTGRES_USER=your-database-user
POSTGRES_PASSWORD=your_postgres_password

# ChromaDB (only for local development mode)
CHROMA_PERSIST_DIR=./chroma_db

# External Services
APPOINTMENT_BOOKING_URL=https://your-appointment-service.com
CUSTOMER_AI_URL=https://your-customer-ai-service.com

# Logging
LOG_LEVEL=INFO
```

### 2. Verify Configuration
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

---

## Running the Service

### Development Mode
```bash
python main.py
```

The service will start on `http://0.0.0.0:8000`

### Production Mode with Uvicorn
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Production Mode with Gunicorn (Recommended)
Use Gunicorn **23.0.0 or later** (CVE-2024-1135, CVE-2024-6827: request smuggling fixes).
```bash
# Install gunicorn (>=23.0.0)
pip install "gunicorn>=23.0.0"

# Run with gunicorn
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

### Using Systemd (Linux)
Create `/etc/systemd/system/customer-ai.service`:
```ini
[Unit]
Description=ndara.ai Customer AI Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/customer_ai
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable customer-ai
sudo systemctl start customer-ai
sudo systemctl status customer-ai
```

### Using Docker (Optional)
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

Build and run:
```bash
docker build -t customer-ai .
docker run -p 8000:8000 --env-file .env customer-ai
```

---

## Production Considerations

### 1. Vector Database
- **Development**: Use local ChromaDB (set `VECTOR_STORAGE_MODE=local`)
- **Production**: Use PostgreSQL with pgvector extension (recommended)
  - Set `VECTOR_STORAGE_MODE=pgvector`
  - Configure PostgreSQL connection settings (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`)
  - Ensure pgvector extension is installed: `CREATE EXTENSION IF NOT EXISTS vector;`
  - Benefits: Same database as backend, ACID compliance, better persistence, easier backups

### 2. Security
- **Never commit `.env` file** to version control
- Use environment-specific `.env` files (`.env.production`)
- **API Authentication**: The Customer AI API does NOT implement its own authentication or rate limiting. The backend/API gateway that sits in front of this service **must** enforce authentication (e.g. API keys, JWT) and request rate limiting before traffic reaches the inference API. Never expose the Customer AI service directly to the public internet without a gateway.
- Configure CORS properly (don't use `*` in production)
- Use HTTPS in production
- Set up firewall rules

### 3. Performance
- Use multiple workers (4-8 workers recommended)
- Monitor memory usage (pgvector uses PostgreSQL connection pooling)
- Consider using Redis for caching (future enhancement)
- Set appropriate timeouts
- For pgvector: Monitor PostgreSQL connection pool usage

### 4. Persistence & In-Memory State

**IMPORTANT**: All runtime state — onboarded business AI instances, compiled LangGraph agent graphs, and conversation managers — is held in Python process memory. A server restart or worker recycle **wipes all active state** and requires businesses to re-onboard via `POST /api/v1/onboard`. For production environments with multiple workers or rolling deployments:
- Trigger re-onboarding automatically from the backend after each deployment
- Or move onboarding state to an external store (Redis/PostgreSQL) in a future iteration

Vector / RAG data persistence:
- **ChromaDB (local mode)**: Data stored in `./chroma_db/` directory — ensure this directory is backed up regularly
- **pgvector (production)**: Data stored in PostgreSQL — use standard PostgreSQL backup tools
  - pg_dump for full backups
  - Point-in-time recovery (PITR) for continuous backups
  - Replication for high availability

### 5. Logging
- Configure log rotation
- Use structured logging for production
- Monitor error logs regularly
- Set appropriate log levels (`INFO` for production)

### 6. Health Monitoring
- The service exposes `/docs` for API documentation
- Monitor `/health` endpoint (if implemented)
- Set up health checks in your load balancer
- Monitor OpenAI API usage and rate limits

---

## Monitoring & Health Checks

### API Documentation
Access API documentation at: `http://your-server:8000/docs`

### Health Check Endpoint
```bash
curl http://your-server:8000/health
```

### Check Service Status
```bash
# If using systemd
sudo systemctl status customer-ai

# Check logs
sudo journalctl -u customer-ai -f
```

### Monitor Resource Usage
```bash
# CPU and Memory
top -p $(pgrep -f "gunicorn.*customer-ai")

# Disk usage
# For ChromaDB (local mode):
du -sh ./chroma_db/

# For pgvector (production):
# Check PostgreSQL database size
psql -U postgres -d customer_ai -c "SELECT pg_size_pretty(pg_database_size('customer_ai'));"
```

---

## Troubleshooting

### Common Issues

#### 1. "Business AI not found" Error
**Problem**: Business AI instance not found after server restart
**Solution**: Re-onboard the business using `/api/v1/onboard` endpoint

#### 2. OpenAI API Errors
**Problem**: Rate limits or authentication errors
**Solution**: 
- Check `OPENAI_API_KEY` is set correctly
- Monitor API usage and rate limits
- Implement retry logic if needed

#### 3. Vector Database Connection Errors
**Problem**: Connection errors with pgvector or ChromaDB
**Solution**: 
- For pgvector: Check PostgreSQL connection settings and ensure pgvector extension is installed
- For ChromaDB: Check disk space and file permissions for `./chroma_db/` directory
- Verify `VECTOR_STORAGE_MODE` environment variable is set correctly

#### 3a. ChromaDB Being Used in Production (CRITICAL)
**Problem**: Logs show "Chroma vector store initialized successfully" in production/staging, causing:
- Worker timeouts and memory issues
- "no such column: collections.topic" errors
- Poor performance and instability

**Symptoms**:
- Logs contain: `"Chroma vector store initialized successfully"`
- Logs contain: `"chromadb.telemetry.product.posthog - ERROR"`
- Worker timeouts: `[CRITICAL] WORKER TIMEOUT`
- Collection errors: `"no such column: collections.topic"`

**Root Cause**: `VECTOR_STORAGE_MODE` is set to `'local'` or not set at all in production environment.

**Solution**:
1. **Check environment variables**: Ensure `VECTOR_STORAGE_MODE=pgvector` is set in your production environment
2. **Check Docker/container config**: If using Docker, verify environment variables in `docker-compose.yml` or deployment config
3. **Check .env file**: Ensure `.env` file in production has `VECTOR_STORAGE_MODE=pgvector` (not `local`)
4. **Restart application**: After fixing, restart the application to load new configuration
5. **Verify**: Check logs for `"pgvector initialized successfully"` instead of ChromaDB messages

**Prevention**: The application now logs a warning when ChromaDB is used in production-like environments. Always set `VECTOR_STORAGE_MODE=pgvector` for production deployments.

#### 4. Memory Issues
**Problem**: High memory usage
**Solution**:
- Reduce number of workers
- Use pgvector for production (better resource management)
- Monitor PostgreSQL connection pool usage
- Monitor and limit concurrent requests

#### 5. Port Already in Use
**Problem**: Port 8000 already in use
**Solution**: Change `API_PORT` in `.env` file

### Logs Location
- Application logs: Check stdout/stderr or systemd journal
- Error logs: Check application logs for detailed error messages

### Getting Help
- Check API documentation at `/docs`
- Review error logs for detailed error messages
- Ensure all environment variables are set correctly

---

## API Endpoints

### Onboard Business
```bash
POST /api/v1/onboard?business_id=1
Content-Type: application/json
X-API-Key: your_api_key (if configured)

{
  "business_info": {...},
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
  "message": "Hello, what products do you have?",
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

---

## Support

For issues or questions, contact the development team or check the project documentation.

---

**Last Updated**: February 2026
**Version**: 3.1.0

