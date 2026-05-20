# Getting Started with Production-Ready ClaimSense

## Quick Summary

You've been provided with a **production-ready** version of ClaimSense. Here's what's changed and how to get started.

## What's New (Production Enhancements)

### Security
- ✅ **JWT Authentication** - Industry-standard token-based auth (replaced custom implementation)
- ✅ **Hardened CORS** - Restricted to specific origins only (no wildcard)
- ✅ **Rate Limiting** - Token bucket algorithm to prevent abuse
- ✅ **Secrets Management** - All sensitive data via environment variables

### Deployment
- ✅ **Docker Compose** - Production-ready orchestration
- ✅ **Health Checks** - Built-in service health monitoring
- ✅ **Database Migrations** - Alembic framework for versioned schema changes
- ✅ **Comprehensive Logging** - Production-grade error handling

### Documentation
- ✅ **DEPLOYMENT.md** - Complete deployment guide
- ✅ **PRODUCTION_CONFIG.md** - Configuration reference
- ✅ **PRODUCTION_READINESS.md** - Detailed change summary
- ✅ **Updated README.md** - With production focus

## Quick Start (< 5 minutes)

### Option 1: Using Deployment Script (Recommended)
```bash
./deploy.sh
```
This script will:
1. Verify Docker/Docker Compose
2. Create `.env` file
3. Generate secure secrets
4. Prompt for configuration
5. Start all services
6. Verify health

### Option 2: Manual Deployment
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Generate secrets
python3 -c "import secrets; print('CLAIMSENSE_AUTH_SECRET=' + secrets.token_urlsafe(32))"

# 3. Edit .env with your values
nano .env
# Required fields:
#   ENVIRONMENT=production
#   DATABASE_URL=postgresql://...
#   CLAIMSENSE_AUTH_SECRET=<generated>
#   CLAIMSENSE_DEMO_PASSWORD=<strong-password>
#   GEMINI_API_KEY=<your-gemini-key>
#   CORS_ORIGINS=https://app.example.com

# 4. Start services
docker-compose up -d

# 5. Check health
curl http://localhost:8000/health
```

## Key Environment Variables

### Required (Must Set)
```bash
ENVIRONMENT=production                    # or development/staging
DATABASE_URL=postgresql+psycopg2://...    # PostgreSQL connection
CLAIMSENSE_AUTH_SECRET=...               # 32+ character secret
CLAIMSENSE_DEMO_PASSWORD=...             # Strong password
GEMINI_API_KEY=...                       # Google Gemini API key
CORS_ORIGINS=https://app.example.com    # Your frontend domain
```

### Optional (Has Defaults)
```bash
JWT_ALGORITHM=HS256                       # JWT signing algorithm
JWT_EXPIRATION_HOURS=168                 # Token lifetime (7 days)
UPLOAD_DIR=/app/uploads                  # Upload directory
REPORTS_DIR=/app/reports                 # Reports directory
MIN_TEXT_CHARS_PER_PAGE=40                # OCR quality threshold
```

See `.env.example` for all available options with descriptions.

## Testing the Setup

### 1. Health Check
```bash
curl http://localhost:8000/health
```
Response:
```json
{
  "status": "ok",
  "product": "ClaimSense",
  "database": "ok"
}
```

### 2. Login Test
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"adjuster","password":"YOUR_PASSWORD"}'
```

### 3. Get User Info
```bash
# Replace TOKEN with the token from login response
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer TOKEN"
```

### 4. View Logs
```bash
docker-compose logs -f api
```

## Important Changes from Previous Version

### 1. Authentication
- **Before**: Custom base64+HMAC tokens
- **After**: Standard JWT (PyJWT)
- **Impact**: All existing tokens are invalidated, users must re-login

### 2. CORS
- **Before**: Wildcard (`*`)
- **After**: Restricted to configured origins only
- **Impact**: Must set `CORS_ORIGINS` environment variable

### 3. Configuration
- **Before**: Hardcoded defaults for demo/development
- **After**: Environment-based, strict validation
- **Impact**: Production deployment requires explicit configuration

### 4. Secrets
- **Before**: "change-me-in-production" comments
- **After**: Validation fails if secrets not properly set
- **Impact**: Impossible to accidentally deploy with weak secrets

## Database Setup

### Automatic (On Startup)
- Tables are created automatically on first run
- Database schemas are initialized from models

### Manual (Future Migrations)
```bash
# Create a new migration
alembic revision --autogenerate -m "Description of change"

# Apply migrations
alembic upgrade head

# Rollback to previous version
alembic downgrade -1
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Get JWT token
- `GET /api/auth/me` - Get current user

### Claims
- `POST /api/upload-claim` - Upload documents
- `GET /api/claims` - List claims
- `POST /api/claims/{id}/process` - Start analysis
- `GET /api/claims/{id}/status` - Check progress
- `GET /api/claims/{id}` - Get results
- `POST /api/claims/{id}/adjuster-action` - Approve/reject

### System
- `GET /health` - Health check
- `GET /api/docs` - API documentation (dev only)

See full documentation at http://localhost:8000/api/docs when running in development mode.

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 | per minute |
| Upload | 10 | per hour |
| Process | 20 | per hour |

Exceeded limits return `HTTP 429 Too Many Requests`.

## Monitoring

### Service Status
```bash
docker-compose ps
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

### Database Connection
```bash
docker-compose exec db psql -U postgres -d claimsense -c "SELECT 1;"
```

## Troubleshooting

### API Won't Start
```bash
# Check logs
docker-compose logs api

# Verify environment variables
docker-compose config | head -20

# Ensure database is ready
docker-compose ps db
```

### Database Connection Error
```bash
# Check PostgreSQL is running
docker-compose ps db

# Verify database exists
docker-compose exec db psql -U postgres -l

# Test connection string
docker-compose config | grep DATABASE_URL
```

### Login Fails
- Verify `CLAIMSENSE_DEMO_PASSWORD` is set correctly
- Ensure `CLAIMSENSE_AUTH_SECRET` is at least 32 characters
- Check auth is using JWT format: `Authorization: Bearer <token>`

### CORS Errors
- Verify frontend domain matches `CORS_ORIGINS`
- Check browser console for exact origin being rejected
- Ensure protocol (http/https) matches exactly

## Production Deployment

### Pre-Flight Checklist
- [ ] Strong secrets (32+ characters)
- [ ] ENVIRONMENT=production
- [ ] HTTPS configured
- [ ] Database backups configured
- [ ] CORS origins for your domain
- [ ] Gemini API key valid
- [ ] Monitoring/alerting set up
- [ ] Disaster recovery plan documented

### Deploy to Server
1. Prepare secrets and environment
2. Run `./deploy.sh` or `docker-compose up -d`
3. Verify with `curl http://localhost:8000/health`
4. Test with actual user workflow
5. Set up monitoring and backups

See **DEPLOYMENT.md** for comprehensive production guide.

## Advanced Configuration

### High Availability
- Load balance multiple API instances
- Use managed PostgreSQL (RDS, CloudSQL)
- Use Redis for caching/sessions

### Performance Tuning
- Adjust database connection pool in `app/db/session.py`
- Use Gunicorn with multiple workers instead of uvicorn
- Set up CDN for frontend assets

### Monitoring
- Add Prometheus metrics export
- Configure error tracking (Sentry)
- Set up structured JSON logging (ELK Stack)

See **PRODUCTION_CONFIG.md** for detailed examples.

## Support & Resources

### Documentation
- **DEPLOYMENT.md** - Full deployment guide
- **PRODUCTION_CONFIG.md** - Configuration options
- **PRODUCTION_READINESS.md** - Technical details of changes

### API Documentation
- Interactive: http://localhost:8000/api/docs (when running)
- OpenAPI: http://localhost:8000/api/openapi.json

### Common Tasks

**Backup database**
```bash
docker-compose exec db pg_dump -U postgres claimsense > backup.sql
```

**Restore database**
```bash
docker-compose exec db psql -U postgres claimsense < backup.sql
```

**Stop services**
```bash
docker-compose down
```

**View service status**
```bash
docker-compose ps
```

**Update services**
```bash
docker-compose pull
docker-compose build --no-cache
docker-compose up -d
```

## Next Steps

1. **Start Services**
   ```bash
   ./deploy.sh
   # or
   docker-compose up -d
   ```

2. **Verify Health**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test Login**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"adjuster","password":"YOUR_PASSWORD"}'
   ```

4. **Read Documentation**
   - Review DEPLOYMENT.md for production setup
   - Review PRODUCTION_CONFIG.md for configuration options

5. **Deploy to Production**
   - Follow checklist in DEPLOYMENT.md
   - Configure monitoring and backups
   - Set up automated health checks

## Need Help?

1. Check logs: `docker-compose logs -f api`
2. Verify configuration: `docker-compose config | grep -i <variable>`
3. Test connectivity: `curl http://localhost:8000/health`
4. Review documentation files in the repo

---

**ClaimSense is now production-ready!** 🚀

For detailed information, see the comprehensive documentation files included in the project.
