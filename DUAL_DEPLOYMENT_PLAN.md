# Dual-Deployment Implementation Plan — Cloud SaaS + Self-Hosted

This plan adds **two first-class deployment models** to NexusCore without forking the
codebase:

- ☁️ **Cloud-Managed SaaS** — central brain on Render + dashboard on Vercel, remote
  machines stream telemetry up via a lightweight client daemon. (`DEPLOYMENT_MODE=cloud`)
- 💻 **Self-Hosted / On-Premise** — the whole stack runs locally via `docker-compose up`,
  with ChromaDB replacing Pinecone and the backend driving the host Docker daemon for real
  sandboxing. (`DEPLOYMENT_MODE=local`)

**Locked decisions (from kickoff):**
- **Hybrid isolation** for local mode: swap Pinecone → ChromaDB, but keep **Gemini
  embeddings (3072-dim) + OpenRouter LLM**. Local mode therefore still needs internet and
  the Gemini/OpenRouter keys. "Local data store, cloud brain." No embedding-dimension swap.
- **Namespace-scoped API keys** for SaaS: `nx_core_...` keys stored in Supabase, each tied
  to a namespace. No user accounts / login.

---

## What already exists (do NOT rebuild — extend)

| Capability | Status | File |
| --- | --- | --- |
| API-key auth dependency | ✅ exists (single shared key, `Authorization: Bearer`) | [auth.py](backend/app/security/auth.py) |
| GitHub `git clone --depth 1` ingest | ✅ exists | [ingest.py:147](backend/app/api/v1/ingest.py#L147) |
| ZIP upload ingest | ✅ exists | [ingest.py:102](backend/app/api/v1/ingest.py#L102) |
| Local-directory ingest | ✅ exists | [ingest.py:25](backend/app/api/v1/ingest.py#L25) |
| Dual-mode sandbox (subprocess/docker) | ✅ exists | [sandbox.py](backend/app/services/sandbox.py) |
| Local psutil telemetry loop | ✅ exists (host-local only) | [telemetry.py](backend/app/anomaly/telemetry.py) |
| Supabase async ledger + pool | ✅ exists | [ledger.py](backend/app/services/ledger.py) |

The work below is mostly **factory-izing what's hardcoded** (Pinecone, single key,
host-local telemetry) and **adding the two missing pieces**: the ChromaDB backend +
compose stack, and the remote telemetry daemon + ingest webhook.

---

## 📋 Plan Overview

```
Phase 0: Deployment-Mode Foundation
  0.1 DEPLOYMENT_MODE setting + derived flags
  0.2 Vectorstore factory (provider-agnostic interface)
  0.3 Runtime mode endpoint for the frontend

Phase 1: Self-Hosted / On-Premise (Model 2)
  1.1 ChromaDB vectorstore adapter (Gemini embeddings, 3072-dim)
  1.2 Backend Dockerfile
  1.3 Frontend Dockerfile (Next.js standalone)
  1.4 docker-compose.yml (frontend + backend + chromadb + docker.sock)
  1.5 Docker-socket sandbox wiring (the bind-mount gotcha)
  1.6 Frontend feature toggling + local-path ingest tab

Phase 2: Cloud-Managed SaaS (Model 1)
  2.1 API-key table + key service (generate/validate nx_core_)
  2.2 Auth middleware upgrade (namespace-scoped, backward compatible)
  2.3 Key-generation endpoint + Settings/onboarding UI
  2.4 Telemetry ingest webhook (receive remote metrics)
  2.5 Client daemon (telemetry.py) + onboarding command UI
  2.6 Sandbox "Simulated" status on Render (Docker unavailable)

Phase 3: Unified Docs & Hardening
  3.1 Dual-track README (the "sorting hat")
  3.2 Env templates + Render/Vercel config split
  3.3 Tests: factory, key auth, webhook, compose smoke

Total: 4 phases, 18 sub-phases
```

---

## Phase 0 — Deployment-Mode Foundation

The single switch the rest of the plan hangs off. Nothing user-visible yet; this makes the
backend mode-aware so 1.x and 2.x can branch cleanly.

### 0.1 — `DEPLOYMENT_MODE` setting + derived flags
- **Modify** [config.py](backend/app/core/config.py): add `deployment_mode: str = "cloud"`
  (`"cloud" | "local"`) and ChromaDB connection fields (`chroma_host`, `chroma_port=8000`,
  `chroma_collection_prefix`). Add a `field_validator` that lowercases/validates the mode.
- **Decision:** make `pinecone_api_key` **optional when `deployment_mode == "local"`** — it's
  currently `Field(...)` (required) and will hard-fail a local boot that has no Pinecone key.
  Use a model validator: require `pinecone_api_key` only in cloud mode, require
  `chroma_host` only in local mode. This is the one change that unblocks `docker-compose up`
  with zero Pinecone account.
- Add convenience props `is_cloud`/`is_local` for readable branching.

### 0.2 — Vectorstore factory (provider-agnostic interface)
- **Modify** [vectorstore.py](backend/app/services/vectorstore.py): extract the public
  surface the app already uses — `aupsert_documents`, `asearch`, `aget_unique_files` — into a
  small `VectorStore` Protocol/ABC. Rename the current class to `PineconeVectorStore­Service`
  (keep behaviour identical).
- **Modify** `get_vectorstore_service()` into the **factory**: return the Pinecone impl in
  cloud mode, the Chroma impl (Phase 1.1) in local mode. Keep the existing singleton caching.
- **Decision:** the `pc_client` arg currently threaded from `app.state.pinecone` becomes
  optional/ignored in local mode. Callers ([ingest.py](backend/app/api/v1/ingest.py),
  [context_node.py](backend/app/graph/nodes/context_node.py)) don't change — they already call
  the factory with no args in most paths.

### 0.3 — Runtime mode endpoint for the frontend
- **Modify** [health.py](backend/app/api/v1/health.py) or add a `system.py` router:
  `GET /api/v1/system/mode` → `{ "deployment_mode": "...", "features": { "api_keys": bool,
  "local_ingest": bool } }`. **No auth** (frontend needs it pre-key).
- **Why a runtime endpoint, not a build-time env:** Vercel builds in the cloud and the
  docker-compose frontend builds locally, but feature toggling must follow the *backend* it's
  talking to. Frontend asks the backend what mode it's in. There's already an untracked
  `frontend/src/lib/systemClient.ts` — wire it here.

---

## Phase 1 — Self-Hosted / On-Premise (Model 2)

### 1.1 — ChromaDB vectorstore adapter
- **Create** `backend/app/services/vectorstore_chroma.py`: `ChromaVectorStoreService`
  implementing the Phase 0.2 interface, backed by `langchain-chroma`'s `Chroma` wrapper
  against an `HttpClient(host=settings.chroma_host, port=settings.chroma_port)`.
- **Reuse** `get_embeddings()` unchanged — Gemini, 3072-dim. (Hybrid decision: Chroma stores
  the same vectors Pinecone would; no dimension change, no re-embedding logic.)
- **Decision — namespaces → collections:** Pinecone uses per-call `namespace`; Chroma binds a
  `collection_name` at construction. Map each namespace to a collection
  (`{prefix}{namespace or "default"}`) and cache one `Chroma` handle per collection. `asearch`
  / `aupsert_documents` / `aget_unique_files` select the collection from the `namespace` arg so
  the call sites stay identical.
- **Add deps** to [requirements.txt](backend/requirements.txt): `langchain-chroma`,
  `chromadb` (client only — server runs as its own container).

### 1.2 — Backend Dockerfile
- **Create** `backend/Dockerfile`: `python:3.10-slim`, install `git` (the GitHub ingest
  shells out to `git clone`) and the Docker CLI is **not** needed (we use the Python SDK over
  the mounted socket). `pip install -r requirements.txt`, copy `app/`, run
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Decision:** keep `requirements-dev.txt` (ragas/datasets) **out** of the runtime image to
  keep it lean; those are eval-only.

### 1.3 — Frontend Dockerfile
- **Create** `frontend/Dockerfile`: multi-stage Next.js build. **Heads-up:**
  [frontend/AGENTS.md](frontend/AGENTS.md) warns this Next.js has breaking changes — read
  `node_modules/next/dist/docs/` and confirm `output: "standalone"` is set in
  [next.config.ts](frontend/next.config.ts) before relying on the standalone server output.
- `NEXT_PUBLIC_API_BASE_URL` must point at the compose backend service
  (`http://localhost:8000` from the browser, since the browser is on the host).

### 1.4 — `docker-compose.yml`
- **Create** at repo root. Three services:
  - `frontend` → builds `frontend/`, maps `3000:3000`.
  - `backend` → builds `backend/`, maps `8000:8000`, env `DEPLOYMENT_MODE=local`,
    `SANDBOX_MODE=docker`, `CHROMA_HOST=chromadb`, plus `GEMINI_API_KEY` / `OPENROUTER_API_KEY`
    / optional `SUPABASE_DB_URL` from a root `.env`. **Mounts
    `/var/run/docker.sock:/var/run/docker.sock`** so the backend drives the host daemon.
  - `chromadb` → official `chromadb/chroma` image, named volume for persistence, port `8000`
    exposed **only inside the compose network** (backend reaches it at `chromadb:8000`; no host
    port-map needed, avoiding the clash with the backend's own 8000).
- **Decision:** a shared named volume `sandbox_workspaces` mounted into the backend — see 1.5
  for why this is mandatory, not optional.

### 1.5 — Docker-socket sandbox wiring (the bind-mount gotcha)
- **Modify** [sandbox.py](backend/app/services/sandbox.py) `_run_docker_sandbox`:
- **The real problem the brief misses:** when the backend runs *inside* a container and mounts
  the host's `docker.sock`, `client.containers.run(volumes={temp_dir: ...})` is resolved by the
  **host** daemon, not the backend container. `temp_dir` (e.g. `/tmp/nexus_sandbox_x`) exists in
  the backend container's FS, not on the host, so the sibling container mounts an **empty
  directory** and every patch "fails." This is the #1 thing that will silently break Model 2.
- **Fix:** write sandbox scratch dirs into the **shared named volume** from 1.4 (e.g.
  `/sandbox/...`), which is a real host-backed volume both the backend and the sibling
  container can see. Pass the volume — not an ephemeral container path — to `volumes=`.
  Alternatively, stream the code in via `put_archive` (tar over the socket) and avoid bind
  mounts entirely; note both options, recommend the named volume for simplicity.
- Local-directory ingest (`POST /ingest`) already works on-prem; it just needs the mounted
  workspace path (e.g. `/app/workspace`) to be readable — document the mount in 1.4.

### 1.6 — Frontend feature toggling + local-path ingest tab
- **Modify** [IngestPanel.tsx](frontend/src/components/IngestPanel.tsx): when
  `GET /system/mode` reports `local`, show a **"Local Path"** tab (absolute path → existing
  `POST /ingest`) and keep GitHub/ZIP. When `cloud`, keep GitHub/ZIP only (current behaviour).
- **Modify** page/settings: hide the API-key modal (Phase 2.3) entirely in local mode — local
  orchestration needs no key. Drive this off the `features` flags from 0.3.

---

## Phase 2 — Cloud-Managed SaaS (Model 1)

### 2.1 — API-key table + key service
- **Modify** [ledger.py](backend/app/services/ledger.py) (or new `services/api_keys.py` reusing
  the pool): add an idempotent `api_keys` table — `id`, `key_hash` (store a SHA-256 **hash**,
  never the raw key), `namespace`, `label`, `created_at`, `revoked` bool, `last_used_at`.
- **Create** `backend/app/services/api_keys.py`: `generate_key()` →
  `nx_core_<token_urlsafe(32)>`, returns the raw key **once** + persists the hash;
  `resolve_key(raw) -> namespace | None` (hash + lookup, updates `last_used_at`).
- **Decision:** namespace-scoped, no accounts (per kickoff). The key *is* the tenant boundary —
  it maps 1:1 to a Pinecone namespace, so an authenticated request is automatically scoped.

### 2.2 — Auth middleware upgrade (backward compatible)
- **Modify** [auth.py](backend/app/security/auth.py) `verify_api_key`: keep accepting the legacy
  shared `nexus_api_key` (dev/local), AND accept `nx_core_` keys by looking them up via 2.1.
  Return the resolved **namespace** (or `None`/`"default"` for the legacy key) so handlers can
  scope ingestion/telemetry automatically.
- **Decision:** change the dependency's return type from `str` (the key) to a small
  `AuthContext { namespace }`. Audit call sites in [ingest.py](backend/app/api/v1/ingest.py),
  [graph.py](backend/app/api/v1/graph.py), [context.py](backend/app/api/v1/context.py) — most
  use `Depends(verify_api_key)` purely as a gate and won't need the return value.
- Keep `verify_webhook_signature` as-is; it's a separate HMAC path.

### 2.3 — Key-generation endpoint + Settings/onboarding UI
- **Create** `POST /api/v1/keys` (generate, returns raw key once) and `GET /api/v1/keys`
  (list labels/namespaces, never raw). Gate behind the legacy admin key for now.
- **Frontend:** add a **Settings tab → "API Keys"** modal that calls these, shows the key once
  with a copy button, and an **Onboarding** card that renders the exact one-liner to run the
  daemon (Phase 2.5), pre-filled with the new key and the Render URL.
- **Decision:** only render this in `cloud` mode (0.3 flags). Untracked
  `frontend/src/lib/systemClient.ts` / `contextClient.ts` suggest this UI layer is already being
  scaffolded — extend, don't duplicate.

### 2.4 — Telemetry ingest webhook (the missing inbound path)
- **Create** `POST /api/v1/telemetry/ingest` (auth via 2.2): body
  `{ cpu, mem, error_rate, logs[] }`. Resolve namespace from the key, feed a **per-namespace**
  `AnomalyDetector`, and on anomaly fire `execute_repair(..., event_source="daemon/telemetry")`
  exactly like the local loop does today.
- **Modify** [telemetry.py](backend/app/anomaly/telemetry.py): the detector is currently a
  module-global singleton tuned for one host. For SaaS, maintain a `dict[namespace ->
  AnomalyDetector]` so tenants don't pollute each other's baselines. Reuse
  [detector.py](backend/app/anomaly/detector.py) unchanged.
- **Decision:** this endpoint is the cloud counterpart to the in-process loop. In local mode the
  in-process loop still runs; in cloud mode the loop stays off (`ENABLE_TELEMETRY_LOOP=false`)
  and metrics arrive via this webhook instead.

### 2.5 — Client daemon (`telemetry.py`)
- **Create** `clients/nexus_daemon.py` (~50–70 lines): `psutil` + `requests`, args
  `--api-key` and `--server-url`, loops every 5s POSTing the metrics payload + tailing a log
  file (`--log-file`) to `/api/v1/telemetry/ingest` with `Authorization: Bearer nx_core_...`.
  Graceful backoff on network errors; minimal deps so users can `pip install psutil requests`
  and run it.
- **Create** `clients/requirements.txt` (just `psutil`, `requests`) and a short README.
- **Decision:** keep it dependency-light and single-file so the onboarding "one-liner"
  (`curl ... | python -`) is realistic.

### 2.6 — Sandbox "Simulated" status on Render
- **Modify** [sandbox.py](backend/app/services/sandbox.py) + the arbitration/sandbox node:
  Render free tier blocks Docker-in-Docker. When `SANDBOX_MODE=docker` but the daemon is
  unreachable, **don't return a hard failure** — fall back to subprocess, tag the result
  `status="simulated"`, and let the **Dual-Model Security Arbitration**
  ([arbitration_node.py](backend/app/graph/nodes/arbitration_node.py)) be the gate that
  validates the patch. Surface `simulated: true` in the SSE stream so the UI can badge it.
- **Decision / honesty flag:** "simulated" means the patch ran in a plain subprocess on the
  Render box (no real isolation, has network). Document this clearly — it's a known free-tier
  trade-off, and it's exactly why Model 2 (real Docker sandbox) is the "secure" track.

---

## Phase 3 — Unified Docs & Hardening

### 3.1 — Dual-track README ("sorting hat")
- **Modify** [README.md](README.md): add the comparison table (Cloud-Managed vs Self-Hosted),
  the live Vercel/Render URLs + daemon one-liner for SaaS, and the `git clone` → `.env` →
  `docker-compose up -d` flow for on-prem.

### 3.2 — Env templates + Render/Vercel config split
- **Modify** [.env.example](backend/.env.example): document `DEPLOYMENT_MODE`,
  `CHROMA_HOST/PORT`, `SANDBOX_MODE`, and which keys each mode requires (cloud: Pinecone+Gemini+
  OpenRouter+Supabase; local: Gemini+OpenRouter, Pinecone optional).
- **Create** root `.env.example` for compose. Note Render's `runtime.txt` / spin-down behaviour.

### 3.3 — Tests
- **Modify/Create** [tests/](backend/tests/): factory returns correct backend per mode; Chroma
  adapter round-trips upsert→search (mark `@pytest.mark.integration`, needs a running chroma);
  `nx_core_` key generate→resolve→revoke; telemetry webhook auth + anomaly trigger (mock
  `execute_repair`); compose smoke (build + `/health`). Extend
  [conftest.py](backend/tests/conftest.py) with a `deployment_mode` fixture.
Key decisions

Use asyncio test utilities (pytest-asyncio) for async endpoints.
Mock external services (Docker, Pinecone, Gemini) where appropriate to keep CI fast.
Mark Chroma integration tests with the integration marker so they can be run optionally.

---

## Cross-cutting risks to keep visible during implementation

1. **Local mode still needs internet + Gemini/OpenRouter keys** (hybrid decision). If anyone
   markets Model 2 as "air-gapped," that's false until a future phase adds Ollama + local
   embeddings (deliberately out of scope here).
2. **Render free tier:** 512MB RAM is tight for the ML deps (pyod/sklearn/langchain); watch for
   OOM on build/boot. Services sleep after ~15 min idle (~50s cold start) — the 5s daemon ping
   keeps it warm but burns the 750 free instance-hours/month.
3. **The DinD bind-mount gotcha (1.5)** is the single most likely silent failure. Validate the
   shared-volume path end-to-end before declaring the on-prem sandbox "working."
4. **Key return-type change (2.2)** ripples to every `Depends(verify_api_key)` call site — do
   the audit in 2.2, not later.

---

### Suggested starting point

Phase 0 is the keystone — nothing else compiles cleanly without the mode switch and the
factory. Recommend **starting at 0.1**, then 0.2/0.3, then choosing whichever model you want
to demo first (Model 2 / Phase 1 is more self-contained and offline-demoable;
Model 1 / Phase 2 reuses more of what already exists).

Which phase/sub-phase should we start with? Or should I begin from the top (0.1)?
