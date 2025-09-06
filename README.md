# Knowledge-Aware-Agent-For-Dynamic-Query-Handling
A modular FastAPI service that orchestrates multiple tools (Web Search, RAG over PDFs/DOCX, NL→SQL) using a LangGraph supervisor with per-user conversation history and long-term memory in SQLite and LangSmith tracing included.

**Tech:** Python, Lang graph Agents,qdrant, Postgres, FastAPI, pytest

## Features

### Agent Architecture
- **Router/Supervisor** (OpenAI or Ollama) intelligently routes queries to specialized agents:
  - **web_researcher** → Tavily web search for real-time information
  - **rag** → Qdrant vector store with MiniLM embeddings over local documents
  - **nl2sql** → Natural language to SQL queries against Chinook Postgres database via LangChain SQL tools
  - **memory** → Persistent user profile management in SQLite

### Persistence & Memory
- **Conversation History** via LangGraph SqliteSaver for maintaining context across sessions
- **Long-term Memory** via SQLite `user_profile` table for personalized interactions
- **FastAPI HTTP Endpoints** with clean separation of concerns for scalable architecture

## Prerequisites

- **Python 3.11+**
- **Docker** (optional, recommended for Qdrant + Postgres)
- **Ollama** running locally with `llama3.2:1b` model pulled

### API Keys Required
- **OPENAI_API_KEY** - If using OpenAI as the router/supervisor
- **TAVILY_API_KEY** - For web search functionality
- **LANGCHAIN_API_KEY** - Optional, for LangSmith tracing and monitoring

## 📁 Project Structure

```text
unified-agents/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── chat.py
│   │       └── memory.py
│   ├── agents/
│   │   └── unified_graph.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logger.py
│   │   └── tracing.py
│   ├── db/
│   │   └── profile_store.py
│   ├── services/
│   │   └── graph_runtime.py
│   ├── tools/
│   │   ├── memory_tools.py
│   │   ├── nl2sql.py
│   │   ├── rag.py
│   │   └── web_search.py
│   └── main.py
├── data/                 # created at runtime
├── docs/                 # put your PDFs/DOCX here for RAG
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── README.md

```

## Quickstart
1. **Clone the Repository**

   ```bash
   git clone https://github.com/vamsi8106/Knowledge-Aware-Agent-For-Dynamic-Query-Handling.git
   ```
## 2. **Install requirements**

```bash
cd Knowledge-Aware-Agent-For-Dynamic-Query-Handling
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. **.env file structure**

Create a `.env` file in the project root with the following structure:

```bash
OPENAI_API_KEY="xxxx"
TAVILY_API_KEY="xxxx"
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY="xxxx"
LANGCHAIN_PROJECT="agent_project"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
```

Make sure in local Ollama is running and llama3.2:1b is pulled:

```bash
# Start Ollama service
ollama serve

# Pull the required model (in a new terminal)
ollama pull llama3.2:1b
```

## 4. **Run Qdrant via docker**

```bash
docker run -d --name qdrant \
  -p 6333:6333 \
  -v ~/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

- Put your PDFs/DOCX into ./docs
- On startup, the app embeds them (MiniLM) and indexes into Qdrant

## 5. **Prepare Postgres:** Import the Chinook sample DB (recommended)

### 1. Create DB & user:

```bash
psql -U postgres -h localhost -c "CREATE USER chinook_user WITH PASSWORD 'chinook_pass';"
psql -U postgres -h localhost -c "CREATE DATABASE chinook_db OWNER chinook_user;"
```

### 2. Import the Chinook schema/data for PostgreSQL (download Chinook_PostgreSql.sql and run):

```bash
psql -U chinook_user -h localhost -d chinook_db -f /path/to/Chinook_PostgreSql.sql
```

This provides tables like Employee (or employee depending on quoting), which the NL→SQL tool can query (e.g., to find Andrew Adams, General Manager).

6. **Run the API server:**

  ```bash
  uvicorn app.main:app --reload --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000}

  ```
## Test the API

### Unified Agents: One-shot Query Flow

Configure your environment variables and test the complete agent system:

```bash
# === Configuration ===
BASE_URL=${BASE_URL:-http://localhost:8000}
USER_ID=${USER_ID:-vami}

# === Health Check ===
# Verify the service is running
curl -s "$BASE_URL/health"

# === Memory Management ===
# (1) Seed user memory directly (persisted in ./data/profile.sqlite3)
curl -s -X POST "$BASE_URL/memory/$USER_ID/remember" \
  -H "Content-Type: application/json" \
  -d '{"key":"prefers_sources","value":true}'

# === Agent Query Tests ===

# (2) Web Research Agent → Routes to web_researcher (Tavily API)
# Tests real-time internet search capabilities
curl -s -X POST "$BASE_URL/chat/$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"message":"what is capital of andhra pradesh?"}'

# (3) RAG Agent → Routes to document retrieval from local PDFs/DOCX
# Requires Qdrant running and documents in ./docs directory
curl -s -X POST "$BASE_URL/chat/$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"message":"what is Diabetic retinopathy screening from my doc?"}'

# (4) NL2SQL Agent → Natural Language to SQL against Postgres
# Requires Chinook database running with sample data
curl -s -X POST "$BASE_URL/chat/$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"message":"what is email of andrew adams who is general manager?"}'

# (5) Memory Agent → Natural language memory storage
# Demonstrates conversational memory management
curl -s -X POST "$BASE_URL/chat/$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"message":"remember that my preferred tone is concise"}'

# === Memory Retrieval ===
# (6) View all saved user preferences and memory
curl -s "$BASE_URL/memory/$USER_ID"
```

### What Each Test Does

- **Health Check**: Confirms the FastAPI service is running and responsive
- **Memory Seeding**: Directly stores user preferences in SQLite database
- **Web Research**: Tests Tavily integration for real-time web search
- **RAG Query**: Tests document retrieval from Qdrant vector store using your local documents
- **NL2SQL Query**: Tests natural language to SQL conversion against Chinook database
- **Conversational Memory**: Tests natural language memory storage via chat interface
- **Memory Retrieval**: Views all stored user data for debugging and verification
  
## Troubleshooting

- **`GET /memory/{user}` returns `{}`** — you haven’t saved anything for that user yet, or you’re checking the wrong user id.

- **“RAG is not initialized”** — ensure Qdrant is running, you have files in `./docs`, then restart the server.

- **Web search fails** — set `TAVILY_API_KEY` (or `tavily_api_key`) in `.env`.

- **NL→SQL fails** — confirm `CHINOOK_URI` is correct and data exists in Postgres.

- **SQLite permission errors** — ensure `DATA_DIR` is writable (`./data`).


## Credits

- [LangGraph](https://www.langchain.com/langgraph) — orchestration and stateful agent graphs on top of LangChain.
- [FastAPI](https://fastapi.tiangolo.com/) — a modern, high-performance web framework for building APIs with Python.

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.




