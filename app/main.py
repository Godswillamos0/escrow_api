from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import models, database
from api.v1 import router
from redis import asyncio as aioredis
from contextlib import asynccontextmanager


# Create tables
models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
    app.state.redis = await aioredis.from_url("redis://localhost")
    yield
    # on shutdown
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    router=router.router,
    )