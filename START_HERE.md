# 🚀 ClaimSense - Start Here

Welcome! Your ClaimSense project is now **production-ready**. Here's where to go based on what you need:

## Quick Navigation

### I want to... 
- **Get the project running quickly** → [GETTING_STARTED.md](GETTING_STARTED.md) (5 min read)
- **Deploy to production** → [DEPLOYMENT.md](DEPLOYMENT.md) (30 min read)
- **Understand what changed** → [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) (15 min read)
- **Configure environment variables** → [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md)
- **See project overview** → [README.md](README.md)

## 30-Second Quick Start

```bash
# 1. Run automated setup
./deploy.sh

# 2. Wait for services to start
# 3. Test the health check
curl http://localhost:8000/health
```

## Key Files You Need

| File | Purpose | Time |
|------|---------|------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Quick setup guide | 5 min |
| [.env.example](.env.example) | Environment template | - |
| [deploy.sh](deploy.sh) | Automated setup script | - |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment | 30 min |
| [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md) | Configuration reference | - |

## What's New (Production Enhancements)

✅ **Security**: JWT auth, hardened CORS, rate limiting
✅ **Database**: Alembic migrations, connection pooling
✅ **Deployment**: Production Docker Compose, health checks
✅ **Documentation**: 45+ pages of guides and examples

## Critical Before Deployment

Set these environment variables (see `.env.example`):
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg2://...
CLAIMSENSE_AUTH_SECRET=<32+ character secret>
CLAIMSENSE_DEMO_PASSWORD=<strong password>
GEMINI_API_KEY=<your API key>
CORS_ORIGINS=https://app.example.com
```

Generate secrets:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Common Commands

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Health check
curl http://localhost:8000/health

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"adjuster","password":"YOUR_PASSWORD"}'
```

## Documentation Structure

```
📖 README.md                 ← Project overview
📖 START_HERE.md            ← You are here
📖 GETTING_STARTED.md       ← Quick setup (5 min)
📖 DEPLOYMENT.md            ← Production guide (30 min)
📖 PRODUCTION_CONFIG.md     ← Configuration reference
📖 PRODUCTION_READINESS.md  ← Technical details
```

## Next Step

👉 **Read [GETTING_STARTED.md](GETTING_STARTED.md)** (takes 5 minutes)

Then either:
- Run `./deploy.sh` for automated setup
- Or follow manual steps in the guide

## Questions?

Check the troubleshooting section in [GETTING_STARTED.md](GETTING_STARTED.md) or [DEPLOYMENT.md](DEPLOYMENT.md).

---

**Your project is production-ready. Let's go! 🎉**
