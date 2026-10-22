"""HTTP API для Music Simplifier."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from simplifier.levels import levels_payload
from simplifier.service import process_musicxml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("music_simplifier")

app = FastAPI(
    title="Music Simplifier API",
    description="Упрощение нот MusicXML для начинающих.",
    version="1.0.0",
)

_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
allowed_origins = [origin.strip() for origin in _raw_origins.split(",") if origin.strip()]
origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX", r"https://.*\.vercel\.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=origin_regex or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class SimplifyRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1)
    level: str = Field(default="medium")


@app.get("/")
def root() -> dict:
    return {
        "service": "Music Simplifier API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "music-simplifier-api", "version": "1.0.0"}


@app.get("/api/levels")
def levels() -> dict:
    return {"levels": levels_payload()}


@app.post("/api/simplify")
async def simplify(request: SimplifyRequest) -> dict:
    try:
        return await run_in_threadpool(
            process_musicxml,
            request.filename,
            request.content_base64,
            request.level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - защита от неожиданных ошибок
        logger.exception("Ошибка обработки файла %s", request.filename)
        raise HTTPException(
            status_code=500,
            detail="Не удалось обработать файл. Проверьте, что это корректный MusicXML.",
        ) from exc
