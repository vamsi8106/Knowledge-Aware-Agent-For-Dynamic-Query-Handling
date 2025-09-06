# # app/core/config.py
# from pydantic_settings import BaseSettings, SettingsConfigDict
# from pathlib import Path
# import os

# class Settings(BaseSettings):
#     app_host: str = "0.0.0.0"
#     app_port: int = 8000

#     data_dir: Path = Path("./data")
#     docs_dir: Path = Path("./docs")

#     qdrant_url: str = "http://localhost:6333"
#     embed_model: str = "all-MiniLM-L6-v2"

#     chinook_uri: str = "postgresql+psycopg2://chinook_user:chinook_pass@localhost:5432/chinook_db"

#     # Router model
#     supervisor_model: str = "openai:gpt-4o"

#     # API keys (optional)
#     openai_api_key: str | None = None
#     ollama_model: str = "llama3.2:1b"
#     groq_api_key: str | None = None
#     tavily_api_key: str | None = None

#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_prefix="",           # we accept the keys as-is
#         case_sensitive=False,    # .env keys can be lower/upper
#         extra="ignore",          # <-- allow unknown keys
#     )

# settings = Settings()
# settings.data_dir.mkdir(parents=True, exist_ok=True)

# # Propagate to library-expected env vars if set (helps Tavily, etc.)
# if settings.tavily_api_key and not os.getenv("TAVILY_API_KEY"):
#     os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
# if settings.openai_api_key and not os.getenv("OPENAI_API_KEY"):
#     os.environ["OPENAI_API_KEY"] = settings.openai_api_key
# if settings.groq_api_key and not os.getenv("GROQ_API_KEY"):
#     os.environ["GROQ_API_KEY"] = settings.groq_api_key

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    data_dir: Path = Path("./data")
    docs_dir: Path = Path("./docs")

    qdrant_url: str = "http://localhost:6333"
    embed_model: str = "all-MiniLM-L6-v2"

    chinook_uri: str = "postgresql+psycopg2://chinook_user:chinook_pass@localhost:5432/chinook_db"

    # Router model
    supervisor_model: str = "openai:gpt-4o"

    # API keys (optional)
    openai_api_key: str | None = None
    ollama_model: str = "llama3.2:1b"
    groq_api_key: str | None = None
    tavily_api_key: str | None = None

    # LangSmith / tracing
    langsmith_enabled: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)

# Propagate to library-expected env vars if set (helps Tavily, etc.)
if settings.tavily_api_key and not os.getenv("TAVILY_API_KEY"):
    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
if settings.openai_api_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.groq_api_key and not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = settings.groq_api_key
# Map keys to libraries’ expected env vars
if settings.langsmith_enabled:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    if settings.langsmith_endpoint:
        os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langsmith_endpoint)
    if settings.langsmith_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    if settings.langsmith_project:
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
