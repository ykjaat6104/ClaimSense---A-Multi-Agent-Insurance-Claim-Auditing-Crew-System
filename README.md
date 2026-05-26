# ClaimSense - A Multi-Agent Insurance Claim Auditing Crew System

ClaimSense is a multi-agent, AI-assisted insurance claim auditing platform built to help adjusters review claims with better structure, stronger evidence handling, and clearer decision support.

It combines document upload, OCR/text extraction, structured field extraction, policy retrieval, multi-agent reasoning, fraud/risk scoring, and report generation into one workflow.

> Disclaimer: ClaimSense is decision-support software. Final claim decisions should always remain with a qualified human reviewer.

## ✨ What ClaimSense Does

- Ingests claim, invoice, policy, and optional evidence files.
- Extracts text from PDFs, images, and text uploads.
- Structures claim data into machine-readable JSON.
- Retrieves relevant policy clauses using RAG-style retrieval.
- Runs a multi-agent debate to support approve, reject, or review outcomes.
- Computes fraud probability and risk scores.
- Generates a PDF report and audit trail for each processed claim.
- Serves a React dashboard for case review and workflow tracking.

## 🧱 Core Architecture

ClaimSense is organized as four cooperating layers: the user interface, the API and workflow layer, the intelligence layer, and the persistence/infrastructure layer. Each layer is intentionally narrow so the claim lifecycle stays traceable from upload to report output.

### 1) High-level system view

```mermaid
flowchart LR
  U[Adjuster / Reviewer] --> W[React Web App]
  W -->|JWT + REST| API[FastAPI API Layer]
  API --> AUTH[Auth + Rate Limit]
  API --> PIPE[Claim Workflow Engine]
  PIPE --> EX[Document Parsing & OCR]
  EX --> STR[Structured Extraction]
  STR --> RAG[Policy Retrieval]
  RAG --> AG[Multi-Agent Claim Review]
  AG --> SCORE[Risk + Fraud Scoring]
  SCORE --> PDF[PDF Report Builder]
  SCORE --> DB[(PostgreSQL Audit Store)]
  PDF --> W
  DB --> W
```

### 2) Layered architecture view

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

### 3) Claim workflow sequence

```mermaid
sequenceDiagram
  autonumber
  actor Adjuster as Adjuster
  participant Web as React UI
  participant API as FastAPI API
  participant Store as File Store
  participant Parse as Parser/OCR
  participant Extract as Structured Extraction
  participant RAG as Policy Retrieval
  participant Agents as Multi-Agent Graph
  participant Score as Risk Scoring
  participant DB as PostgreSQL
  participant PDF as PDF Renderer

  Adjuster->>Web: Sign in and upload claim package
  Web->>API: POST /api/upload-claim
  API->>Store: Save claim, invoice, policy, evidence
  API->>Parse: Read and normalize source documents
  Parse->>Extract: Send raw text
  Extract->>RAG: Build retrieval query
  RAG->>Agents: Provide relevant policy snippets
  Agents->>Score: Approve / Reject / Mediator output
  Score->>DB: Persist score, logs, and verdict data
  Score->>PDF: Render final report
  PDF->>DB: Store report path and status
  API->>Web: Return status, logs, and final result
```

### 4) Multi-agent workflow and roles

This is the core review loop used by ClaimSense. The claim is first normalized, then split into parallel analysis paths, then reconciled by a conditional router and final judge.

```mermaid
flowchart TD
  IN[Claim Input] --> EX[Extraction]
  EX --> SM[State Management]
  SM --> PA[Policy Analyst]
  SM --> DM[Data Miner]
  PA --> PAR[Parallel Execution]
  DM --> PAR
  PAR --> FA[Fraud Auditor]
  FA --> CR[Conditional Router]
  CR --> J[Judge Node]
  J --> OUT[Final Decision]
```

The agent layer is designed as a crew of specialized roles that review the same claim from different angles:

- Policy Analyst: extracts policy coverage details from policy text and retrieved clauses.
- Data Miner: analyzes customer history, payment status, and prior-claim patterns.
- Fraud Auditor: looks for suspicious patterns, market mismatches, and anomaly signals.
- Judge: synthesizes all evidence and emits the final decision-support outcome.

```mermaid
flowchart TD
  INPUT[Structured claim, invoice, policy, evidence, and RAG snippets] --> PA[Policy Analyst]
  INPUT --> DM[Data Miner]
  PA --> FA[Fraud Auditor]
  DM --> FA
  FA --> ROUTER[Conditional Router]
  ROUTER --> JUDGE[Judge Node]
  JUDGE --> OUTPUT[Decision Support Output]
  OUTPUT --> VERDICT{Approved / Rejected / Review}
  VERDICT -->|Approved| PAY[Suggested payout amount]
  VERDICT -->|Rejected| DENY[Denial rationale]
  VERDICT -->|Review| ESC[Escalation for manual review]
```

## 🤖 Agent Roles & Responsibilities

### 🎓 Policy Analyst (The Scholar)
- **Job**: Extract policy coverage details.
- **Tools**: RAG search on policy documents.
- **Output**: Coverage limits, exclusions, deductibles.
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

### 5) Multi-modal ingestion flow

ClaimSense works with several input modalities at once:

```mermaid
flowchart LR
  C[Claim Form PDF / Image / Text] --> T[Text Extraction]
  I[Invoice / Estimate PDF / Image / Text] --> T
  P[Policy PDF / Image / Text] --> T
  E[Optional Evidence Files] --> T
  H[Optional Past Claims CSV] --> HX[Historical Context Builder]
  T --> N[Normalize and Clean Text]
  N --> J[Structured JSON Objects]
  J --> RAG[Policy Retrieval and Clause Matching]
  HX --> HX2[Behavioral and Frequency Signals]
  RAG --> AGENTS[Agent Debate]
  HX2 --> AGENTS
  AGENTS --> OUT[Verdict, Risk Score, Fraud Probability, PDF Report]
```

## 🧠 Detailed Data Flow

1. A user signs in and receives a JWT session token.
2. The UI submits the claim package to the backend through multipart upload.
3. The upload handler validates file size, type, and claim completeness.
4. Files are stored under a claim-specific directory for traceability.
5. Text extraction runs across claim, invoice, policy, and evidence inputs.
6. Structured extraction converts unstructured text into normalized JSON payloads.
7. Policy retrieval finds the most relevant contract excerpts for the current claim.
8. The agent graph generates two competing arguments and a mediator conclusion.
9. Fraud, anomaly, and risk scorers convert the raw signals into reviewable scores.
10. A report is rendered to PDF and linked back to the claim record.
11. The frontend refreshes status, logs, and downloadable report state.
12. The result stays auditable in PostgreSQL for later review and reporting.

```mermaid
flowchart TB
  U[User] --> UI[Web UI]
  UI --> UP[Upload Claim Package]
  UP --> VAL[Validate Input]
  VAL --> FS[Persist Files]
  FS --> TXT[Extract Text]
  TXT --> JSON[Structure Data]
  JSON --> RET[Retrieve Policy Evidence]
  RET --> DEC[Agent Decision Making]
  DEC --> RISK[Fraud + Risk Scoring]
  RISK --> REP[Generate PDF Report]
  RISK --> DB[(PostgreSQL)]
  REP --> UI
  DB --> UI
```

For the full technical deep dive, see [MULTI_AGENT_ARCHITECTURE.md](MULTI_AGENT_ARCHITECTURE.md).

## 🕵️ Fraud Detection Architecture

The README already mentions fraud scoring at a high level. This section adds the dedicated fraud-detection pipeline and shows how it fits inside the broader claim review flow.

```mermaid
flowchart TB
  INPUT[Claim Data Input] --> CLAIM[Claim Data]
  INPUT --> MARKET[Market Data & Vendor]
  INPUT --> HISTORY[Historical Claims]

  CLAIM --> ENGINE[FraudDetectionEngine]
  MARKET --> ENGINE
  HISTORY --> ENGINE

  ENGINE --> PATTERN[PatternRecognizer]
  ENGINE --> ANOMALY[AnomalyDetector]
  ENGINE --> RISK[RiskScorer]

  PATTERN --> SIGNALS[Fraud Signal List]
  ANOMALY --> SIGNALS
  RISK --> SIGNALS

  SIGNALS --> RESULT[FraudDetectionResult]
```

### Fraud detection components

| Component | Role | Output |
|---|---|---|
| FraudDetectionEngine | Coordinates the full fraud-analysis pipeline | Combined fraud decision output |
| PatternRecognizer | Detects rule-based fraud patterns | Linked claims, timing anomalies, vendor red flags |
| AnomalyDetector | Finds statistical outliers in claim features | Anomaly score and anomaly flag |
| RiskScorer | Combines signals into a final score | Risk score and fraud probability |
| Fraud Signal List | Stores all detected indicators | Typed fraud signals with severity and confidence |
| FraudDetectionResult | Final fraud analysis record | Verdict, risk score, fraud probability, signals |

### What this layer does

- Compares claim values against invoices, market data, and historical behavior.
- Flags suspicious timing, repeated claims, inflated estimates, and vendor issues.
- Converts raw evidence into a consistent fraud probability and risk score.
- Feeds the final scoring output back into the judge and report generation path.

## 🛠 Tech Stack

### 🎨 Frontend Stack

| Component | Technology | Purpose |
|---|---|---|
| UI Framework | React 18 | Browser interface for adjusters and reviewers |
| Language | TypeScript | Typed UI logic and safer refactors |
| Build Tool | Vite | Fast local development and production builds |
| Routing | React Router DOM | Auth-gated navigation and page routing |

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
| PDF Generation | ReportLab | Final claim report rendering |

### 🤖 AI, Retrieval, and Agent Stack

| Component | Technology | Purpose |
|---|---|---|
| LLM Provider | Google Generative AI | Extraction and agent reasoning support |
| Prompt Utilities | LangChain Core | Prompt and chain utilities |
| Integrations | LangChain Community | Additional integrations and helpers |
| Orchestration | LangGraph | Multi-step agent workflow orchestration |
| Retrieval | RAG service | Policy snippet matching and context retrieval |

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
- `app/api/claims.py`: handles uploads, processing, status, claim retrieval, comparison, and PDF download.
- `app/services/document_parser.py`: extracts text from different file types.
- `app/services/extraction.py`: converts raw text into structured claim data.
- `app/services/rag_service.py`: retrieves policy excerpts relevant to the current case.
- `app/agents/graph.py`: runs the approve/reject/mediator workflow.
- `app/services/risk_scoring.py`: turns mediator output into risk and fraud scores.
- `app/services/report_pdf.py`: renders the final PDF report.

## 🚪 API Surface

### Authentication

- `POST /api/auth/login` - log in with the demo or configured user.
- `GET /api/auth/me` - return the authenticated user profile.

### Claims

- `POST /api/upload-claim` - upload claim, invoice, policy, and evidence files.
- `POST /api/claims/{claim_id}/process` - start async analysis.
- `GET /api/claims` - list recent claims.
- `GET /api/claims/{claim_id}` - fetch full claim details.
- `GET /api/claims/{claim_id}/status` - retrieve processing state and logs.
- `GET /api/claims/{claim_id}/pdf` - download the generated report.
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

## 🧭 How the Claim Processing Pipeline Works

1. Upload documents through the API or web UI.
2. Store the files and create a claim record.
3. Extract text from claim, invoice, policy, and evidence documents.
4. Convert each source into structured data.
5. Retrieve policy snippets relevant to the claim scenario.
6. Run the multi-agent debate:
   - approve argument
   - reject argument
   - mediator decision support
7. Compute fraud and risk indicators.
8. Generate the final PDF report.
9. Update the claim status and expose the result to the UI.

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
