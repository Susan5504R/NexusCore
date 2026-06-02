import logging
from typing import List

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

from app.core.config import get_settings
from app.services.embeddings import get_embeddings

logger = logging.getLogger("nexuscore.vectorstore")

class VectorStoreService:
    def __init__(self, pc_client: Pinecone = None):
        self.settings = get_settings()
        # Use provided client (e.g., from app.state) or create a new one
        self.pc = pc_client or Pinecone(api_key=self.settings.pinecone_api_key)
        self.index_name = self.settings.pinecone_index
        
        # Ensure index exists (synchronous API call, happens once on init)
        self._ensure_index()
        
        self.embeddings = get_embeddings()
        
        # Initialize LangChain wrapper
        self.vectorstore = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings,
            pinecone_api_key=self.settings.pinecone_api_key
        )

    def _ensure_index(self):
        """Creates the Pinecone index if it does not already exist."""
        try:
            # list_indexes() returns an iterable of IndexModel objects in pinecone>=3.0
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: '{self.index_name}'...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.settings.embedding_dimension,
                    metric=self.settings.pinecone_metric,
                    spec=ServerlessSpec(
                        cloud=self.settings.pinecone_cloud,
                        region=self.settings.pinecone_region
                    )
                )
                logger.info(f"Index '{self.index_name}' created successfully.")
            else:
                logger.info(f"Pinecone index '{self.index_name}' already exists.")
        except Exception as e:
            logger.error(f"Failed to ensure Pinecone index exists: {e}")
            raise

    async def aupsert_documents(self, documents: List[Document], namespace: str = None):
        """Async wrapper to upsert LangChain Document chunks."""
        if not documents:
            logger.warning("No documents provided to upsert.")
            return
            
        logger.info(f"Upserting {len(documents)} documents to vector store '{self.index_name}'...")
        await self.vectorstore.aadd_documents(documents, namespace=namespace)
        logger.info("Upsert complete.")

    async def asearch(self, query: str, top_k: int = None, namespace: str = None) -> List[Document]:
        """Async semantic search returning the most relevant Document chunks."""
        top_k = top_k or self.settings.retrieval_top_k
        logger.info(f"Searching vector store for query: '{query}' (top_k={top_k})")
        results = await self.vectorstore.asimilarity_search(query, k=top_k, namespace=namespace)
        return results


# Process-wide singleton
_vectorstore_service = None

def get_vectorstore_service(pc_client: Pinecone = None) -> VectorStoreService:
    """Returns a cached instance of the VectorStoreService."""
    global _vectorstore_service
    if _vectorstore_service is None:
        _vectorstore_service = VectorStoreService(pc_client)
    return _vectorstore_service
