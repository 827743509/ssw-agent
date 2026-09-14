from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE)


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数，当前值：{raw_value}") from exc
def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"环境变量 {name} 必须是浮点数，当前值：{raw_value}"
        ) from exc


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    value = raw_value.strip().lower()

    if value in {"true", "1", "yes", "y", "on"}:
        return True

    if value in {"false", "0", "no", "n", "off"}:
        return False

    raise ValueError(
        f"环境变量 {name} 必须是布尔值，当前值：{raw_value}"
    )

SSW_BASE_URL = os.getenv("SSW_BASE_URL", "https://api.moonshot.cn/v1")
SSW_MODEL = os.getenv("SSW_MODEL", "kimi-k3")
SSW_API_KEY = os.getenv("SSW_API_KEY")
AGENT_NAME = os.getenv("AGENT_NAME","ssw-agent")
REDIS_URL = os.getenv("REDIS_URL","redis://127.0.0.1:6379/0")
SSW_WORKSPACE = str(PROJECT_ROOT)
SSW_WEB_HOST = os.getenv("SSW_WEB_HOST", "127.0.0.1")
SSW_WEB_PORT = int(_get_int_env("SSW_WEB_PORT", 8000))
SSW_AGENT_PROTOCOL_HOST = os.getenv("SSW_AGENT_PROTOCOL_HOST", "127.0.0.1")
SSW_AGENT_PROTOCOL_PORT = _get_int_env("SSW_AGENT_PROTOCOL_PORT", 2024)
SSW_AGENT_PROTOCOL_URL = os.getenv(
    "SSW_AGENT_PROTOCOL_URL",
    f"http://{SSW_AGENT_PROTOCOL_HOST}:{SSW_AGENT_PROTOCOL_PORT}",
)


LS_MONGODB_URI = os.getenv("LS_MONGODB_URI","mongodb://root:123456@localhost:27017/langgraph?authSource=admin&replicaSet=rs0")
DATABASE_URL = os.getenv("DATABASE_URL","postgresql+asyncpg://rag:rag@localhost:5432/rag_kb")

# ===== Embedding =====
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_BASE_URL = os.getenv(
    "EMBEDDING_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIM = _get_int_env("EMBEDDING_DIM", 1024)

EMBEDDING_BATCH_SIZE = _get_int_env("EMBEDDING_BATCH_SIZE", 10)

# ===== 文档上传与切分 =====
UPLOAD_MAX_SIZE_MB = _get_int_env("UPLOAD_MAX_SIZE_MB", 50)
CHUNK_SIZE = _get_int_env("CHUNK_SIZE", 600)
CHUNK_OVERLAP = _get_int_env("CHUNK_OVERLAP", 60)

# ===== minio =====
OSS_ORIGINS=os.getenv("OSS_ORIGINS","localhost:9000")
OSS_ACCESS_KEY=os.getenv("OSS_ACCESS_KEY","VRDCTCVBTVDLX0YJJHM3")
OSS_SECRET_KEY=os.getenv("OSS_SECRET_KEY","YotSomHBA5E2zPuqeqXVb65GyHWzRWEUw44aZ+Wc")
OSS_BUCKET=os.getenv("OSS_BUCKET","ssw-bucket")


CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL","redis://localhost:6379/1")
CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND","redis://localhost:6379/2")





CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:9000",
    ).split(",")
    if origin.strip()
]

# 关掉后 route_query 节点强制走 original，方便对比有/无路由的效果
QUERY_ROUTE_ENABLED: bool = _get_bool_env("QUERY_ROUTE_ENABLED",False)
# Multi-Query 策略生成的子查询数量，过大会增加 embedding 成本
RETRIEVAL_TOP_K: int = _get_int_env("RETRIEVAL_TOP_K",5)
RETRIEVAL_MIN_SCORE: float = _get_float_env("RETRIEVAL_MIN_SCORE",0.6)
CHAT_HISTORY_WINDOW: int = _get_int_env("CHAT_HISTORY_WINDOW",5)
MULTI_QUERY_COUNT: int = _get_int_env("MULTI_QUERY_COUNT",3)

RETRIEVAL_RECALL_TOP_K: int = _get_int_env("RETRIEVAL_RECALL_TOP_K",20)
RRF_K: int = _get_int_env("RRF_K",60)

# ===== Reranker =====
RERANK_ENABLED: int = _get_bool_env("RERANK_ENABLED",True)
RERANK_MODEL: str = os.getenv("RERANK_MODEL","qwen3-rerank")
RERANK_BASE_URL: str = os.getenv("RERANK_BASE_URL","https://dashscope.aliyuncs.com/compatible-api/v1/reranks")
RERANK_API_KEY: str = os.getenv("RERANK_API_KEY","sk-ws-H.EXXDDRD.Mx4w.MEYCIQCHPkC9Czt21nH54-5ykj2tCNvSf1--FgXuLaAqGF9RKwIhAJz0DWoe58INbwwl_YZ3PpZFWYUWoGCpZ_N3oqUB94TY")
RERANK_MIN_SCORE: float = _get_float_env("RERANK_MIN_SCORE",0.3)
RERANK_TIMEOUT: int = _get_int_env("RERANK_TIMEOUT",8)

AGENT_LOOP_ENABLED: bool = _get_bool_env("AGENT_LOOP_ENABLED",True)
AGENT_MAX_ROUNDS: int = _get_int_env("AGENT_MAX_ROUNDS",3)


# ===== 语义缓存 =====
# 关掉后 chat 主链路完全跳过缓存查询/写入
SEMANTIC_CACHE_ENABLED: int = _get_bool_env("SEMANTIC_CACHE_ENABLED",True)
# 单条缓存最大存活时间（秒），默认 1 小时
SEMANTIC_CACHE_TTL_SECONDS: int = _get_int_env("SEMANTIC_CACHE_TTL_SECONDS",3600)
# 余弦相似度阈值：query 与缓存问题向量相似度 ≥ 此值且权限范围一致才视为命中
SEMANTIC_CACHE_MIN_SIMILARITY: int = _get_float_env("SEMANTIC_CACHE_MIN_SIMILARITY",0.92)


