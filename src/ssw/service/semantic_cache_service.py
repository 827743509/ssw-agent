import asyncio
import json
from dataclasses import dataclass
from functools import lru_cache

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.query.filter import FilterExpression
from redisvl.utils.vectorize import CustomVectorizer

from ssw.config import EMBEDDING_DIM, REDIS_URL, SEMANTIC_CACHE_MIN_SIMILARITY, SEMANTIC_CACHE_TTL_SECONDS
from ssw.core.logging import get_logger

logger = get_logger(__name__)

_CACHE_NAME = "rag_semantic_cache"
_SCOPE_FIELD = "document_id"

def _stub_embed(text: str, **_: object) -> list[float]:
    """占位 vectorizer：仅用于让 RedisVL 在建索引时知道向量维度。

    主链路始终预先调用项目自己的 embedder 算好 query_embedding，
    再通过 `vector=` 参数直接传给 acheck/astore，永远不会触发到这里。
    """
    return [0.0] * EMBEDDING_DIM



@dataclass(frozen=True)
class CachedAnswer:
    """缓存命中后返回给调用方的快照。"""

    answer: str
    metadata: dict
    cached_question: str


class SemanticCacheService:
    """问答语义缓存。

    与 RAG 链路解耦：lookup 命中时跳过整个图与 LLM；save 在主链路成功（非拒答）
    后由 ChatService 显式调用。
    """

    def __init__(self) -> None:
        self._cache = SemanticCache(
            name=_CACHE_NAME,
            redis_url=REDIS_URL,
            # RediSearch 用「余弦距离 = 1 - 余弦相似度」做 KNN 排序；阈值同步转换
            distance_threshold=1.0 - SEMANTIC_CACHE_MIN_SIMILARITY,
            ttl=SEMANTIC_CACHE_TTL_SECONDS,
            # CustomVectorizer 自带 pydantic model_fields，pyright 看不到 __init__
            # 的位置参数；运行时正常，按 RedisVL 文档示例传入 embed 函数即可
            vectorizer=CustomVectorizer(_stub_embed),  # pyright: ignore[reportCallIssue]
            filterable_fields=[{"name": _SCOPE_FIELD, "type": "tag"}],
            overwrite=False,
        )

    async def lookup(
        self,
        query_embedding: list[float],
    ) -> CachedAnswer | None:
        """Redis 内 KNN 查询：相似度阈值 + 权限范围 Tag 同时满足才返回。"""
        try:
            hits = await self._cache.acheck(
                vector=query_embedding,
                num_results=1,
                return_fields=["prompt", "response", "metadata"],
            )
        except Exception:
            logger.exception("semantic cache lookup failed, treat as miss")
            return None

        if not hits:
            return None

        hit = hits[0]
        metadata = hit.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        logger.info(
            "semantic cache hit: distance=%.4f question=%r",
            float(hit.get("vector_distance", 0.0)),
            hit.get("prompt"),
        )
        return CachedAnswer(
            answer=hit.get("response", ""),
            metadata=metadata,
            cached_question=hit.get("prompt", ""),
        )

    async def save(
        self,
        *,
        question: str,
        query_embedding: list[float],
        answer: str,
        metadata: dict,
        document_id_tag: set[str],
    ) -> None:
        """写入缓存；TTL 由 SemanticCache 自身的 ttl 配置统一控制。"""
        try:
            await self._cache.astore(
                prompt=question,
                response=answer,
                vector=query_embedding,
                metadata=metadata,
                filters={"document_id": ",".join(document_id_tag)},
            )
        except Exception:
            # 写缓存失败不影响主链路：用户已经拿到答案，缓存只是优化
            logger.exception("semantic cache save failed, skip")

    async def delete(
        self,
        *,
        filter_expression: FilterExpression,
    ) -> None:
        """删除缓存；TTL 由 SemanticCache 自身的 ttl 配置统一控制。"""
        try:
            await asyncio.to_thread(
                self._cache.index.drop_by_filter,
                filter_expression
            )
        except Exception:
            logger.exception("semantic cache delete failed, skip")


@lru_cache(maxsize=1)
def get_semantic_cache() -> SemanticCacheService:
    return SemanticCacheService()