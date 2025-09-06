import os
from typing import List
from pydantic import BaseModel
from langchain.tools import tool
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatOllama
from app.core.config import settings
from app.core.tracking import traceable

# Global vectorstore (set at startup)
VECTORSTORE: Qdrant | None = None

@traceable(name="initialize_vectorstore")
def initialize_vectorstore(docs_dir: str) -> Qdrant:
    documents: List[Document] = []
    if os.path.isdir(docs_dir):
        for filename in os.listdir(docs_dir):
            path = os.path.join(docs_dir, filename)
            if filename.lower().endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif filename.lower().endswith(".docx"):
                loader = Docx2txtLoader(path)
            else:
                continue
            loaded = loader.load()
            for d in loaded:
                d.metadata = d.metadata or {}
                d.metadata.setdefault("source", path)
            documents.extend(loaded)
    print(f"RAG: loaded {len(documents)} docs")

    chunks = []
    if documents:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)
    print(f"RAG: split into {len(chunks)} chunks")

    embedding = SentenceTransformerEmbeddings(model_name=settings.embed_model)

    client = QdrantClient(url=settings.qdrant_url)
    collection = "my_rag_collection"
    names = [c.name for c in client.get_collections().collections]
    if collection not in names:
        client.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    vs = Qdrant.from_documents(
        documents=chunks,
        embedding=embedding,
        collection_name=collection,
        url=settings.qdrant_url,
    )
    return vs

class RagToolSchema(BaseModel):
    question: str

RAG_QA_LLM = ChatOllama(model=settings.ollama_model)

@tool(args_schema=RagToolSchema)
@traceable(name="retriever_tool")
def retriever_tool(question: str) -> str:
    """Retrieve the most relevant chunks from the local RAG index (Qdrant) and answer using ONLY that context, with sources appended."""
    global VECTORSTORE
    if VECTORSTORE is None:
        return ("RAG is not initialized yet (no documents indexed). "
                "Add PDF/DOCX files to the docs folder and restart the server.")
    try:
        retriever = VECTORSTORE.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.3},
        )
        docs = retriever.invoke(question)
        if not docs:
            return "I don't have enough information in the documents."

        combined = "\n\n".join(d.page_content for d in docs)

        prompt = ChatPromptTemplate.from_template(
            """You are a precise assistant. Using ONLY the context below, answer clearly and concisely.
If the answer isn't in the context, say "I don't have enough information in the documents."
Respect the user's stored tone, summary_style, and prefers_sources.

Question:
{q}

Context:
{c}

Answer:"""
        )
        chain = (prompt | RAG_QA_LLM | StrOutputParser())
        answer = chain.invoke({"q": question, "c": combined})

        sources = []
        for d in docs:
            s = d.metadata.get("source")
            page = d.metadata.get("page")
            sources.append(f"{os.path.basename(s)}#page={page}" if s and page is not None
                           else os.path.basename(s) if s else "")
        sources = sorted(set([s for s in sources if s]))
        if sources:
            answer += "\n\nSources: " + ", ".join(sources)
        return answer
    except Exception as e:
        return f"RAG error: {e}"