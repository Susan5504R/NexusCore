import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from langchain_core.language_models.fake_chat_models import FakeListChatModel

# Ensure all async tests can run
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_ledger():
    ledger = AsyncMock()
    ledger.log_event = AsyncMock()
    ledger.close = AsyncMock()
    return ledger

@pytest.fixture(autouse=True)
def patch_services(monkeypatch, mock_ledger):
    # Patch get_chat_model to return a Fake model
    def mock_get_chat_model(*args, **kwargs):
        return FakeListChatModel(responses=["""```python
import math
def main(): pass
```"""])
    
    monkeypatch.setattr("app.core.llm.get_chat_model", mock_get_chat_model)

    # Patch the VectorStoreService
    mock_vectorstore = AsyncMock()
    mock_vectorstore.asearch.return_value = [
        MagicMock(page_content="Mocked source code content.")
    ]
    # We patch the class wherever it is used, e.g., in context_node
    monkeypatch.setattr("app.graph.nodes.context_node.VectorStoreService", lambda namespace: mock_vectorstore)

    # Patch the Docker sandbox execution (simulate success)
    monkeypatch.setattr("app.graph.nodes.sandbox_node.execute_code_in_sandbox", AsyncMock(return_value=(0, "Success\n", "")))

    # Patch the ledger
    monkeypatch.setattr("app.services.ledger.create_ledger", AsyncMock(return_value=mock_ledger))
    
    # We also patch getattr in graph_runner so it returns our mock ledger instead of needing a real app.state
    original_getattr = getattr
    def custom_getattr(obj, name, default=None):
        if name == "ledger":
            return mock_ledger
        return original_getattr(obj, name, default)
    monkeypatch.setattr("app.services.graph_runner.getattr", custom_getattr)
