# NexusCore SRE

NexusCore SRE is an autonomous DevSecOps agent built with LangGraph, FastAPI, and Next.js. It detects system anomalies, retrieves relevant codebase context via Pinecone (Agentic RAG), synthesizes self-healing patches using Google Gemini, and securely tests them inside isolated Docker sandboxes before deployment.

## Architecture Highlights
- **Stateful Ledger**: Asynchronous Postgres logging (Supabase) for compliance tracking.
- **Agentic RAG**: AST-aware semantic chunking into Pinecone Vector DB.
- **Cyclic LangGraph**: `Evaluation → Context → Modification → Arbitration → Sandbox`.
- **Docker Isolation**: Hardened container execution (`128MB RAM`, `network_mode="none"`) for safe testing.
- **Real-Time Dashboards**: Next.js Server-Sent Events (SSE) streaming UI.

## Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Docker Desktop** (CRITICAL: Must be running for the agent to safely execute code sandboxes).
- **API Keys**: Google Gemini API, Pinecone API, and a Supabase Postgres URL.

## Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy the env template and add your keys
cp .env.example .env

# Run the API
uvicorn app.main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install

# Copy the env template
cp .env.local.example .env.local

# Run the dashboard
npm run dev
```

Visit `http://localhost:3000` to access the real-time SRE Dashboard.

## Deployment Options

| Mode | Frontend URL | Backend URL | Key Requirements | Onboarding |
|------|--------------|------------|------------------|------------|
| **Cloud‑Managed SaaS** | https://nexuscore-dashboard.vercel.app | https://nexuscore-api.onrender.com | Gemini, Pinecone, Supabase, OpenRouter | `curl https://nexuscore-onrender.com/daemon.sh | python - --api-key <YOUR_nx_core_KEY>` |
| **Self‑Hosted / On‑Premise** | http://localhost:3000 (after `docker‑compose up`) | http://localhost:8000 | Gemini, OpenRouter (Pinecone optional) | `git clone <repo> && cp .env.example .env && docker‑compose up -d` |

**How it works**
- **Cloud‑Managed** runs the FastAPI backend on Render and the Next.js UI on Vercel. The daemon (`telemetry.py`) posts metrics to `/api/v1/telemetry/ingest` using the SaaS API key.
- **Self‑Hosted** runs the entire stack locally via Docker Compose. The backend talks to a local Chroma vector store and uses the host Docker daemon for sandboxed execution.

> Choose the mode that fits your security and operational needs. The rest of the codebase is shared; only the vector‑store provider and deployment scripts differ.
