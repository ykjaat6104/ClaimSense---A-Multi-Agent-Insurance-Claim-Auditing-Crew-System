# Production Configuration Guide

## Quick Start

### 1. Generate Secrets
```bash
# Generate auth secret
python -c "import secrets; print('CLAIMSENSE_AUTH_SECRET=' + secrets.token_urlsafe(32))"

# Generate database password
python -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(16))"

# Generate demo password
python -c "import secrets; print('CLAIMSENSE_DEMO_PASSWORD=' + secrets.token_urlsafe(12))"
```

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Database Setup
```bash
# Ensure PostgreSQL is running
docker-compose up -d db

# Wait for database to be ready
docker-compose exec db pg_isready -U postgres
```

### 4. Start the Application
```bash
docker-compose up -d

# Verify all services are healthy
docker-compose ps
```

### 5. Test the API
```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"adjuster","password":"YOUR_PASSWORD_HERE"}'
```

## Environment-Specific Configuration

### Development
```bash
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/claimsense
```

### Staging
```bash
ENVIRONMENT=staging
CORS_ORIGINS=https://staging.app.example.com
DATABASE_URL=postgresql+psycopg2://claimsense:PASSWORD@staging-db.example.com:5432/claimsense
```

### Production
```bash
ENVIRONMENT=production
CORS_ORIGINS=https://app.example.com
DATABASE_URL=postgresql+psycopg2://claimsense:PASSWORD@prod-db.example.com:5432/claimsense
```

## Security Configuration

### 1. Authentication Secret
- **Minimum Length**: 32 characters
- **Rotation**: Every 90 days in production
- **Storage**: Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)

### 2. CORS Origins
Always specify exact origins in production:
```bash
# Good
CORS_ORIGINS=https://app.example.com,https://admin.example.com

# Bad (allows all)
CORS_ORIGINS=*
```

### 3. Database Security
- Use strong passwords (16+ characters)
- Enable SSL connections to database
- Restrict database access to application servers only
- Regular backups with encryption

### 4. API Keys
- Keep Gemini API key secure
- Use separate keys for development/production
- Rotate keys regularly
- Monitor API usage for anomalies

## Performance Tuning

### Database Connection Pool
```python
# In app/db/session.py
create_engine(
    database_url,
    pool_size=20,  # Maximum 20 connections
    max_overflow=10,  # Allow up to 10 overflow connections
    pool_pre_ping=True,  # Test connections before use
    pool_recycle=3600,  # Recycle connections every hour
)
```

### Gunicorn Configuration (for production)
```bash
# Instead of uvicorn, use gunicorn with multiple workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  app.main:app
```

### Nginx Load Balancing
```nginx
upstream claimsense_api {
    least_conn;
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name app.example.com;
    
    location /api {
        proxy_pass http://claimsense_api;
        proxy_connect_timeout 5s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    location / {
        proxy_pass http://claimsense_api;
        # Serve SPA
    }
}
```

## Monitoring Setup

### Health Check Monitoring
```bash
# Continuous health monitoring
watch -n 30 'curl -s http://localhost:8000/health | jq .'
```

### Log Aggregation Example (ELK Stack)
```yaml
# docker-compose addition for logging
logstash:
  image: docker.elastic.co/logstash/logstash:8.0.0
  volumes:
    - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  environment:
    - xpack.monitoring.enabled=false
  ports:
    - "5000:5000"
```

### Metrics Export (Prometheus)
Add to `app/main.py`:
```python
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Instrument FastAPI
Instrumentator().instrument(app).expose(app)
```

## Backup & Disaster Recovery

### Daily Backup Script
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/claimsense"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec db pg_dump -U postgres claimsense | \
  gzip > $BACKUP_DIR/claimsense-$(date +%Y%m%d-%H%M%S).sql.gz

# Backup uploads
tar -czf $BACKUP_DIR/uploads-$(date +%Y%m%d).tar.gz ./uploads

# Backup reports
tar -czf $BACKUP_DIR/reports-$(date +%Y%m%d).tar.gz ./reports

# Clean old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Optional: Upload to S3
# aws s3 sync $BACKUP_DIR s3://my-backups/claimsense/
```

### Restore from Backup
```bash
# Restore database
gunzip < backup.sql.gz | docker-compose exec db psql -U postgres claimsense

# Restore uploads
tar -xzf uploads-backup.tar.gz

# Restore reports
tar -xzf reports-backup.tar.gz
```

## SSL/TLS Configuration

### Let's Encrypt with Certbot
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d app.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Self-Signed Certificate (Testing Only)
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Database Optimization

### Connection Pool Tuning
```python
# app/db/session.py
pool_size = 20  # Adjust based on load
max_overflow = 10  # Allow temporary overflow
pool_pre_ping = True  # Verify connections
pool_recycle = 3600  # Recycle connections hourly
```

### Query Optimization
- Add database indexes on frequently queried columns
- Use connection pooling
- Monitor slow queries
- Use EXPLAIN ANALYZE for query optimization

## Rate Limiting Configuration

### Adjust Rate Limits
Edit `app/middleware/rate_limit.py`:
```python
RATE_LIMITS = {
    "auth": "10/minute",  # Brute force protection
    "upload": "20/hour",  # File upload limit
    "process": "30/hour",  # Processing limit
    "default": "100/minute",  # Default rate
}
```

## Secrets Management

### Using AWS Secrets Manager
```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In config.py
if settings.is_production():
    secrets = get_secret('claimsense/production')
    settings.claimsense_auth_secret = secrets['auth_secret']
```

### Using HashiCorp Vault
```python
import hvac

vault_client = hvac.Client(url='https://vault.example.com')
vault_client.auth.approle.login(role_id='...', secret_id='...')
secrets = vault_client.secrets.kv.read_secret_version(path='claimsense/prod')
```

## Checklist for Production Deployment

- [ ] All secrets configured via environment variables
- [ ] Database credentials changed from defaults
- [ ] CORS origins restricted to your domain(s)
- [ ] HTTPS/SSL configured
- [ ] Database backups automated and tested
- [ ] Monitoring and alerting configured
- [ ] Log aggregation set up
- [ ] Database connection pool optimized
- [ ] Rate limiting configured appropriately
- [ ] Healthchecks monitored
- [ ] API documentation available (or disabled)
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Regular security updates planned
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Performance benchmarks recorded

## Support

For issues or questions, refer to:
- `DEPLOYMENT.md` - Deployment guide
- `README.md` - Project overview
- API docs - `/api/docs` (when available)
