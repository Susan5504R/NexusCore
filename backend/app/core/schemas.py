"""Shared data shapes for Nexus-Core.

This module is the single source of truth for every structure that crosses a
boundary in the system:

* ``AgentState`` — the central memory object passed through the LangGraph
  execution graph (defined exactly to the system spec).
* The Pydantic request/response models that define the API contracts and the
  ledger record.

Graph nodes, API endpoints, and services all import from here so the state, the
HTTP contracts, and the database records never drift apart.
"""

import operator
from typing import Any, Dict, List, Optional

from typing_extensions import Annotated, TypedDict

from pydantic import BaseModel, Field


# ───────────────────────── LangGraph orchestrator state ──────────────────────
class AgentState(TypedDict):
    """Central memory tracked through the SRE execution graph.

    ``messages`` uses an ``operator.add`` reducer so that each node can return a
    partial ``{"messages": [...]}`` and LangGraph appends rather than overwrites —
    this is how the conversation/log trail accumulates across the cyclic graph.
    All other keys are plain values that nodes overwrite as the run progresses.
    """

    messages: Annotated[List[Dict[str, str]], operator.add]
    current_target_file: str
    discovered_logs: List[str]
    proposed_patch: str
    execution_exit_code: int
    execution_stderr: str
    security_clearance: bool
    retry_count: int
    telemetry_metrics: Dict[str, Any]


def new_agent_state(
    *,
    current_target_file: str = "",
    discovered_logs: Optional[List[str]] = None,
    messages: Optional[List[Dict[str, str]]] = None,
) -> AgentState:
    """Build a fully-initialized ``AgentState`` with safe defaults.

    TypedDicts have no constructor, and every entry point into the graph (the
    /graph/run endpoint and the anomaly trigger) needs the state seeded the same
    way. Centralizing it here prevents missing-key errors inside the nodes.

    ``execution_exit_code`` starts at -1 to mean "not yet executed" — distinct
    from 0 (success), which the routing logic treats as a terminal condition.
    """
    return AgentState(
        messages=messages or [],
        current_target_file=current_target_file,
        discovered_logs=discovered_logs or [],
        proposed_patch="",
        execution_exit_code=-1,
        execution_stderr="",
        security_clearance=False,
        retry_count=0,
        telemetry_metrics={},
    )


# ───────────────────────────── API: health ───────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-dependency readiness, e.g. {'pinecone': 'ok', 'docker': 'ok'}.",
    )


# ───────────────────────────── API: anomaly webhook ──────────────────────────
class AnomalyPayload(BaseModel):
    alert_id: str = Field(..., description="Unique ID from the external alerting system.")
    service_name: str = Field(..., description="Name of the affected service/container.")
    target_file: str = Field(..., description="The source code file suspected of causing the anomaly.")
    logs: List[str] = Field(..., description="The crash logs or stack trace that triggered the alert.")


# ───────────────────────────── API: ingestion ────────────────────────────────
class IngestRequest(BaseModel):
    directory_path: str = Field(..., description="Absolute path to the codebase to ingest.")
    namespace: Optional[str] = Field(
        default=None, description="Optional Pinecone namespace to isolate this codebase."
    )


class IngestResponse(BaseModel):
    files_processed: int
    chunks_indexed: int
    elapsed_ms: int


# ───────────────────────────── API: context query ────────────────────────────
class ContextQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Raw user/system prompt to answer.")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace to search.")
    top_k: Optional[int] = Field(
        default=None, ge=1, le=50, description="Override for retrieval depth; defaults to settings."
    )


# ───────────────────────────── API: graph run ────────────────────────────────
class GraphRunRequest(BaseModel):
    target_file: str = Field(..., description="File the agent should focus its repair on.")
    logs: List[str] = Field(
        default_factory=list, description="Error/log lines that triggered this run."
    )


class GraphRunResponse(BaseModel):
    run_id: str
    final_exit_code: int
    retry_count: int
    security_clearance: bool
    proposed_patch: str


# ───────────────────────────── API: graph run stream ─────────────────────────
class GraphStreamEvent(BaseModel):
    event: str = Field(..., description="'node_update', 'complete', or 'error'")
    run_id: str
    node: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def from_delta(cls, run_id: str, node_name: str, delta: dict) -> "GraphStreamEvent":
        state_payload = {"active_node": node_name}
        for key in ["retry_count", "execution_exit_code", "security_clearance", "proposed_patch"]:
            if key in delta:
                state_payload[key] = delta[key]
                
        messages = delta.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                state_payload["latest_message"] = last_msg.content
            elif isinstance(last_msg, dict):
                state_payload["latest_message"] = last_msg.get("content", "")
                
        return cls(event="node_update", run_id=run_id, node=node_name, state=state_payload)


# ───────────────────────── Operational ledger record ─────────────────────────
class OperationalLogEntry(BaseModel):
    """Mirrors the ``operational_logs`` table. ``id`` and ``timestamp`` are
    generated by the database, so they are optional on writes."""

    id: Optional[str] = None
    timestamp: Optional[str] = None
    event_source: str
    agent_action: Optional[str] = None
    execution_payload: Optional[str] = None
    execution_status: Optional[str] = None
    token_consumption: int = 0
    compute_latency_ms: int = 0
    ragas_fidelity_score: Optional[float] = None
