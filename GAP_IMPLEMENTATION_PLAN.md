# Nexus-Core — Gap-Closure Implementation Plan

> Companion to `IMPLEMENTATION_PLAN.md`. The original plan's 20 sub-phases are
> substantially built, but five gaps keep the system from being *truly* complete:
> the "live" graph view is **simulated**, there is **no real end-to-end SSE
> state stream**, the Ragas suite runs on a **hardcoded mock dataset**, there is
> **no automated test suite**, and the Phase 4 work (`eval/`, `demo/`, `frontend/`)
> is **uncommitted**. This plan closes those gaps.

This plan follows `plan-driven-dev` (`.agent/skills/plan-driven-dev/SKILL.md`):
snippets show **intent**, not copy-paste code. Each sub-phase gets a
Pre-Implementation Brief and is built only after approval, one at a time.

---

## Why these gaps exist (grounding)

Verified against the current codebase:

- `app/api/v1/graph.py` — `/graph/run` is plain request→response (`ainvoke` then
  JSON). No SSE, no per-node deltas. The SSE pattern *does* exist already in
  `app/api/v1/context.py` (`EventSourceResponse` + `astream`), so streaming the
  graph is a natural extension, not new infrastructure.
- `frontend/src/app/page.tsx` — node transitions are faked with `setTimeout`
  (lines 34–47); the real API is fired in the background and its result is shown
  ~10s later regardless of actual progress. No `components/`, no `lib/`, no SSE hook.
- `app/eval/ragas_suite.py` — evaluates a hardcoded `data_samples` dict, not real
  retrieved contexts / real patches. Score extraction (`result.get(...)`) does not
  match the Ragas 0.2.x `EvaluationResult` API.
- `test_nodes.py` / `test_sandbox.py` / `test_vectorstore.py` are manual
  `asyncio.run(main())` scripts needing live Gemini + Docker + Pinecone. `pytest`
  collects **0 tests**.
- `git status` — `app/eval/`, `demo/`, `frontend/` are untracked; the last commit
  claims "Phase 2 and 3 complete" but Phase 4 is on disk only.

**Stack facts that constrain the design:**
- Backend: FastAPI 0.115, LangGraph 0.2.62 (`astream(stream_mode="updates")`
  yields `{node_name: partial_state}`), `sse-starlette` 2.2.1 already installed.
- `AgentState` keys: `messages`, `current_target_file`, `discovered_logs`,
  `proposed_patch`, `execution_exit_code`, `execution_stderr`,
  `security_clearance`, `retry_count`, `telemetry_metrics`.
- Node order: `evaluation_node → context_node → modification_node →
  arbitration_node →(route_security)→ sandbox_node →(route_execution)→ loop/END`.
- Frontend: Next **16.2.7**, React **19**, Tailwind **v4** (CSS `@theme` in
  `globals.css`, no `tailwind.config`), app-router under `src/app`. Theme switches
  via `data-theme` on `<html>`. Native `EventSource` is GET-only.

---

## Cross-cutting invariants (carried over + extended)

1. **Isolated execution** — unchanged; AI code still only runs in Docker.
2. **Async everywhere** — streaming must not block; SSE generators stay async.
3. **Bounded cost/latency** — streaming run honors the same retry/depth caps.
4. **One run path** *(new)* — `/run`, `/run/stream`, the anomaly webhook, and the
   telemetry loop must share a single graph-execution + ledger-logging service, so
   behavior can never drift between trigger sources.
5. **Tests need no secrets** *(new)* — the suite mocks Gemini, Pinecone, Docker,
   and the ledger; it runs offline in CI.

---

## Phase G1 — Real-Time Streaming Backbone (backend)

> Build the genuine SSE state stream first; the frontend depends on it. Mirror the
> existing `context.py` SSE idiom so the codebase stays consistent.

### G1.1 Stream event contract & shared run service
Define the wire shape for graph events once, in `app/core/schemas.py`, and extract
the run/ledger logic out of the endpoint so every trigger reuses it.

- Add a `GraphStreamEvent` model (Pydantic) with a stable, typed shape, e.g.
  `event` (`node_update` | `complete` | `error`), `run_id`, `node`, and a
  `state` delta carrying only UI-relevant fields (`active_node`, `retry_count`,
  `execution_exit_code`, `security_clearance`, `proposed_patch`, latest message).
- Add `app/services/graph_runner.py` with one async function that seeds state,
  invokes the orchestrator, and writes the ledger entry — returning the final
  state. `/graph/run` becomes a thin caller of it.

Intent:
```python
# graph_runner.py
async def execute_repair(app, *, target_file, logs, run_id) -> AgentState:
    state = new_agent_state(current_target_file=target_file, discovered_logs=logs)
    final = await sre_orchestrator.ainvoke(state)
    await _record_ledger(app, run_id, target_file, final, ...)
    return final
```

### G1.2 `POST /api/v1/graph/run/stream` (SSE)
Add a streaming sibling to `/graph/run` that emits one event per node as the graph
advances, then a terminal `complete` event. Keep the existing JSON `/run` intact
(the webhook/background path still uses it via the shared service).

Intent (mirrors `context.py`):
```python
async def event_generator():
    async for update in sre_orchestrator.astream(initial_state, stream_mode="updates"):
        node_name, delta = next(iter(update.items()))
        yield {"event": "node_update",
               "data": GraphStreamEvent.from_delta(run_id, node_name, delta).json()}
    yield {"event": "complete", "data": summary.json()}
return EventSourceResponse(event_generator())
```
Wrap in try/except → emit `{"event": "error", ...}`; write the ledger entry once at
stream end via the G1.1 service helper.

### G1.3 Unify the trigger paths
Refactor `app/api/v1/anomaly.py` and `app/anomaly/telemetry.py` to call
`graph_runner.execute_repair(...)` instead of the current fragile patterns
(`anomaly.py` calls the `run_graph` *handler* and hand-builds a `Request`;
`telemetry.py` re-instantiates its own orchestrator and re-implements ledger
writes). One service, four callers, identical behavior.

---

## Phase G2 — Frontend Real-Time Dashboard

> Replace the `setTimeout` simulation with a typed client that renders the actual
> backend stream. POST-SSE (run needs a body) is consumed with a `fetch` +
> `ReadableStream` parser, since native `EventSource` is GET-only.

### G2.1 Config, types & API base
- `src/lib/config.ts` — read `NEXT_PUBLIC_API_BASE_URL` (default
  `http://localhost:8000`); stop hardcoding the URL in components.
- `src/lib/types.ts` — TS mirror of `GraphStreamEvent` and the node names, kept in
  lockstep with the backend contract.
- `frontend/.env.local.example` + fix `layout.tsx` metadata (title/description
  still say "Create Next App").

### G2.2 Typed SSE client + `useGraphStream` hook
- `src/lib/sseClient.ts` — a small POST-aware SSE reader: `fetch(..., {method:"POST"})`,
  read `response.body` via `TextDecoder`, split on `\n\n`, parse `event:`/`data:`
  frames, yield typed events. Handle abort + connection failure cleanly.
- `src/hooks/useGraphStream.ts` — exposes `{ run(payload), events, activeNode,
  status, finalState, isRunning, error }` driven entirely by real events.

### G2.3 Presentational components (`src/components/`)
- `NodeStatusPanel` — the 5 nodes, highlighting the **real** active node from the
  stream (reuses existing `glow-active` / theme tokens).
- `TerminalLog` — streams real `messages`/log lines (keeps the terminal styling,
  auto-scroll, `[PATCH]` block rendering already in `page.tsx`).
- `StatusBanner` — success / security-blocked / failed from the `complete` event.
- `MetricsPanel` — retry count, final exit code, token/latency from the stream.

### G2.4 Wire `page.tsx` to the real stream
Delete the simulated `steps`/`setTimeout` block; the page composes the components
above and drives them from `useGraphStream`. "Trigger Anomaly" now reflects live
node progress and the true outcome. Preserve the palette toggle and visual design.

---

## Phase G3 — Genuine Ragas Evaluation

> Make the score mean something: evaluate the *real* RAG pipeline, not a literal dict.

### G3.1 Real evaluation dataset from the live pipeline
Replace the hardcoded `data_samples` with a builder that, for a small set of seeded
questions about the **ingested demo corpus**, calls the real retrieval path
(`vectorstore.asearch`) for `contexts` and the real model for `answer`, pairing
each with a curated `ground_truth`. Store seed Q/GT pairs in
`app/eval/fixtures/` so runs are reproducible.

### G3.2 Correct Ragas runner & persistence
Fix the Ragas 0.2.x integration: `evaluate(...)` returns an `EvaluationResult`;
extract `faithfulness` and `context_recall` via `.to_pandas()` (mean of the column)
rather than `result.get(...)`. Persist **both** metrics to the ledger
(`ragas_fidelity_score` = faithfulness, recall in `execution_payload`). Add CLI
args (`--namespace`, `--samples`) and graceful failure with a non-zero exit code.

---

## Phase G4 — Automated Test Suite

> `pytest` must pass offline, no keys, no Docker, no network. This is the gate that
> makes "complete" verifiable.

### G4.1 Harness & fixtures
- Add dev deps: `pytest`, `pytest-asyncio`, `respx` (or rely on `monkeypatch`),
  `pytest-cov` → `requirements-dev.txt`.
- `tests/conftest.py` — fixtures that patch `get_chat_model`, the vectorstore
  service, the Docker sandbox runner, and `create_ledger` with fakes, so nodes and
  endpoints run deterministically.
- Retire the manual `test_*.py` scripts: convert their useful parts to real tests,
  move the rest to `scripts/` (clearly marked as live smoke scripts).

### G4.2 Unit tests
- `routing` — every branch of `route_security` and `route_execution` (no clearance,
  exit 0, retry cap, loop-back).
- `security/blocklist` — `rm -rf`, credential-exfil, escape strings are rejected;
  benign patches pass.
- `anomaly/detector` — warm-up (<20 pts) returns no anomaly; a clear outlier trips.
- `schemas` — `new_agent_state` defaults (esp. `execution_exit_code == -1`).
- `services/sandbox` — exit code / stdout / stderr plumbing with a mocked Docker
  client; asserts `network_mode="none"` and resource caps are set.
- each graph node — correct state delta with mocked LLM/vectorstore.

### G4.3 API / integration tests (FastAPI `TestClient`)
- `health` reports dependency readiness.
- `ingest` and `context/query` (SSE frames) with mocked services.
- `graph/run` **and** `graph/run/stream` with a mocked/stubbed orchestrator —
  assert event sequence (`node_update*` → `complete`) and ledger write.
- `anomaly/trigger` webhook acknowledges fast and dispatches via the shared service.

---

## Phase G5 — Finalization & Hardening

### G5.1 Docs & environment
Refresh `frontend/README.md`, add a root `README.md` with run instructions
(backend `uvicorn`, frontend `next dev`, demo flow), and ensure `.env.example`
lists every key Settings requires. Document the `/graph/run/stream` contract.

### G5.2 Health, CORS & config sanity
Confirm `/api/v1/health` surfaces `pinecone` / `docker` / `ledger` status, and that
`settings.cors_origins` includes the dashboard origin so SSE isn't blocked.

### G5.3 Version control
Add a proper `.gitignore` (ignore `frontend/.next/`, `backend/venv/`,
`__pycache__/`), then commit the untracked Phase 4 work (`eval/`, `demo/`,
`frontend/`) plus all gap-closure changes in logically scoped commits.

---

## Plan Summary

- **Phase G1** Real-Time Streaming Backbone — 3 sub-phases
- **Phase G2** Frontend Real-Time Dashboard — 4 sub-phases
- **Phase G3** Genuine Ragas Evaluation — 2 sub-phases
- **Phase G4** Automated Test Suite — 3 sub-phases
- **Phase G5** Finalization & Hardening — 3 sub-phases

**Total: 5 phases, 15 sub-phases.**

**Sequencing (no broken dependencies):** G1 → G2 (frontend consumes G1's stream),
then G3 and G4 (independent of each other; both depend on the unified run path from
G1.1/G1.3), then G5 last (commits the finished, tested system).
