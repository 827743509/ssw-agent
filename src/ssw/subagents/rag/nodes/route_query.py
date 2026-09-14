"""route_query：判断是否对查询做改写 / HyDE / Multi-Query 处理。

策略由 LLM 路由器选择，节点本身只做编排，具体调用封装在 `app.llm.query_rewriter`。
失败降级在 QueryRewriter 内部完成；这里只关心"把结果写回 state"。
"""
import json

from langchain_core.messages import messages_from_dict

from ssw.config import QUERY_ROUTE_ENABLED, MULTI_QUERY_COUNT
from ssw.ingestion.embedder import get_embeddings
from ssw.service.semantic_cache_service import get_semantic_cache
from ssw.subagents.rag.query_rewriter import get_query_rewriter
from ssw.subagents.rag.rag_state import RAGState


async def route_query(state: RAGState) -> RAGState:
    state["query"] = state["messages"][-1].content


    embedding=await get_embeddings(1).aembed_documents([state["query"]])
    hits = await get_semantic_cache().lookup(embedding[0])
    if  hits:
        metadata=deserialize_state(hits.answer)
        return {
            **metadata,
            "query_embedding":embedding[0],
            "cache_hit": True,
            "query": state["query"],
        }
    else:
        state["cache_hit"] = False

    if not QUERY_ROUTE_ENABLED:
        # 关闭路由：直接走原始查询，保留 normalize_query 透传的 state["query"]
        return {"route": "original", "query": state["query"],"query_embedding":embedding[0]}

    result = await get_query_rewriter().optimize(
        question=state["query"],
        multi_query_count=MULTI_QUERY_COUNT,
    )
    # query 字段被显式覆盖：rewrite/hyde 路径下用改写文本去向量召回
    update: RAGState = {"route": result.route, "query": result.query,"query_embedding":embedding[0]}
    if result.rewritten_query is not None:
        update["rewritten_query"] = result.rewritten_query
    if result.hyde_answer is not None:
        update["hyde_answer"] = result.hyde_answer
    if result.multi_queries is not None:
        update["multi_queries"] = result.multi_queries
    return update


def deserialize_state(value: str) -> dict:
    data = json.loads(value)

    if "messages" in data:
        data["messages"] = messages_from_dict(data["messages"])

    return data