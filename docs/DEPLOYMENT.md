# Deployment Guide

## Prerequisites

### System Requirements
- Python 3.10.12+, 3.11.4+, or 3.12+ (for PEP 706 pip tar/symlink fix; see [SECURITY.md](../SECURITY.md))
- PostgreSQL 12+ (production) or SQLite (development)
- 2GB RAM minimum, 4GB recommended
- Linux/Mac/Windows OS

### API Keys Required
- OpenAI API key (required)
- Google Maps API key (optional)
- Google Calendar API key (optional)
- Google Cloud Vision API key (optional for OCR)

## Local Development Setup

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd AI-PROJECT

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip   # Required for pip tar/symlink fix (see SECURITY.md)

# Customer AI
cd customer_ai
pip install -r requirements.txt

# Business Owner AI (when ready)
cd ../business_owner_ai
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create `.env` file in each system folder:

```bash
# Customer AI (.env)
OPENAI_API_KEY=your-openai-api-key
GOOGLE_MAPS_API_KEY=your-maps-key  # Optional
GOOGLE_CALENDAR_API_KEY=your-calendar-key  # Optional
GOOGLE_CLOUD_PROJECT_ID=your-project-id  # Optional
DATABASE_URL=sqlite:///customer_ai.db  # Development
LOG_LEVEL=INFO
```

### 4. Initialize Database

```bash
# Customer AI
cd customer_ai
python -c "from src.models.database_models import Base; from src.services.database_service import engine; Base.metadata.create_all(engine)"
```

### 5. Run Development Server

```bash
# Customer AI
python main.py

# Access at: http://localhost:5000
# API Docs at: http://localhost:5000/docs
```

## Production Deployment

### Option 1: Google Cloud Run (Recommended)

#### 1. Prepare Docker Container

```dockerfile
# Dockerfile (customer_ai/)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py", "--mode", "prod"]
```

#### 2. Build and Deploy

```bash
# Build container
docker build -t customer-ai:latest .

# Push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/customer-ai

# Deploy to Cloud Run
gcloud run deploy customer-ai \
  --image gcr.io/PROJECT_ID/customer-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your-key
```

### Option 2: Traditional VPS

#### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies (use 3.11+ for PEP 706; see SECURITY.md)
sudo apt install python3.11 python3-pip postgresql nginx -y

# Install supervisor for process management
sudo apt install supervisor -y
```

#### 2. Application Setup

```bash
# Clone and setup
git clone <repository-url>
cd AI-PROJECT/customer_ai
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Configure Supervisor

```ini
# /etc/supervisor/conf.d/customer-ai.conf
[program:customer-ai]
command=/path/to/venv/bin/python main.py --mode prod
directory=/path/to/AI-PROJECT/customer_ai
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/customer-ai.err.log
stdout_logfile=/var/log/customer-ai.out.log
environment=OPENAI_API_KEY="your-key"
```

#### 4. Configure Nginx

```nginx
# /etc/nginx/sites-available/customer-ai
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 3: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  customer-ai:
    build: ./customer_ai
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/customer_ai
    depends_on:
      - db

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=customer_ai
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Database Setup

### PostgreSQL (Production)

```bash
# Create database
createdb customer_ai_prod

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost:5432/customer_ai_prod

# Run migrations
python -c "from src.models.database_models import Base; from src.services.database_service import engine; Base.metadata.create_all(engine)"
```

### Backup Strategy

```bash
# Daily backup
pg_dump customer_ai_prod > backup_$(date +%Y%m%d).sql

# Automated backup with cron
0 2 * * * pg_dump customer_ai_prod > /backups/customer_ai_$(date +\%Y\%m\%d).sql
```

## Monitoring & Logging

### Application Logs

```python
# Logging configuration in main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### Health Checks

```bash
# Health endpoint
curl http://localhost:5000/api/health

# System status
curl http://localhost:5000/api/system/status
```

### Performance Monitoring

```bash
# Token usage monitoring
curl http://localhost:5000/api/budget/status

# Conversation analytics
curl http://localhost:5000/api/business/{business_id}/conversation/history
```

## Security Hardening

### 1. Environment Variables
- Never commit `.env` files
- Use secret management (Google Secret Manager, AWS Secrets Manager)
- Rotate API keys regularly

### 2. API Security
- Implement API key authentication
- Enable rate limiting
- Use HTTPS in production
- Input validation and sanitization

### 3. Database Security
- Use strong passwords
- Enable SSL connections
- Regular backups
- Restricted network access

## Troubleshooting

### Common Issues

**OpenAI API Errors**
```bash
# Check API key
echo $OPENAI_API_KEY

# Test API connectivity
python -c "from openai import OpenAI; print(OpenAI().models.list())"
```

**Database Connection Issues**
```bash
# Test database connection
python -c "from src.services.database_service import engine; print(engine.connect())"
```

**Import Errors**
```bash
# Verify Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Scaling Considerations

### Load Balancing
- Use Nginx or cloud load balancer
- Session affinity not required (stateless)
- Health check endpoint: `/api/health`

### Database Scaling
- Connection pooling (SQLAlchemy default)
- Read replicas for analytics
- Partitioning by business_id

### Caching
- Redis for session data
- Cache frequently accessed business data
- TTL: 5 minutes for business data


## Backup & Recovery

### Backup Strategy
- Daily automated database backups
- Weekly full system backups
- Retention: 30 days

### Recovery Procedures
```bash
# Restore database
psql customer_ai_prod < backup_20241008.sql

# Verify restoration
python -c "from src.services.database_service import get_database_service; print(get_database_service().get_all_businesses())"
```

## Update & Maintenance

### Zero-Downtime Deployment
1. Deploy new version to separate instance
2. Run health checks
3. Switch traffic to new instance
4. Monitor for issues
5. Keep old instance ready for rollback

### Rolling Updates
```bash
# Update code
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Run migrations if needed
python migrations.py

# Restart service
sudo supervisorctl restart customer-ai
```

## Monitoring Checklist

- [ ] Application health checks
- [ ] API response times
- [ ] Error rates
- [ ] Token usage
- [ ] Database performance
- [ ] Disk space
- [ ] Memory usage
- [ ] Network traffic

## Support & Maintenance

### Regular Tasks
- Weekly: Review logs and errors
- Monthly: Update dependencies
- Quarterly: Security audit
- Annually: Architecture review

### Emergency Contacts
- System errors: Check logs at `/var/log/`
- Database issues: Contact DBA
- API issues: Check OpenAI status
- Cloud issues: Check GCP status

