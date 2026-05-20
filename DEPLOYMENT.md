# ClaimSense Production Deployment Guide

## Overview

ClaimSense is a production-ready FastAPI application with React frontend for AI-assisted insurance claim evaluation. This guide covers everything needed to deploy to production.

## Architecture

- **Backend**: FastAPI + Python 3.12
- **Frontend**: React 18 + TypeScript + Vite
- **Database**: PostgreSQL 16
- **Authentication**: JWT-based bearer tokens
- **Rate Limiting**: Slowapi (token bucket)
- **Containerization**: Docker + Docker Compose

## Pre-Deployment Checklist

### Security

- [ ] Set strong `CLAIMSENSE_AUTH_SECRET` (minimum 32 characters)
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] Set strong demo password or replace with database auth
- [ ] Configure CORS origins for your domain
- [ ] Set `ENVIRONMENT=production`
- [ ] Obtain Gemini API key from https://aistudio.google.com/apikey
- [ ] Use HTTPS only in production
- [ ] Configure firewall rules
- [ ] Set up SSL certificates (Let's Encrypt recommended)

### Infrastructure

- [ ] PostgreSQL 16+ server ready
- [ ] Docker and Docker Compose installed (v2.0+)
- [ ] Sufficient disk space for uploads and reports
- [ ] Backup strategy for PostgreSQL data
- [ ] Monitoring and alerting configured

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ClaimSense
   ```

2. **Create .env file from template**
   ```bash
   cp .env.example .env
   ```

3. **Edit .env with production values**
   ```bash
   nano .env
   ```
   
   Key values to configure:
   - `ENVIRONMENT=production`
   - `DATABASE_URL` - PostgreSQL connection string
   - `CLAIMSENSE_AUTH_SECRET` - Strong secret key
   - `CLAIMSENSE_DEMO_PASSWORD` - Strong password
   - `GEMINI_API_KEY` - Your Gemini API key
   - `CORS_ORIGINS` - Your frontend domain(s)

## Deployment Methods

### Method 1: Docker Compose (Recommended for most deployments)

```bash
# Build and start all services
docker-compose up -d

# Check service health
docker-compose ps
docker-compose logs -f api

# Verify API is running
curl http://localhost:8000/health
```

### Method 2: Standalone Docker

```bash
# Build the image
docker build -t claimsense:latest .

# Run the container
docker run -d \
  --name claimsense \
  -p 8000:8000 \
  --env-file .env \
  -v /var/claimsense/uploads:/app/uploads \
  -v /var/claimsense/reports:/app/reports \
  claimsense:latest
```

### Method 3: Kubernetes

A Kubernetes deployment manifest example:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: claimsense
spec:
  replicas: 3
  selector:
    matchLabels:
      app: claimsense
  template:
    metadata:
      labels:
        app: claimsense
    spec:
      containers:
      - name: api
        image: claimsense:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: claimsense-secrets
              key: database-url
        # ... more env vars
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

## Database Setup

### Initial Setup

1. **Ensure PostgreSQL is running**
   ```bash
   docker-compose ps db
   ```

2. **Tables are auto-created on startup** via the lifespan hook in `app/main.py`

3. **For future migrations**, use Alembic:
   ```bash
   # Generate a migration
   alembic revision --autogenerate -m "Add new column"
   
   # Apply migrations
   alembic upgrade head
   
   # Rollback last migration
   alembic downgrade -1
   ```

### Backup Strategy

```bash
# Backup database
docker-compose exec db pg_dump -U postgres claimsense > backup.sql

# Restore from backup
docker-compose exec db psql -U postgres claimsense < backup.sql
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with username/password
- `GET /api/auth/me` - Get current user info

### Claims
- `POST /api/upload-claim` - Upload claim documents
- `GET /api/claims` - List claims (with search)
- `POST /api/claims/{id}/process` - Start claim processing
- `GET /api/claims/{id}/status` - Get processing status
- `GET /api/claims/{id}` - Get claim details
- `POST /api/claims/{id}/adjuster-action` - Approve/reject/review
- `GET /api/claims/{id}/pdf` - Download claim report

### Health
- `GET /health` - System health check

## Monitoring & Logging

### Check API Status
```bash
curl -X GET http://localhost:8000/health
```

### View Logs
```bash
# All services
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just Database
docker-compose logs -f db
```

### Structured Logging

The application uses Python's standard logging module. Configure logging levels in environment:
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages
- `WARNING` - Warning messages (default)
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

## Rate Limiting

The API implements rate limiting using token bucket algorithm:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/auth/login` | 5 | Per minute |
| `/api/upload-claim` | 10 | Per hour |
| `/api/claims/*/process` | 20 | Per hour |
| Other endpoints | 100 | Per minute |

Rate limit errors return `429 Too Many Requests`.

## Performance Optimization

### Frontend
- Built with Vite for fast development and optimized production builds
- React Router for client-side navigation
- Lazy loading of components

### Backend
- Database connection pooling (SQLAlchemy)
- Efficient OCR/PDF processing
- Asynchronous task processing with background jobs
- JWT caching (stateless authentication)

### Caching Recommendations
```yaml
# Example: Add Redis for caching
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Troubleshooting

### Issue: API won't start
```bash
# Check logs
docker-compose logs api

# Verify environment variables
docker-compose config | grep ENVIRONMENT
```

### Issue: Database connection failing
```bash
# Verify PostgreSQL is running
docker-compose ps db

# Test connection manually
docker-compose exec db psql -U postgres -d claimsense -c "SELECT 1;"
```

### Issue: Authentication errors
- Ensure `CLAIMSENSE_AUTH_SECRET` is set and same across all instances
- Verify JWT algorithm matches (`JWT_ALGORITHM=HS256`)
- Check token expiration (`JWT_EXPIRATION_HOURS`)

### Issue: Rate limiting too aggressive
Adjust rate limits in `app/middleware/rate_limit.py`:
```python
RATE_LIMITS = {
    "auth": "10/minute",  # Increase if needed
    "upload": "20/hour",
    "process": "30/hour",
    "default": "200/minute",
}
```

## Production Best Practices

### 1. Use Environment Variables
Never hardcode secrets. Use `.env` file (not in version control).

### 2. Enable HTTPS
Always use HTTPS in production. Use a reverse proxy (Nginx, HAProxy) or load balancer.

```nginx
# Example Nginx configuration
server {
    listen 443 ssl http2;
    server_name app.example.com;
    
    ssl_certificate /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Use Strong Passwords
- Demo password: At least 12 characters, mixed case, numbers, symbols
- Database password: At least 16 characters

### 4. Regular Backups
```bash
# Automated daily backup
0 2 * * * docker-compose -f /path/to/docker-compose.yml exec db pg_dump -U postgres claimsense > /backups/claimsense-$(date +\%Y\%m\%d).sql
```

### 5. Monitoring & Alerting
Set up monitoring for:
- CPU and memory usage
- Disk space
- API response times
- Database connections
- Authentication failures

### 6. Update Dependencies
Regularly update base images and packages:
```bash
docker-compose pull
docker-compose build --no-cache
docker-compose up -d
```

### 7. Disaster Recovery
- Test backup restoration monthly
- Document recovery procedures
- Maintain at least 2 backups at different locations
- Set up automated alerts for backup failures

## API Documentation

Interactive API documentation available at:
- Development: `http://localhost:8000/api/docs` (Swagger UI)
- Production: Disabled by default (can enable with `ENVIRONMENT=development`)

## Support & Troubleshooting

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify `.env` file configuration
3. Ensure database connectivity
4. Check API health endpoint: `curl http://localhost:8000/health`

## License

[Your License Here]
