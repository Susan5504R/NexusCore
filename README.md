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
