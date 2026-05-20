#!/bin/bash
# Production Deployment Quick Start Script
# This script helps set up ClaimSense for production deployment

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ClaimSense Production Deployment Quick Start           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker and Docker Compose
echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker and Docker Compose found${NC}"

# Create .env file
echo -e "\n${YELLOW}[2/5] Setting up environment configuration...${NC}"
if [ -f .env ]; then
    echo -e "${YELLOW}⚠ .env already exists${NC}"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping .env creation"
    else
        cp .env.example .env
        echo -e "${GREEN}✓ .env created${NC}"
    fi
else
    cp .env.example .env
    echo -e "${GREEN}✓ .env created from template${NC}"
fi

# Generate secrets
echo -e "\n${YELLOW}[3/5] Generating production secrets...${NC}"

echo ""
echo "Generate the following and add to .env:"
echo ""

echo -e "${YELLOW}1. Authentication Secret (paste into CLAIMSENSE_AUTH_SECRET):${NC}"
AUTH_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "FAILED_TO_GENERATE")
if [ "$AUTH_SECRET" != "FAILED_TO_GENERATE" ]; then
    echo -e "${GREEN}${AUTH_SECRET}${NC}"
else
    echo -e "${RED}Failed to generate. Run manually:${NC}"
    echo "python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
fi

echo ""
echo -e "${YELLOW}2. Database Password (paste into DB_PASSWORD):${NC}"
DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || echo "FAILED_TO_GENERATE")
if [ "$DB_PASS" != "FAILED_TO_GENERATE" ]; then
    echo -e "${GREEN}${DB_PASS}${NC}"
else
    echo -e "${RED}Failed to generate. Run manually:${NC}"
    echo "python3 -c \"import secrets; print(secrets.token_urlsafe(16))\""
fi

echo ""
echo -e "${YELLOW}3. Demo User Password (paste into CLAIMSENSE_DEMO_PASSWORD):${NC}"
DEMO_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(12))" 2>/dev/null || echo "FAILED_TO_GENERATE")
if [ "$DEMO_PASS" != "FAILED_TO_GENERATE" ]; then
    echo -e "${GREEN}${DEMO_PASS}${NC}"
else
    echo -e "${RED}Failed to generate. Run manually:${NC}"
    echo "python3 -c \"import secrets; print(secrets.token_urlsafe(12))\""
fi

echo ""
echo -e "${YELLOW}Edit .env with your configuration:${NC}"
echo "  - ENVIRONMENT=production"
echo "  - DATABASE_URL=postgresql+psycopg2://..."
echo "  - GEMINI_API_KEY=your-key-here"
echo "  - CORS_ORIGINS=https://app.example.com"
echo ""

# Ask user to confirm
read -p "Edit .env now? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if command -v nano &> /dev/null; then
        nano .env
    elif command -v vim &> /dev/null; then
        vim .env
    else
        echo -e "${YELLOW}Open .env in your editor and configure the required values${NC}"
    fi
fi

# Build and start services
echo -e "\n${YELLOW}[4/5] Building and starting services...${NC}"
docker-compose build
docker-compose up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}[5/5] Waiting for services to be healthy...${NC}"
sleep 5

# Check health
echo ""
echo "Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$HEALTH" = "ok" ] || [ "$HEALTH" = "degraded" ]; then
            echo -e "${GREEN}✓ API is healthy${NC}"
            break
        fi
    fi
    echo -n "."
    sleep 2
done

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ClaimSense is now running!                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Display service information
echo "Services:"
echo "  API:      http://localhost:8000"
echo "  Health:   http://localhost:8000/health"
echo "  Docs:     http://localhost:8000/api/docs (dev mode only)"
echo ""

echo "Next steps:"
echo "  1. Test login:"
echo "     curl -X POST http://localhost:8000/api/auth/login \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"username\":\"adjuster\",\"password\":\"YOUR_PASSWORD\"}'"
echo ""
echo "  2. Check logs:"
echo "     docker-compose logs -f api"
echo ""
echo "  3. Review documentation:"
echo "     - DEPLOYMENT.md - Full deployment guide"
echo "     - PRODUCTION_CONFIG.md - Configuration options"
echo "     - PRODUCTION_READINESS.md - Implementation summary"
echo ""
