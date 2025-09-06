from pydantic import BaseModel
from langchain.tools import tool

# If you prefer non-deprecated wrapper:
# from langchain_tavily import TavilySearchResults
from langchain_community.tools.tavily_search import TavilySearchResults
from app.core.tracking import traceable

class WebSearchSchema(BaseModel):
    query: str


@tool(args_schema=WebSearchSchema)
@traceable(name="web_search_tool")
def web_search_tool(query: str) -> str:
    """Search the web (Tavily) and return a concise summary of top results with links."""
    tavily = TavilySearchResults(max_results=4)
    results = tavily.invoke({"query": query})
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        url = r.get("url", "")
        content = (r.get("content") or "").replace("\n", " ")
        title = r.get("title") or url
        snippet = content[:500].strip()
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    return "Top results:\n\n" + "\n\n".join(lines)# def web_search_tool(query: str) -> str:

