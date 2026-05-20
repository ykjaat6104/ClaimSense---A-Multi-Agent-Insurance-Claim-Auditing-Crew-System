# ClaimSense — AI Claim Evaluation (Production-Ready)

ClaimSense is a **production-ready** adjuster-facing decision-support stack for insurance claims. It features a **React** dashboard, **FastAPI** backend, **PDF/OCR** extraction, **Gemini** structured field extraction, **RAG** (embeddings + semantic retrieval), **LangGraph** agents, **PostgreSQL** audit storage, and **PDF/JSON** exports.

> **Disclaimer**: Outputs support human review; they are not binding claim decisions.

## Key Features

- **Smart Document Processing** - PDF extraction, OCR, intelligent field recognition
- **AI-Powered Analysis** - Gemini integration for structured data extraction
- **RAG System** - Semantic search through policy documents and past claims
- **Agent Workflow** - LangGraph orchestration for approval/rejection decisions
- **Audit Trail** - Complete PostgreSQL audit log with adjuster actions
- **Secure Authentication** - JWT-based bearer tokens with rate limiting
- **Production-Ready** - Docker deployment, migrations, comprehensive logging

## Architecture

| Component | Technology |
|-----------|------------|
| **Frontend** | React 18 + TypeScript + Vite |
| **Backend** | FastAPI + Python 3.12 |
| **Database** | PostgreSQL 16 |
| **Authentication** | JWT (HS256) |
| **Rate Limiting** | Slowapi (token bucket) |
| **Containerization** | Docker + Docker Compose |

## Quick Start

### Prerequisites
- Docker & Docker Compose v2.0+
- Or: Python 3.12+, Node.js 20+, PostgreSQL 16+
- Google Gemini API key

### 1. Clone & Configure
```bash
git clone <repo-url>
cd ClaimSense

# Copy environment template
cp .env.example .env

# Edit with your production values
nano .env
```

Required environment variables:
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg2://user:pass@host/claimsense
GEMINI_API_KEY=your-api-key-here
CLAIMSENSE_AUTH_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
CLAIMSENSE_DEMO_PASSWORD=strong-password-here
```

### 2. Run with Docker Compose
```bash
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 3. Test the API
```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"adjuster","password":"YOUR_PASSWORD"}'
```

## Development Setup

### Backend
```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start PostgreSQL
docker run -d --name claimsense-db \
  -e POSTGRES_DB=claimsense \
  -p 5432:5432 \
  postgres:16-alpine

# Run API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Hot Reload)
```bash
cd web
npm install
npm run dev
```

Navigate to `http://localhost:5173` (Vite proxies `/api` to `http://localhost:8000`)

## Project Structure

```
ClaimSense/
├── app/
│   ├── api/              # API routes
│   ├── db/               # Database models & CRUD
│   ├── services/         # Business logic (auth, extraction, PDF)
│   ├── schemas/          # Pydantic models
│   ├── middleware/       # Rate limiting, CORS
│   ├── config.py         # Settings management
│   └── main.py           # FastAPI application
├── web/                  # React frontend
│   ├── src/
│   ├── dist/            # Built production assets
│   ├── package.json
│   └── vite.config.ts
├── alembic/             # Database migrations
├── samples/             # Test documents
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Local development/production
├── DEPLOYMENT.md        # Deployment guide
└── PRODUCTION_CONFIG.md # Production configuration
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Authenticate and get JWT token
- `GET /api/auth/me` - Get current user info

### Claims Management
- `POST /api/upload-claim` - Upload claim documents (5 file max)
- `GET /api/claims` - List claims (with search)
- `POST /api/claims/{id}/process` - Start AI analysis
- `GET /api/claims/{id}/status` - Check processing status
- `GET /api/claims/{id}` - Get claim details & results
- `POST /api/claims/{id}/adjuster-action` - Approve/reject/review
- `GET /api/claims/{id}/pdf` - Download report PDF

### System
- `GET /health` - System health check
- `GET /api/docs` - Interactive API documentation (dev only)

## Production Deployment

### Quick Deploy
```bash
# 1. Prepare environment
cp .env.example .env
nano .env  # Fill in production values

# 2. Generate secrets
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Start services
docker-compose up -d

# 4. Verify health
curl http://localhost:8000/health
```

### Production Checklist
- [ ] Use strong secrets (32+ characters)
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure CORS origins for your domain
- [ ] Enable HTTPS with SSL/TLS
- [ ] Set up database backups
- [ ] Configure monitoring & logging
- [ ] Test disaster recovery
- [ ] Review security policies

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment guide.

## Database Migrations

### Auto-create Tables (Development)
Tables are created automatically on startup via SQLAlchemy `create_all()`.

### Using Alembic (Production)
```bash
# Create new migration
alembic revision --autogenerate -m "Add field X"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 | per minute |
| Upload | 10 | per hour |
| Process | 20 | per hour |
| Other | 100 | per minute |

Exceeded limits return `429 Too Many Requests`.

## Configuration

### Environment Variables
See `.env.example` for all available settings:
- **Database**: Connection pool, credentials
- **Security**: Auth secrets, CORS origins
- **AI**: Gemini API key, models
- **Processing**: File size limits, OCR settings

### Logging
```bash
# Set log level
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps db

# Test connection
docker-compose exec db psql -U postgres -d claimsense -c "SELECT 1;"
```

### API Won't Start
```bash
# Check logs
docker-compose logs api

# Verify environment
docker-compose config | grep ENVIRONMENT
```

### Authentication Errors
- Verify `CLAIMSENSE_AUTH_SECRET` is set and 32+ characters
- Ensure `CLAIMSENSE_DEMO_PASSWORD` is configured
- Check token hasn't expired (default: 7 days)

### Rate Limiting Too Strict
Edit limits in `app/middleware/rate_limit.py`:
```python
RATE_LIMITS = {
    "auth": "10/minute",  # Increase as needed
    "upload": "20/hour",
    "process": "30/hour",
}
```

## Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide, scaling, monitoring
- **[PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md)** - Environment configuration, optimization, backup strategies
- **[API Docs](http://localhost:8000/api/docs)** - Interactive Swagger documentation (when running)

## Backup & Recovery

### Automated Daily Backup
```bash
# Backup database
docker-compose exec db pg_dump -U postgres claimsense > backup.sql

# Backup uploads & reports
tar -czf uploads-backup.tar.gz ./uploads
tar -czf reports-backup.tar.gz ./reports
```

### Restore from Backup
```bash
# Restore database
docker-compose exec db psql -U postgres claimsense < backup.sql

# Restore files
tar -xzf uploads-backup.tar.gz
tar -xzf reports-backup.tar.gz
```

## Security

- **Authentication**: JWT with HS256 (configurable)
- **CORS**: Restricted to configured origins only
- **Rate Limiting**: Protects against brute-force and DoS
- **Database**: Connection pooling, SSL support
- **Secrets**: Environment-based, never hardcoded
- **Audit Trail**: Complete action logging in PostgreSQL

## Performance

- **Database Connection Pooling**: SQLAlchemy with configurable pool size
- **Async Processing**: Background task support for long operations
- **Caching**: JWT tokens are stateless (no session storage)
- **Compression**: GZIP support for responses

## Technologies

- **Frontend**: React, TypeScript, Vite, React Router
- **Backend**: FastAPI, Pydantic, SQLAlchemy
- **AI**: Google Gemini, LangChain, LangGraph
- **Document Processing**: PyMuPDF, Tesseract, Pillow, ReportLab
- **Database**: PostgreSQL with Alembic migrations
- **Auth**: PyJWT
- **Rate Limiting**: Slowapi

## License

MIT License — See LICENSE file for details

## Support & Issues

For issues, questions, or feature requests:
1. Check existing documentation
2. Review API documentation at `/api/docs`
3. Check logs: `docker-compose logs -f`
4. Verify `.env` configuration

## Contributing

To contribute:
1. Create a feature branch
2. Make changes following project conventions
3. Test thoroughly (especially security-related changes)
4. Submit pull request

---

**ClaimSense** — Empowering Insurance Adjusters with AI

