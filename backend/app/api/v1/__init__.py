"""Aggregate router for API v1.

Each endpoint module exposes its own ``router``; they are collected here under the
``/api/v1`` prefix and registered once in ``main.create_app()``. Later sub-phases
append their routers to this list (ingest, context, graph).
"""

from fastapi import APIRouter

from app.api.v1 import health, ingest, context, graph, anomaly

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(ingest.router)
api_router.include_router(context.router)
api_router.include_router(graph.router, prefix="/graph")
api_router.include_router(anomaly.router, prefix="/anomaly")
