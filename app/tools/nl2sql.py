import re
from pydantic import BaseModel
from langchain.tools import tool
from langchain_community.utilities import SQLDatabase
from langchain_community.chat_models import ChatOllama
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from app.core.config import settings
from app.core.tracking import traceable

DB = SQLDatabase.from_uri(settings.chinook_uri)
SQL_LLM = ChatOllama(model=settings.ollama_model)

def _clean_sql_query(text: str) -> str:
    text = re.sub(r"```(?:sql|SQL|postgresql|mysql)?\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"^(?:SQL\s*Query|SQLQuery|MySQL|PostgreSQL|SQL)\s*:\s*", "", text, flags=re.IGNORECASE)
    cte = re.search(r"(WITH\b[\s\S]*?SELECT[\s\S]*?;)", text, flags=re.IGNORECASE)
    if cte: text = cte.group(1)
    else:
        selects = list(re.finditer(r"(SELECT[\s\S]*?;)", text, flags=re.IGNORECASE))
        if selects: text = selects[-1].group(1)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    lowered = text.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Generated SQL is not a read-only SELECT/CTE.")
    return text

class SQLToolSchema(BaseModel):
    question: str

@tool(args_schema=SQLToolSchema)
@traceable(name="nl2sql_tool")
def nl2sql_tool(question: str) -> str:
    """Translate a natural-language question into a **read-only** SQL query for the Chinook Postgres DB, execute it, and return SQL + a result preview."""
    write = create_sql_query_chain(SQL_LLM, DB)
    exec_tool = QuerySQLDataBaseTool(db=DB)
    query = _clean_sql_query(write.invoke({"question": question}))
    result = exec_tool.invoke(query)
    preview = result
    if isinstance(result, list) and len(result) > 20:
        preview = result[:20] + [f"... ({len(result)-20} more rows)"]
    return f"SQL:\n{query}\n\nResult:\n{preview}"
