from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timezone, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.store.redis import RedisStore

from ssw.api.documents import documents_router
from ssw.config import AGENT_NAME, REDIS_URL, CORS_ORIGINS
from ssw.core.AuthenticationMiddleware import AuthenticationMiddleware
from ssw.core.MongodbClient import mongo_client, async_mongo_client
from ssw.core.error_handlers import register_error_handlers
from ssw.core.logging import get_logger, configure_logging

src_dir = Path(__file__).resolve().parents[1]
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
from langgraph.checkpoint.mongodb import MongoDBSaver
from ssw.api.database import routerDataBase
from ssw.api.chat import routerChat
from ssw.api.mcp import routerMcp
from ssw.api.skills import routerSkills
from ssw.agent import create_chat_agent

from ssw.dependency import get_mcp_repository, get_mcp_service

scheduler = AsyncIOScheduler()

logger = get_logger(__name__)
async def scan_agent_conversations():
    print("开始扫描超时会话")
    one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
    db = async_mongo_client["langgraph"]
    cursor = await db.agent_conversations.find(
        {"status": 0,"agent_name":AGENT_NAME,"created_at":{"$lt": one_minute_ago}},
        {"thread_id": 1}
    ).to_list(length=None)

    thread_ids = [item["thread_id"] for item in cursor]

    checkpoints = await db.checkpoints.find(
        {
            "thread_id": {
                "$in": thread_ids
            }
        },
        {
            "thread_id": 1
        }
    ).to_list(length=None)
    checkpoint_thread_ids = {
        item["thread_id"] for item in checkpoints
    }
    success_ids = []
    delete_ids = []
    for conversation in cursor:
        if conversation["thread_id"] in checkpoint_thread_ids:
            success_ids.append(conversation["_id"])
        else:
            delete_ids.append(conversation["_id"])
    if success_ids:
        await db.agent_conversations.update_many(
            {
                "_id": {
                    "$in": success_ids
                },
                "status": 0
            },
            {
                "$set": {
                    "status": 1,
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        )

    if delete_ids:
        await db.agent_conversations.update_many(
            {
                "_id": {
                    "$in": delete_ids
                },
                "status": 0
            },
            {
                "$set": {
                    "status": -1,
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        )

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:

    scheduler.add_job(scan_agent_conversations, "interval", minutes=1)
    scheduler.start()
    try:
        logger.info("开始加载mongodb checkpoint")
        checkpointer = MongoDBSaver(mongo_client, db_name="langgraph")
        app.state.checkpointer = checkpointer
        logger.info("开始加载redis短期记忆")
        with RedisStore.from_conn_string(REDIS_URL) as redis_store:
            redis_store.setup()
            app.state.store = redis_store
            mcp_service = get_mcp_service(get_mcp_repository())
            try:
                logger.info("开始加载mcp_service")
                async with asyncio.timeout(60):  # 60 秒超时
                    mcp_tools = await mcp_service.load_current_tools()
            except TimeoutError:
                logger.warning("加载 MCP 工具超时")
                mcp_tools = []
            except Exception as exc:
                logger.info(f"MCP 工具加载失败，当前将不启用 MCP 工具：{exc}")
                mcp_tools = []
            logger.info("创建主agent")
            app.state.agent = await create_chat_agent(checkpointer, redis_store, mcp_tools)
            logger.info("主agent创建完毕")
            logger.info("LANGSMITH_ENDPOINT:%s",os.getenv("LANGSMITH_ENDPOINT"))
            yield
    finally:
        scheduler.shutdown()


configure_logging()
app = FastAPI(lifespan=lifespan)
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Thread-Id"],
)
app.add_middleware(AuthenticationMiddleware)
app.include_router(routerChat)
app.include_router(documents_router)
app.include_router(routerDataBase)
app.include_router(routerMcp)
app.include_router(routerSkills)
