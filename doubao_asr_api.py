#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi>=0.109.0",
#     "uvicorn[standard]>=0.27.0",
#     "python-multipart>=0.0.6",
#     "pydantic>=2.5.0",
#     "pydantic-settings>=2.1.0",
#     "doubaoime-asr",
# ]
#
# [tool.uv.sources]
# doubaoime-asr = { git = "https://github.com/starccy/doubaoime-asr" }
# ///
"""
OpenTypeless - Standalone single-file edition.

OpenAI-compatible Speech-to-Text API powered by Doubao IME ASR.

Run:
    uv run doubao_asr_api.py

Environment:
    通过 .env 文件或者 环境变量配置参数：
    | 变量 | 默认值 | 说明 |
    |------|--------|------|
    | `DOUBAO_ASR_HOST` | `127.0.0.1` | 监听地址 |
    | `DOUBAO_ASR_PORT` | `8000` | 监听端口 |
    | `DOUBAO_ASR_DEBUG` | `false` | 调试模式（启用 API 文档） |
    | `DOUBAO_ASR_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
    | `DOUBAO_ASR_CREDENTIAL_PATH` | `./credentials.json` | 凭据文件路径 |
    | `DOUBAO_ASR_API_KEY` | — | API 密钥（可选），不设置时允许所有请求 |
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, List, Optional

from doubaoime_asr import ASRConfig, ResponseType, transcribe_stream
from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

__version__ = "0.1.0"


# =============================================================================
# Config
# =============================================================================

class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    credential_path: str = "./credentials.json"
    device_id: Optional[str] = None
    token: Optional[str] = None
    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 20
    api_key: Optional[str] = None

    model_config = {"env_prefix": "DOUBAO_ASR_", "env_file": ".env"}


settings = Settings()


# =============================================================================
# Logging
# =============================================================================

def setup_logging():
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    fmt = "[%(asctime)s] %(levelname)s %(name)s - %(message)s"
    if level == logging.DEBUG:
        fmt = "[%(asctime)s] %(levelname)s %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    logger = logging.getLogger("doubao_asr_api")
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


logger = setup_logging()


# =============================================================================
# Models
# =============================================================================

class ResponseFormat(str, Enum):
    JSON = "json"
    TEXT = "text"
    SRT = "srt"
    VERBOSE_JSON = "verbose_json"
    VTT = "vtt"


class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="The transcribed text.")


class VerboseTranscriptionResponse(BaseModel):
    task: str = "transcribe"
    language: str = "zh"
    duration: float = 0.0
    text: str


class ErrorResponse(BaseModel):
    error: dict


# =============================================================================
# Service
# =============================================================================

class ASRService:
    def __init__(self):
        self._config: Optional[ASRConfig] = None

    @property
    def config(self) -> ASRConfig:
        if self._config is None:
            kwargs = {
                "credential_path": settings.credential_path,
                "sample_rate": settings.sample_rate,
                "channels": settings.channels,
                "frame_duration_ms": settings.frame_duration_ms,
            }
            if settings.device_id:
                kwargs["device_id"] = settings.device_id
            if settings.token:
                kwargs["token"] = settings.token
            self._config = ASRConfig(**kwargs)
        return self._config

    async def transcribe(self, audio_data: bytes) -> str:
        size = len(audio_data)
        logger.info("Starting transcription: audio_size=%.1f KB", size / 1024)

        final_texts: List[str] = []
        async for response in transcribe_stream(audio_data, config=self.config, realtime=False):
            logger.debug("ASR response: type=%s, text=%r", response.type, getattr(response, "text", None))
            if response.type == ResponseType.FINAL_RESULT:
                final_texts.append(response.text or "")
                logger.info("Final result: %r", response.text)
            elif response.type == ResponseType.ERROR:
                raise RuntimeError(f"ASR error: {response.error_msg}")

        result = "".join(final_texts)
        logger.info("Transcription complete: %d segment(s), total_length=%d", len(final_texts), len(result))
        return result


asr_service = ASRService()


# =============================================================================
# Routes
# =============================================================================

def verify_api_key(authorization: Annotated[Optional[str], Header()] = None):
    if not settings.api_key:
        return True
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": {"message": "Missing Authorization header"}})
    key = authorization[7:] if authorization.startswith("Bearer ") else authorization
    if key != settings.api_key:
        raise HTTPException(status_code=401, detail={"error": {"message": "Invalid API key"}})
    return True


router = APIRouter(prefix="/v1/audio", dependencies=[Depends(verify_api_key)])


def format_srt(text: str) -> str:
    return f"1\n00:00:00,000 --> 00:00:00,000\n{text}\n"


def format_vtt(text: str) -> str:
    return f"WEBVTT\n\n1\n00:00:00.000 --> 00:00:00.000\n{text}\n"


@router.post("/transcriptions")
async def transcribe(
    file: Annotated[UploadFile, File()],
    model: Annotated[str, Form()] = "doubao-asr",
    response_format: Annotated[ResponseFormat, Form()] = ResponseFormat.JSON,
    language: Annotated[Optional[str], Form()] = None,
    prompt: Annotated[Optional[str], Form()] = None,
    temperature: Annotated[Optional[float], Form()] = None,
):
    logger.info("Request: filename=%s, format=%s", file.filename, response_format.value)
    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail={"error": {"message": "Empty audio file"}})

    text = await asr_service.transcribe(audio_data)
    logger.info("Result: length=%d", len(text))

    match response_format:
        case ResponseFormat.TEXT:
            return PlainTextResponse(content=text)
        case ResponseFormat.SRT:
            return PlainTextResponse(content=format_srt(text))
        case ResponseFormat.VTT:
            return PlainTextResponse(content=format_vtt(text), media_type="text/vtt")
        case ResponseFormat.VERBOSE_JSON:
            return VerboseTranscriptionResponse(text=text, language=language or "zh")
        case _:
            return TranscriptionResponse(text=text)


# =============================================================================
# App
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OpenTypeless v%s", __version__)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="OpenTypeless",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "healthy", "version": __version__}


@app.get("/v1/models")
async def models() -> Dict[str, Any]:
    return {"object": "list", "data": [{"id": "doubao-asr", "object": "model"}]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
