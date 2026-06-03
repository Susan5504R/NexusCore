# Nexus-Core — Production-Readiness Fix Plan

> Companion to `IMPLEMENTATION_PLAN.md` and `GAP_IMPLEMENTATION_PLAN.md`. The 20 + 15
> sub-phases are built, but a code review (run against the live API + test runner)
> found that two features committed as "complete" are **non-functional** and one
> shipped feature is a **production hazard**. This plan repairs them.
>
> Grounded in verified facts (not assumptions):
> - `pytest tests/` → **10/10 ERROR at setup**; `conftest.py` patches modules/attrs
>   that don't exist (`app.core.llm`, `context_node.VectorStoreService`,
>   `sandbox_node.execute_code_in_sandbox`).
> - `import app.eval.dataset_builder` → `ModuleNotFoundError: app.core.llm`; the
>   Ragas pipeline cannot import, let alone run (5 stacked bugs).
> - `anomaly/telemetry.py` starts on boot and fires real Gemini + Docker graph runs
>   off `random`-generated "anomalies" — unbounded cost/side-effects in production.
> - Model names are **valid** (verified live): `gemini-3.5-flash` exists,
>   `models/gemini-embedding-001` → 3072 dims, matching the Pinecone index. The core
>   runtime path imports cleanly. These are NOT changed.

Follows `plan-driven-dev`: snippets show **intent**, not copy-paste code. Each
sub-phase is implemented as clean, integrated code that matches existing conventions.

---

## Cross-cutting invariants (carried over)

1. **Tests need no secrets** — the suite mocks Gemini, Pinecone, Docker, and the
   ledger, and runs offline. Lifespan I/O is stubbed so `TestClient` boots clean.
2. **No behavior drift** — all triggers keep using the single `graph_runner` path.
3. **Bounded cost** — autonomous side-effects (telemetry → graph run) are opt-in.
4. **Core runtime untouched** — valid model names, dimensions, and the request→RAG→
   graph→sandbox path stay exactly as they are; we only repair what's broken.

---

## Phase F1 — Restore the Automated Test Suite (the verification gate)

> Nothing else can be trusted until `pytest` actually runs. Rebuild the harness so
> every collected test passes offline.

### F1.1 Rebuild `tests/conftest.py`
Replace the broken autouse fixture. Patch each dependency **where it is imported**
(node modules bind names at import time, so patching the source module is not
enough), and stub the lifespan's external clients so `TestClient` boots offline.

- Mock `get_chat_model` / `get_security_model` in `modification_node`,
  `arbitration_node`, and `api.v1.context` — returning a fake whose
  `with_structured_output(...).ainvoke()` yields a real `PatchProposal` /
  `SecurityDecision`, and whose `astream(...)` yields message chunks.
- Mock `get_vectorstore_service` in `context_node`, `api.v1.ingest`,
  `api.v1.context` → returns an object with async `asearch` / `aupsert_documents`.
- Mock `execute_in_sandbox` in `sandbox_node` → `(0, "Success\n", "")`.
- Stub lifespan internals (`app.core.lifespan.Pinecone`, `create_ledger`,
  `telemetry_loop`, `docker.from_env`) so startup does no real network/IO.
- Drop the deprecated custom `event_loop` fixture (no `async def` tests exist).

### F1.2 Fix `tests/test_api.py` + verify green
`TestClient(app)` at module scope never runs lifespan, so `app.state` is empty.
Provide a context-managed `client` fixture (so lifespan + mocks run) and have the
API tests consume it. Then run `pytest` and confirm **all tests pass**.

---

## Phase F2 — Repair the Ragas Evaluation Pipeline

> Make the detached eval script import and run against the real RAG path.

### F2.1 Fix `app/eval/dataset_builder.py`
- `from app.services.llm import get_chat_model` (not `app.core.llm`).
- Use `get_vectorstore_service()` and pass `namespace` to `asearch` — drop the
  invalid `VectorStoreService(namespace=...)` ctor and `settings.pinecone_namespace`.
- Call `get_chat_model()` with no args (it is already temperature 0).
- Add an optional `samples` cap so a run can be limited for cost.

### F2.2 Fix `app/eval/ragas_suite.py`
- `create_ledger(settings.supabase_db_url)`; skip persistence gracefully if the
  ledger is unconfigured (don't crash).
- Use `models/gemini-embedding-001` for eval embeddings (`models/embedding-001` no
  longer exists in the API).
- Add a `--samples` CLI arg, thread it into the builder; keep non-zero exit on
  failure.

---

## Phase F3 — Production Safety & Repo Hygiene

### F3.1 Gate the autonomous telemetry loop
Add `enable_telemetry_loop: bool = False` to `Settings`. The lifespan starts the
loop only when enabled, so a default deployment never fires unsolicited LLM/Docker
runs off simulated metrics. Document the flag in `.env.example`.

### F3.2 Relocate stale root smoke scripts
Move `test_nodes.py`, `test_sandbox.py`, `test_stream.py`, `test_vectorstore.py`
from `backend/` into `backend/scripts/` (they are live, key-dependent smoke
scripts) so a bare `pytest` no longer collects `test_stream::test_stream`.

---

## Phase F4 — Consistency & Minor Correctness

### F4.1 Config-driven routing + drop dead Groq config
- `route_execution` reads `settings.max_retries` instead of the literal `3`.
- Remove the unused `groq_api_key` / `security_model` settings and the
  `langchain-groq` dependency (the arbiter runs on Gemini at temperature 0); the
  config no longer advertises a path the code doesn't take.

### F4.2 Docstring & env/template cleanup
- Fix the `embeddings.py` docstring (`text-embedding-004` → `gemini-embedding-001`)
  and the stale "wired in a later phase" notes in `health.py`.
- Update `.env.example` (drop Groq, add the telemetry flag).

---

## Phase F5 — Final Verification

### F5.1 Full sweep
- `pytest` → all green; `import app.main` + `import app.eval.ragas_suite` clean.
- Confirm a bare `pytest` collects only real tests.
- Report the final state.

---

## Explicitly deferred (flagged, not done here)

- **Ledger token accounting** (`token_consumption` is always 0). Real per-run token
  totals require threading `usage_metadata` through `AgentState` and the nodes;
  `with_structured_output` also hides usage. This is a feature gap, not a bug, and a
  fragile change — deferred so it doesn't destabilize the runtime path. Flagged for
  a follow-up.
- **Real telemetry signal source** — the loop still uses simulated metrics; F3.1
  only makes it opt-in. Wiring a real log/metric aggregator is out of scope.

---

## Plan Summary

- **F1** Restore the Test Suite — 2 sub-phases
- **F2** Repair Ragas Evaluation — 2 sub-phases
- **F3** Production Safety & Hygiene — 2 sub-phases
- **F4** Consistency & Minor Correctness — 2 sub-phases
- **F5** Final Verification — 1 sub-phase

**Total: 5 phases, 9 sub-phases.** Order: F1 first (proves everything else), then
F2/F3 (independent), F4, F5 last.
