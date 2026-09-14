import json
from typing import TypedDict

from langchain_core.messages import BaseMessage, message_to_dict
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from ssw.config import AGENT_MAX_ROUNDS, AGENT_LOOP_ENABLED
from ssw.core.MongodbClient import mongo_client
from ssw.service.semantic_cache_service import get_semantic_cache
from ssw.subagents.rag.nodes.judge_context import judge_context
from ssw.subagents.rag.nodes.observe_context import observe_context
from ssw.subagents.rag.nodes.plan_retrieval import plan_retrieval
from ssw.subagents.rag.nodes.refuse import refuse
from ssw.subagents.rag.nodes.rerank import rerank
from ssw.subagents.rag.nodes.retrieve import retrieve
from ssw.subagents.rag.nodes.route_query import route_query
from ssw.subagents.rag.rag_state import RAGState


class RAGInput(TypedDict):
    query: str

def _after_plan(state: RAGState) -> str:
    """planner 决策为 refuse 时直接走 refuse 节点统一塞拒答文案，跳过后续检索 / 精排。"""
    if state.get("agent_steps"):
        last_action = state["agent_steps"][-1].get("action")
        if last_action == "refuse":
            return "refuse"
    return "retrieve"

def _cache_hit(state: RAGState) -> str:
    """planner 决策为 refuse 时直接走 refuse 节点统一塞拒答文案，跳过后续检索 / 精排。"""
    if state.get("cache_hit"):
        return "end"
    return "plan_retrieval"

def _after_observe(state: RAGState) -> str:
    """observe 后决定继续循环还是结束循环交给 rerank 精排。

    退出循环条件（任一即停）：
    - 关闭了 agent loop（退化为单轮）
    - 本轮已足够（context_sufficient=True）
    - 达到 agent_max_rounds 上限

    退出循环后统一进 rerank（不再直接 END）：哪怕本轮 sufficient=False，
    也走完 rerank → judge_context，让 judge_context 一处统一拒答闸门。
    """
    if not AGENT_LOOP_ENABLED:
        return "rerank"
    if state.get("context_sufficient"):
        return "rerank"
    if state.get("retrieval_round", 0) >= AGENT_MAX_ROUNDS:
        return "rerank"
    return "plan"


async def _after_judge(state: RAGState) -> str:
    """judge_context 后的最终闸门：上下文足够 → END；不足 → refuse 节点。"""
    if state.get("context_is_enough"):
        #写入redis语义缓存
        await get_semantic_cache().save(question=state.get("query"),answer=json.dumps(state, default=json_default, ensure_ascii=False),metadata={},
                                  document_id_tag= set([str(chunk.document_id) for chunk in state.get("retrieved_chunks",[])]),query_embedding=state["query_embedding"])
        return "end"
    return "refuse"

def json_default(obj):
    if isinstance(obj, BaseMessage):
        return message_to_dict(obj)

    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    return str(obj)

async def _build_rag_graph():
    builder = StateGraph(RAGState)


    builder.add_node("route_query", route_query)
    builder.add_node("plan_retrieval", plan_retrieval)
    builder.add_node("retrieve", retrieve)
    builder.add_node("observe_context", observe_context)
    builder.add_node("rerank", rerank)
    builder.add_node("judge_context", judge_context)
    builder.add_node("refuse", refuse)



    builder.add_edge(START, "route_query")


    builder.add_conditional_edges(
        "route_query",
        _cache_hit,
        {"end": END, "plan_retrieval": "plan_retrieval"},
    )


    builder.add_conditional_edges(
        "plan_retrieval",
        _after_plan,
        {"retrieve": "retrieve", "refuse": "refuse"},
    )
    builder.add_edge("retrieve", "observe_context")
    builder.add_conditional_edges(
        "observe_context",
        _after_observe,
        {"plan": "plan_retrieval", "rerank": "rerank"},
    )
    builder.add_edge("rerank", "judge_context")
    builder.add_conditional_edges(
        "judge_context",
        _after_judge,
        {"end": END, "refuse": "refuse"},
    )
    builder.add_edge("refuse", END)


    checkpointer = MongoDBSaver(mongo_client, db_name="langgraph")
    return builder.compile(checkpointer)






