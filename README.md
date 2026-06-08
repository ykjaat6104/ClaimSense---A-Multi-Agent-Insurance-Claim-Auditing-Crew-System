# ClaimSense - A Multi-Agent Insurance Claim Auditing Crew System

ClaimSense is a multi-agent, AI-assisted insurance claim auditing platform built to help adjusters review claims with better structure, stronger evidence handling, and clearer decision support.

It combines document upload, OCR/text extraction, structured field extraction, policy retrieval, multi-agent reasoning, fraud/risk scoring, and report generation into one workflow.

> Disclaimer: ClaimSense is decision-support software. Final claim decisions should always remain with a qualified human reviewer.

## ✨ What ClaimSense Does

- Ingests claim, invoice, policy, extra docs, and evidence files.
- Extracts text from PDFs, images, and text uploads.
- Structures claim data into machine-readable JSON.
- Retrieves relevant policy clauses using hybrid RAG (graph-aware as primary, simple vector as fallback).
- Runs a multi-agent debate (Policy Analyst, Data Miner, Fraud Auditor, Judge) to produce decisions and scores.
- Computes fraud probability and risk scores.
- Generates PDF and DOCX reports and an audit trail for each processed claim.
- Serves a React dashboard for case review and workflow tracking.

## 🧱 Core Architecture

ClaimSense is organized as four cooperating layers: the user interface, the API and workflow layer, the intelligence layer, and the persistence/infrastructure layer. Each layer is intentionally narrow so the claim lifecycle stays traceable from upload to report output.

### 1) Layered architecture view

```mermaid
flowchart TB
  subgraph L1[Presentation Layer]
    UI[React + Vite UI]
    ROUTER[React Router Pages]
  end

  subgraph L2[Application Layer]
    FASTAPI[FastAPI]
    ROUTES[Auth + Claims Routes]
    SVC[Services: parsing, extraction, RAG, PDF, scoring]
    AGENTS[LangGraph Agent Workflow]
  end

  subgraph L3[Intelligence Layer]
    LLM[Gemini-assisted reasoning]
    RULES[Deterministic rules + thresholds]
    ML[Fraud/anomaly models]
  end

  subgraph L4[Data Layer]
    PG[(PostgreSQL)]
    FILES[(Uploads + Reports)]
    MIG[Alembic migrations]
  end

  UI --> ROUTER --> FASTAPI
  FASTAPI --> ROUTES --> SVC
  SVC --> AGENTS
  AGENTS --> LLM
  AGENTS --> RULES
  SVC --> ML
  SVC --> PG
  SVC --> FILES
  MIG --> PG
```

The agent layer is designed as a crew of specialized roles that review the same claim from different angles:

- **Policy Analyst**: extracts policy coverage details from policy text and retrieved clauses.
- **Data Miner**: analyzes customer history, payment status, and prior-claim patterns.
- **Fraud Auditor**: looks for suspicious patterns, market mismatches, and anomaly signals.
- **Judge**: synthesizes all evidence and emits the final decision-support outcome.

### 🎓 Policy Analyst (The Scholar)
- **Job**: Extract policy coverage details, exclusions, limits, deductibles, and clause relationships.
- **Tools**: Hybrid RAG (graph-aware: knowledge graph + vector + BM25 as primary; simple vector as fallback).
- **Output**: Coverage limits, exclusions, deductibles, clause_relationships, rag_method_used.
- **Example**: "This policy covers theft up to $10,000 with $500 deductible"

### 🔍 Data Miner (The Investigator)
- **Job**: Analyze customer history and patterns.
- **Tools**: Database queries for claims history, payment status.
- **Output**: Customer profile, frequency analysis, red flags.
- **Example**: "Customer has filed 0 claims in past 12 months, all payments current"

### 😼 Fraud Auditor (The Cynic)
- **Job**: Look for suspicious patterns and anomalies.
- **Tools**: Web search for market prices, vendor verification.
- **Output**: Suspicious flags, market analysis, risk assessment.
- **Example**: "Claimed $5,000 for item worth $1,200 (4.17x markup)"

### ⚖️ Judge (The Final Arbitrator)
- **Job**: Synthesize evidence and issue final verdict.
- **Tools**: LLM with structured output.
- **Output**: APPROVED/DENIED/ESCALATED with payout amount and risk score.
- **Example**: "APPROVED at fair market value ($1,700 after deductible)"

## 🧭 Navigation Tabs

The app nav is intentionally small. The table below lists each tab, what it is for, and whether it is needed today.

| Tab | What it is for |
|---|---|
| Dashboard | Portfolio overview, recent claims, and risk posture. |
| Claims Mgmt. | Upload claim, invoice, policy, extra docs, and evidence files, then run the multi-agent workflow. |
| Results | Browse completed evaluations and export reports as PDF, JSON, or DOCX. |
| Reports | Search historical claims, compare cases, and open report detail pages. |
| Results (detail) | Claim-level multi-agent output and human decision buttons. Reached by clicking a claim ID. |

### Multi-modal ingestion flow

ClaimSense works with several input modalities at once:

```
Inputs
┌─────────────────────────┐
│ Claim Form              │──┐
│ (PDF/Image/Text)        │  |
├─────────────────────────┤  │
│ Invoice / Estimate      │  ├──► [Text Extraction] ──► [Normalize & Clean Text] ──► [Structured JavaScript Object Notation] 
│ (PDF/Image/Text)        |  |                                                                                       |              
├─────────────────────────┤  │                                                                                       |              
│ Policy Document         │  │                                                                                       |              
│ (PDF/Image/Text)        |  |                                                                                       |              
├─────────────────────────┤  │                                                                                       |              
│ Optional Extra Docs     │──┘
├─────────────────────────┤
│ Optional Evidence Files │──┘                                                                                       |              
└─────────────────────────┘                                                                                          ▼              
                                                               ┌─────────────────────────┐     ┌───────────────────────────────────┐
                                                               │    Hybrid RAG           │──►  │                                   |
                                                               │ Policy Retrieval        │     │    Agent Debate                   │ ──► ┌────────────────────────┐
                                                               └─────────────────────────┘     │    (Multi-Agent System)           │     │ Verdict / Risk Score   │
                                                                                                │                                   │     | Fraud Probability /    │
                                                               ┌─────────────────────────┐     └───────────────────────────────────┘     │ PDF Report             |
                                                               │   Past Claims           │──►                                            └────────────────────────┘
                                                               │  (CSV / History/        │
                                                               |  Behavioral Signals     │
                                                               └─────────────────────────┘


```

## 🧠 Detailed Data Flow

1. A user signs in and receives a JWT session token.
2. The UI submits the claim package to the backend through multipart upload.
3. The upload handler validates file size, type, and claim completeness.
4. Files are stored under a claim-specific directory for traceability.
5. Text extraction runs across claim, invoice, policy, and evidence inputs.
6. Structured extraction converts unstructured text into normalized JSON payloads.
7. Hybrid RAG retrieves policy context (primary: graph-aware with knowledge graph, BM25, and vectors; fallback: simple vector).
8. The multi-agent graph runs: Policy Analyst + Data Miner (parallel) -> Fraud Auditor -> Conditional Router -> Judge.
9. Fraud, anomaly, and risk scorers convert the raw signals into reviewable scores.
10. A report is rendered to PDF and linked back to the claim record.
11. The frontend refreshes status, logs, and downloadable report state.
12. The result stays auditable in PostgreSQL for later review and reporting.

For the full technical deep dive on agents, fraud detection, and architecture, see [MULTI_AGENT_ARCHITECTURE.md](MULTI_AGENT_ARCHITECTURE.md).

## 🛠 Tech Stack

### 🎨 Frontend Stack

| Component | Technology | Purpose |
|---|---|---|
| UI Framework | React 18 | Browser interface for adjusters and reviewers |
| Language | TypeScript | Typed UI logic and safer refactors |
| Build Tool | Vite | Fast local development and production builds |
| Routing | React Router DOM | Auth-gated navigation and page routing |
| Charting | Recharts | Interactive bar, pie, and gauge chart visualizations |

### 🧠 Backend Stack

| Component | Technology | Purpose |
|---|---|---|
| Runtime | Python 3.12 | Core application runtime |
| API Framework | FastAPI 0.115 | API server, validation, and OpenAPI docs |
| ASGI Server | Uvicorn | ASGI server for development and deployment |
| ORM | SQLAlchemy 2.0 | Database access and domain persistence |
| Settings | Pydantic v2 / Settings | Request models and environment config |
| Migrations | Alembic | Schema migrations |
| Auth | PyJWT | Token authentication |
| Rate Limiting | SlowAPI | Rate limiting and abuse control |
| Async Jobs | Celery + Redis | Optional async queue and worker support |

### 🧾 Document Processing Stack

| Component | Technology | Purpose |
|---|---|---|
| PDF Parsing | PyMuPDF | PDF text extraction and page handling |
| OCR | pytesseract + Tesseract OCR | OCR for scanned documents and images |
| Image Handling | Pillow | Image loading and preprocessing |
| PDF Generation | ReportLab | Final claim PDF report rendering |
| DOCX Generation | python-docx | Final claim DOCX report rendering |

### 🤖 AI, Retrieval, and Agent Stack

| Component | Technology | Purpose |
|---|---|---|
| LLM Provider | Google Generative AI | Extraction and agent reasoning support |
| Prompt Utilities | LangChain Core | Prompt and chain utilities |
| Integrations | LangChain Community | Additional integrations and helpers |
| Orchestration | LangGraph | Multi-step agent workflow orchestration |
| Retrieval | Hybrid RAG service | Graph-aware hybrid RAG (vector + BM25 + knowledge graph) with simple fallback |

### 📊 Analytics and Fraud Stack

| Component | Technology | Purpose |
|---|---|---|
| Anomaly Detection | scikit-learn | Fraud/anomaly detection tooling |
| Gradient Boosting | xgboost / lightgbm | Optional model-based scoring support |
| Numeric Processing | numpy / pandas / scipy | Feature work and statistical processing |

### 🗄 Data and Storage Stack

| Component | Technology | Purpose |
|---|---|---|
| Primary Database | PostgreSQL | Persistent claims, logs, and report metadata |
| File Storage | Upload directory + reports directory | Claim inputs and generated artifacts |

### 🚢 Deployment and Operations Stack

| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker | Containerized runtime packaging |
| Configuration | Environment variables | Environment-specific configuration |
| Observability | Health endpoint | Service and database readiness checks |
| Local Dev | `.env` + Vite proxy | Fast local workflow with backend proxying |

### ✅ Quality and Testing Stack

| Component | Technology | Purpose |
|---|---|---|
| Testing | pytest | Unit, integration, and pipeline testing |
| API Testing | httpx | HTTP client utilities for tests |
| Coverage | pytest-cov | Coverage reporting |
| Linting / Formatting | black, flake8, isort | Style and code quality checks |
| Type Checking | mypy | Static typing validation |

## 📁 Project Structure

```text
ClaimSense/
├── app/
│   ├── api/             # Auth and claim endpoints
│   ├── agents/          # Multi-agent graph, nodes, state, tools
│   ├── db/              # SQLAlchemy models, CRUD, session helpers
│   ├── middleware/      # Rate limiting and request controls
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Parsing, extraction, RAG, scoring, PDF generation
│   ├── config.py        # Environment settings
│   └── main.py          # FastAPI application entrypoint
├── web/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── alembic/             # Migration environment
├── samples/             # Example claim and policy documents
├── tests/               # Unit, integration, and e2e test scaffolding
├── requirements.txt     # Python dependencies
├── deploy.sh            # Production bootstrap helper
├── LICENSE              # MIT License
└── README.md            # You are here
```

## 🔍 Main Runtime Components

- `app/main.py`: boots FastAPI, configures CORS, health checks, SPA fallback routing, and startup initialization.
- `app/api/router.py`: mounts the `/api/auth` and `/api` claim routes.
- `app/api/claims.py`: handles uploads, processing, status, claim retrieval, comparison, PDF download, and DOCX download.
- `app/services/document_parser.py`: extracts text from different file types.
- `app/services/extraction.py`: converts raw text into structured claim data.
- `app/services/rag_service.py`: vector and hybrid (vector+BM25) policy retrieval.
- `app/services/policy_graph.py`: knowledge graph for clause extraction and relationship inference.
- `app/services/hybrid_rag_service.py`: orchestrator that chooses graph-aware hybrid RAG (primary) or fallback methods.
- `app/agents/graph.py`: runs the approve/reject/mediator workflow.
- `app/services/risk_scoring.py`: turns mediator output into risk and fraud scores.
- `app/services/report_pdf.py`: renders the final PDF report.
- `app/services/report_docx.py`: renders the final DOCX report.

## 🚪 API Surface

### Authentication

- `POST /api/auth/login` - log in with the demo or configured user.
- `GET /api/auth/me` - return the authenticated user profile.

### Claims

- `POST /api/upload-claim` - upload claim, invoice, policy, extra docs, and evidence files (multipart).
- `POST /api/claims/{claim_id}/process` - start async analysis.
- `GET /api/claims` - list recent claims.
- `GET /api/claims/{claim_id}` - fetch full claim details.
- `GET /api/claims/{claim_id}/status` - retrieve processing state and logs.
- `GET /api/claims/{claim_id}/pdf` - download the generated PDF report.
- `GET /api/claims/{claim_id}/docx` - download the generated DOCX report.
- `GET /api/claims/compare?ids=...` - compare multiple claims.

### Health

- `GET /health` - service and database health check.

## 🚀 Installation

### Prerequisites

- Python 3.12 or newer
- Node.js 20 or newer
- PostgreSQL 16 or a compatible PostgreSQL database
- Tesseract OCR installed on the host if you want the local OCR path available
- A Gemini API key if you want the LLM-backed extraction and agent reasoning path enabled

### 1) Clone the repository

```bash
git clone <repo-url>
cd ClaimSense
```

### 2) Create the Python environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Install frontend dependencies

```bash
cd web
npm install
cd ..
```

### 4) Configure environment variables

Copy the example file and edit it for your environment:

```bash
cp .env.example .env
```

Minimum required values for a real deployment:

```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/claimsense
CLAIMSENSE_AUTH_SECRET=generate_a_strong_32_plus_character_secret
CLAIMSENSE_DEMO_PASSWORD=choose_a_strong_demo_password
GEMINI_API_KEY=your_gemini_key
```

Useful optional values:

```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
UPLOAD_DIR=./uploads
REPORTS_DIR=./reports
JWT_EXPIRATION_HOURS=168
TAVILY_API_KEY=
```

You can generate a secure auth secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## ▶️ Run Guide

### Backend in development

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend in development

```bash
cd web
npm run dev
```

The frontend runs on Vite and proxies API requests to the backend on `http://127.0.0.1:8000`.

### Open the app

- Web UI: `http://localhost:5173`
- API health: `http://localhost:8000/health`
- Interactive docs: `http://localhost:8000/api/docs`

### Production-style local run

If you want to run the backend without hot reload:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then build and preview the frontend:

```bash
cd web
npm run build
npm run preview
```

## 🧪 Testing

Run the Python test suite:

```bash
pytest
```

If you want coverage or focused checks, use the test files under `tests/unit`, `tests/integration`, and `tests/e2e`.

## 🧰 Useful Commands

```bash
# Format / lint toolchain is available through requirements.txt
pytest tests/unit/test_api_endpoints.py
pytest tests/unit/test_fraud_detection.py
```

## 🔐 Security and Safety Notes

- JWT authentication is required for protected routes.
- File uploads are limited in size and validated by type.
- CORS is environment-configurable.
- Rate limiting is enabled to reduce abuse.
- Production deployments should use a strong `CLAIMSENSE_AUTH_SECRET` and a secure `DATABASE_URL`.
- Gemini-backed reasoning is assistive, not authoritative.

## 📦 Deployment Notes

- The app is Docker-friendly through the provided `Dockerfile`.
- The backend can boot its required directories at startup.
- Database migrations are supported through Alembic.
- In production, prefer an external PostgreSQL instance and a proper secret management strategy.

## 🤝 Contributing

Contributions are welcome. If you want to improve ClaimSense, the most useful areas are:

- claim extraction quality
- multi-agent reasoning prompts
- fraud and anomaly scoring
- UI polish and workflow clarity
- tests and observability
- documentation improvements

Please keep changes focused, well-tested, and consistent with the existing architecture.

## ⭐ If You Like ClaimSense

If this project helps you or you find it useful, drop a star on the repository.

It genuinely helps the project get noticed and motivates further improvements.

## 📝 License

This project is licensed under the MIT License. See [LICENSE](/home/obito84r/Documents/Code/Projects/ClaimSense/LICENSE) for the full text.
