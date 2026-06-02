import json
import asyncio
import logging
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from datasets import Dataset

from app.core.config import get_settings
from app.core.llm import get_chat_model
from app.services.vectorstore import VectorStoreService

logger = logging.getLogger("nexuscore.eval.dataset_builder")

async def build_ragas_dataset(namespace: str = None) -> Dataset:
    """
    Reads the seed questions, queries the real Pinecone vectorstore, 
    and generates answers using the real Gemini model to build a 
    genuine evaluation dataset for RAGAS 0.2.x.
    """
    settings = get_settings()
    fixture_path = Path(__file__).parent / "fixtures" / "seed_questions.json"
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)
        
    vectorstore = VectorStoreService(namespace=namespace or settings.pinecone_namespace)
    llm = get_chat_model(temperature=0.0)
    
    # Simple RAG prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the user's question using ONLY the provided context.\n\nContext:\n{context}"),
        ("user", "{question}")
    ])
    
    chain = prompt | llm
    
    # Ragas 0.2.x required column names
    dataset_dict = {
        "user_input": [],       # replaces "question"
        "retrieved_contexts": [], # replaces "contexts"
        "response": [],         # replaces "answer"
        "reference": []         # replaces "ground_truth"
    }
    
    logger.info(f"Building dataset for {len(seeds)} seed questions...")
    
    for seed in seeds:
        question = seed["question"]
        ground_truth = seed["ground_truth"]
        
        # 1. Real Retrieval
        docs = await vectorstore.asearch(question, top_k=3)
        context_texts = [doc.page_content for doc in docs]
        combined_context = "\n\n".join(context_texts) if context_texts else "No context found."
        
        # 2. Real Generation
        ai_msg = await chain.ainvoke({
            "context": combined_context,
            "question": question
        })
        
        # 3. Format
        dataset_dict["user_input"].append(question)
        dataset_dict["retrieved_contexts"].append(context_texts)
        dataset_dict["response"].append(ai_msg.content)
        dataset_dict["reference"].append(ground_truth)
        
    logger.info("Dataset built successfully!")
    return Dataset.from_dict(dataset_dict)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(build_ragas_dataset())
