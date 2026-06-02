from fastapi import APIRouter

routerDataBase = APIRouter(prefix="/database", tags=["数据库管理"])


@routerDataBase.get("/info")
async def user_info():
    return {"type": "mysql"}