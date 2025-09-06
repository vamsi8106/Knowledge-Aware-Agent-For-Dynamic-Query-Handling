from __future__ import annotations
from typing import Literal, Sequence, List
from typing_extensions import Annotated, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from app.core.config import settings
from app.db.profile_store import ProfileStore
from app.services.graph_runtime import current_user_id_ctx
from app.tools.web_search import web_search_tool
from app.tools.nl2sql import nl2sql_tool
from app.tools.memory_tools import remember_tool, recall_tool
import app.tools.rag as rag_mod  # IMPORTANT: use the module, not a copied symbol
from app.core.tracking import traceable

# LLMs
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama


def get_router_llm():
    if settings.supervisor_model.startswith("openai:"):
        model = settings.supervisor_model.split("openai:", 1)[1]
        return ChatOpenAI(model_name=model)
    if settings.supervisor_model.startswith("ollama:"):
        model = settings.supervisor_model.split("ollama:", 1)[1]
        return ChatOllama(model=model)
    return ChatOpenAI(model_name="gpt-4o")


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def make_memory_injector(profile_store: ProfileStore):
    def _inject(messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
        uid = current_user_id_ctx.get()
        prof = profile_store.get_profile(uid)
        if not prof:
            return messages
        lines = ["User profile memory (facts/preferences):"] + [f"- {k}: {v}" for k, v in prof.items()]
        rubric = (
            "When responding, respect the user's stored preferences (tone, summary_style, prefers_sources, etc.). "
            "If prefers_sources is True, place sources at the very end."
        )
        return [SystemMessage(content="\n".join(lines) + "\n\n" + rubric)] + list(messages)
    return _inject

@traceable(name="worker_agent_step")
def create_agent(agent_llm, tools: List, memory_inject):
    llm_with_tools = agent_llm.bind_tools(tools)

    def chatbot(state: AgentState):
        msgs = memory_inject(state["messages"])
        return {"messages": [llm_with_tools.invoke(msgs)]}

    gb = StateGraph(AgentState)
    gb.add_node("agent", chatbot)
    gb.add_node("tools", ToolNode(tools=tools))
    gb.add_conditional_edges("agent", tools_condition)
    gb.add_edge("tools", "agent")
    gb.set_entry_point("agent")
    return gb.compile()


def _should_finish(state: MessagesState, workers: list[str]) -> bool:
    msgs = state.get("messages", [])
    if not msgs:
        return False
    last = msgs[-1]
    if isinstance(last, AIMessage) and getattr(last, "name", None) in workers:
        tool_calls = (last.additional_kwargs or {}).get("tool_calls")
        if not tool_calls:
            return True
    return False


class Router(BaseModel):
    next: Literal["web_researcher", "rag", "nl2sql", "memory", "FINISH"]


def build_graph(checkpointer, profile_store: ProfileStore):
    # Ensure the vectorstore exists ON THE MODULE (so the tool sees it)
    if rag_mod.VECTORSTORE is None:
        rag_mod.VECTORSTORE = rag_mod.initialize_vectorstore(str(settings.docs_dir))

    memory_inject = make_memory_injector(profile_store)
    SUP_LLM = get_router_llm()

    members = ["web_researcher", "rag", "nl2sql", "memory"]
    options = members + ["FINISH"]
    SUPERVISOR_PROMPT = (
        "You are a supervisor managing these workers: "
        f"{members}. Respond ONLY with the next worker from: {options}. "
        "Routing guidelines:\n"
        "- web_researcher for public web/news\n"
        "- rag for local documents\n"
        "- nl2sql for Chinook database\n"
        "- memory for remember/recall/save/forget\n"
        "- FINISH when task is complete.\n"
    )

    # Create each worker agent ONCE, and use rag_mod.retriever_tool
    web_agent = create_agent(SUP_LLM, [web_search_tool, remember_tool, recall_tool], memory_inject)
    rag_agent = create_agent(SUP_LLM, [rag_mod.retriever_tool, remember_tool, recall_tool], memory_inject)
    sql_agent = create_agent(SUP_LLM, [nl2sql_tool, remember_tool, recall_tool], memory_inject)
    mem_agent = create_agent(SUP_LLM, [remember_tool, recall_tool], memory_inject)


    @traceable(name="supervisor_node")
    def supervisor_node(state: MessagesState) -> Command:
        if _should_finish(state, members):
            return Command(goto=END)
        messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
        decision = SUP_LLM.with_structured_output(Router).invoke(messages)
        goto = decision.next
        if goto == "FINISH":
            return Command(goto=END)
        return Command(goto=goto)

    def wrap(agent, name: str):
        def node(state: MessagesState) -> Command:
            result = agent.invoke({"messages": state["messages"]})
            last = result["messages"][-1]
            return Command(
                update={"messages": [AIMessage(content=last.content, name=name, additional_kwargs=last.additional_kwargs)]},
                goto="supervisor"
            )
        return node

    builder = StateGraph(MessagesState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("web_researcher", wrap(web_agent, "web_researcher"))
    builder.add_node("rag", wrap(rag_agent, "rag"))
    builder.add_node("nl2sql", wrap(sql_agent, "nl2sql"))
    builder.add_node("memory", wrap(mem_agent, "memory"))
    builder.add_edge(START, "supervisor")
    return builder.compile(checkpointer=checkpointer)
