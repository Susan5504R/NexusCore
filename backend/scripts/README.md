# Live smoke scripts

These are **manual, live** smoke scripts — not part of the automated test suite.
They hit real services (Gemini, Pinecone, Docker) and need valid keys in `.env`.

They are named `test_*.py` for historical reasons but are excluded from `pytest`
collection (see `backend/pytest.ini`, which pins `testpaths = tests`). Run them
directly:

```bash
python scripts/test_sandbox.py
python scripts/test_vectorstore.py
python scripts/test_nodes.py
python scripts/test_stream.py   # requires the API running on localhost:8000
```

The offline, deterministic suite lives in `backend/tests/`.
