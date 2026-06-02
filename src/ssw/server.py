from fastapi import FastAPI

from ssw.api.database import routerDataBase

app = FastAPI()

app.include_router(routerDataBase)