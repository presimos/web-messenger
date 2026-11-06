"""Minimal API foundation for the web messenger project."""

from fastapi import FastAPI

app = FastAPI(title="Web Messenger API", version="0.1.0")


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": "web-messenger-api", "status": "ok"}


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "healthy"}
