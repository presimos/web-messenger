from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app import models
from app.auth import router as auth_router
from app.messaging import router as messaging_router, websocket_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Web Messenger API", version="0.4.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(messaging_router)
app.include_router(websocket_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": "web-messenger-api", "status": "ok"}


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "healthy"}
