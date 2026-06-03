# Nexus-Core — Implementation Plan

> Autonomous SRE & infrastructure-orchestration framework: a stateful, cyclic LangGraph
> of specialized AI agents that observe logs, synthesize codebase context via Agentic RAG,
> and execute deterministic repairs inside isolated Docker sandboxes.

This plan is a **guide, not a script** (per `plan-driven-dev`). Code snippets show intent and
structure; the real implementation must be clean, integrated, and working. Each sub-phase is
implemented only after its Pre-Implementation Brief is approved.

---

## Target Architecture & Layout

```
backend/
  app/
    main.py                  # FastAPI app: lifespan, router includes, CORS
    core/
      config.py              # pydantic-settings Settings (env vars, fail-fast)
      schemas.py             # AgentState TypedDict + Pydantic request/response models
      logging.py             # structured JSON logging
    services/
      llm.py                 # Gemini 1.5 Flash chat wrapper (async, streaming)
      embeddings.py          # Google AI Studio embedding wrapper
      vectorstore.py         # Pinecone serverless client + index lifecycle
      ingestion.py           # code-aware chunking + upsert pipeline
      sandbox.py             # Docker SDK ephemeral, network-isolated runner
      ledger.py              # operational_logs writer (Supabase/Postgres, async)
    graph/
      nodes/
        context_node.py      # RAG context retrieval node
        modification_node.py # code/patch generation node
        sandbox_node.py      # Docker execution-verification node
        security_node.py     # guardrail: blocklist + dual-model arbitration
        evaluation_node.py   # entry evaluation / triage node
      routing.py             # conditional edge logic (route_execution)
      orchestrator.py        # create_sre_orchestrator() graph assembly
    api/v1/
      health.py              # GET /api/v1/health
      ingest.py              # POST /api/v1/ingest
      context.py             # POST /api/v1/context/query (streamed inference)
      graph.py               # POST /api/v1/graph/run + GET SSE state stream
    anomaly/
      telemetry.py           # streaming metric sampler (CPU, net, log-error freq)
      detector.py            # PyOD Isolation Forest anomaly scoring
      trigger.py             # async internal trigger -> graph run
    security/
      blocklist.py           # absolute blocklist regex validation
      arbitrator.py          # secondary zero-temp model security assessment
    eval/
      ragas_suite.py         # detached Ragas faithfulness + context-recall script
  requirements.txt
  .env
frontend/                    # Next.js 14 (app router) + Tailwind
  app/, components/, lib/    # SSE log window + real-time state visualization
demo/
  buggy_server.py            # dummy crashable web server for the E2E self-healing demo
```

**Dependency additions** (current `requirements.txt` is missing these — added in Phase 0.1):
`pydantic-settings`, `sse-starlette`, `google-generativeai`, `docker`, `pyod`, `numpy`,
`scikit-learn`, `psutil`, `supabase` (or `asyncpg`), `ragas`, `datasets`, `httpx`,
`uvicorn[standard]`, `langchain-pinecone`.

**Cross-cutting invariants** (Operational Validation Checklist):
1. **Isolated execution** — AI-generated code only ever runs inside Docker, never on the host.
2. **Async everywhere** — all model calls, file I/O, and DB writes are non-blocking.
3. **Bounded cost/latency** — every graph run terminates gracefully on retry/depth thresholds.

---

## Phase 0 — Scaffolding & Foundations

### 0.1 Dependencies, configuration & settings
Pin the full dependency set; build a `Settings` object (pydantic-settings) that loads and
validates all env vars at startup (fail fast on missing keys). Centralize model names,
Pinecone index/region, Docker image, resource limits, and thresholds.

### 0.2 Core schemas & shared types
Implement `AgentState` (TypedDict, exactly the spec schema with `operator.add`-annotated
`messages`) plus Pydantic request/response models for every endpoint. Single source of truth
for shapes used across services and graph nodes.

### 0.3 FastAPI app skeleton, logging & health
`main.py` with lifespan (init Pinecone client, Docker client, ledger pool; clean shutdown),
structured JSON logging, CORS for the Next.js UI, router registration, and a health endpoint
that reports dependency readiness.

### 0.4 Operational ledger (Supabase / PostgreSQL)
Create the `operational_logs` table (provided DDL) and an async writer service that records
every agent action: source, action, payload, status, token consumption, latency, ragas score.
Used by all nodes and the anomaly trigger.

---

## Phase 1 — Context Synthesis Foundation (The Core Brain)

### 1.1 Code-aware ingestion & chunking
Async pipeline that walks a target codebase (respecting `.gitignore` via `pathspec`), detects
language, and splits with `RecursiveCharacterTextSplitter.from_language` to preserve class/
function structure. **No** static window splitting. Emits chunks with metadata (path, language,
start/end). Intent:

```python
splitter = RecursiveCharacterTextSplitter.from_language(
    language=detected_language, chunk_size=1200, chunk_overlap=150
)
chunks = splitter.create_documents([source_text], metadatas=[{"path": rel_path, ...}])
```

### 1.2 Embeddings + Pinecone vectorstore service
Google AI Studio embedding wrapper (async batched) and a Pinecone serverless service that
ensures the index exists (cosine metric, correct dimension), upserts vectors with metadata,
and runs similarity queries. Cosine similarity is the proximity metric.

### 1.3 Ingestion endpoint — `POST /api/v1/ingest`
Wire 1.1 + 1.2 behind an endpoint that accepts a directory path (or upload), chunks, embeds,
and upserts; returns counts and timing. Logs to the ledger.

### 1.4 Baseline retrieval loop — `POST /api/v1/context/query`
Accept a raw prompt → embed it → cosine similarity search in Pinecone → assemble a context
window → **stream** Gemini inference back to the caller (`sse-starlette` / streaming response).
This is the foundational RAG loop reused by the graph's context node.

---

## Phase 2 — Autonomous Edge Routing & Sandboxed Operations (The Core Hands)

### 2.1 Docker SDK sandbox tool
Ephemeral container runner: `python:3.10-slim`, `network_mode="none"`, `mem_limit="128m"`,
`nano_cpus=500_000_000`, `remove=True`, hard timeout. Returns `(exit_code, stdout, stderr)`.
Runs in a thread executor so it never blocks the event loop. Host never executes AI code.

### 2.2 LangGraph nodes
Implement the four async nodes operating on `AgentState`:
- **evaluation_node** — triage incoming logs/target, seed state.
- **context_retrieval node** — reuse the 1.4 RAG loop to populate context.
- **code_modification node** — Gemini generates a patch from context + stderr.
- **sandbox_verification node** — run patch via 2.1, capture exit code + stderr into state.

### 2.3 Conditional routing & self-correction
`route_execution`: if no security clearance → END; if exit code == 0 → END; if
`retry_count >= 3` → END; else increment retry, route back to modification. Assemble the graph
with `create_sre_orchestrator()` matching the provided lifecycle template.

### 2.4 Graph execution endpoint + SSE state stream
`POST /api/v1/graph/run` to launch a run; stream `AgentState` deltas (active node, retry count,
token spend, exit codes) over SSE so the UI can visualize the cyclic loop live.

---

## Phase 3 — Advanced Portfolio Integration

### 3.1 Proactive anomaly isolation (PyOD Isolation Forest)
Background telemetry sampler (CPU load, network throughput, log-error frequency) feeding a PyOD
Isolation Forest that computes anomaly indices `s(x,n)=2^(-E(h(x))/c(n))` against a contamination
threshold.

### 3.2 Autonomous trigger
When the anomaly index crosses threshold, bypass user hooks and fire an async **internal**
FastAPI event that launches a graph run seeded with the offending logs — the self-healing
heartbeat.

### 3.3 Command validation blocklist
Absolute blocklist regex layer rejecting escape strings, destructive/unapproved modifications
(e.g. `rm -rf`), and credential-retrieval attempts before any sandbox execution.

### 3.4 Dual-model arbitration (Guardrail node)
Secondary lightweight model (zero-temperature security assessment). On negative verification,
force `security_clearance=False` and route to a hard termination node. Wire blocklist +
arbitration into `security_node` inside the graph.

---

## Phase 4 — Verification, Evaluation & Dashboards

### 4.1 Ragas evaluation suite
Detached script computing **Faithfulness** (patches rely strictly on retrieved snippets) and
**Context Recall** (ingestion pulled all relevant sources) across test splits; persists
`ragas_fidelity_score` to the ledger.

### 4.2 Next.js 14 + Tailwind scaffold + SSE client
App-router frontend with a typed SSE client hook consuming the graph state stream.

### 4.3 Streaming log window + state visualization
Terminal-style streaming execution log + real-time panel: active node tracking, resource
utilization, and token-expenditure counts per run.

### 4.4 End-to-end self-healing demo
`demo/buggy_server.py` that can be crashed on purpose; verify the full loop: crash → anomaly
detection → autonomous trigger → RAG → patch → Docker test → verified fix.

---

## Phase 5 — Bring Your Own Code (BYOC)

> Closes the gap between "impressive demo" and "fixes *my* project." Phases 0–4 proved the
> autonomous loop on a single hardcoded file (`buggy_server.py`). Phase 5 makes the system
> operate on a user's real Python project, end to end, through the UI. Intake starts with the
> simplest option (local path); upload and Git-URL intake, plus multi-language fixing, are
> deferred to Phase 6 (post-deployment).

**Design decisions (locked):**
- Intake order: **local path first**, then upload, then Git URL (Phase 6).
- Fix scope: **Python-first but project-faithful** now; multi-language later (Phase 6).
- Nothing in Phase 5 is exposed without auth (5.5) — it executes user-supplied code.

### 5.1 Ingest UI + wired local-path intake
Frontend "Ingest Project" panel (directory path + optional namespace) calling the existing
`POST /api/v1/ingest`, showing files processed / chunks indexed. Confirm the endpoint returns
`IngestResponse` cleanly and threads `namespace` through to Pinecone. *Unblocks using your own
code at all — the smallest, highest-leverage step.*

### 5.2 Run form — target file + logs + repro command (replaces the hardcoded button)
Replace `handleTrigger`'s fixed payload with a real form: pick the target file (from the
ingested set), paste the crash logs, and supply the **reproduction command** (e.g.
`python server.py`). Add a small backend endpoint to list ingested files per namespace for the
picker. The repro command is what makes 5.3 faithful.

### 5.3 Project-faithful Python sandbox
Stop running synthetic standalone snippets. Mount the user's project into the container,
install dependencies (`requirements.txt` if present), and run the **actual repro command** to
reproduce the real failure — capturing real exit code + stderr. Extend `AgentState` / the run
request to carry the project path and repro command. Keep the hard resource + network limits.

### 5.4 Whole-file patching + apply + re-verify + rollback
Modification node reads the **real target file** and proposes a corrected version (diff against
real content, not a from-scratch script). A new apply/verify node writes the patch into a
working copy, re-runs the repro in the sandbox, and keeps the change only if it passes;
otherwise rolls back. This finally makes "deploy the fix" true.

### 5.5 Auth & safety hardening
- [x] Basic rate limiting on SRE endpoints
- [x] API-key/JWT auth on all endpoints
- [x] HMAC webhook signature verification for anomaly triggers

---

## Phase 6 — Post-Deployment Extensions (deferred)

Built only after Phase 5 ships and is stable.

### 6.1 Upload intake
Browser file/zip upload → unpack to a temp dir → ingest → cleanup.

### 6.2 Git-URL intake
Paste a Git URL → clone → ingest → run real repro. Adds clone/auth/secret handling.

### 6.3 Multi-language, real project
Generalize the patcher + sandbox beyond Python: per-language build/install/run strategies,
driven by the language already detected at ingestion time.

---

## Plan Summary

- **Phase 0** Scaffolding & Foundations — 4 sub-phases ✅
- **Phase 1** Context Synthesis Foundation — 4 sub-phases ✅
- **Phase 2** Autonomous Edge Routing & Sandbox — 4 sub-phases ✅
- **Phase 3** Advanced Portfolio Integration — 4 sub-phases ✅
- **Phase 4** Verification, Evaluation & Dashboards — 4 sub-phases ✅
- **Phase 5** Bring Your Own Code (BYOC) — 5 sub-phases ----> done
- **Phase 6** Post-Deployment Extensions — 3 sub-phases (deferred)

Phases 0–4 are built; Phase 5 turns the demo into a tool that fixes the user's own Python
projects. Phase 6 broadens intake and language coverage after deployment.
