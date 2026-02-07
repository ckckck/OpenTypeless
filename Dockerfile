FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DOUBAO_ASR_HOST=0.0.0.0 \
    DOUBAO_ASR_PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends libopus0 curl git g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY doubao_asr_api.py ./

EXPOSE 8000

CMD ["uv", "run", "--with", "cryptography", "doubao_asr_api.py"]
