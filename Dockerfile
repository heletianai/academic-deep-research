# Multi-Agent Academic DeepResearch
# Build:  docker build -t academic-deep-research .
# Run:    docker run --rm -e ZHIPU_API_KEY=$ZHIPU_API_KEY academic-deep-research

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Academic DeepResearch"
LABEL org.opencontainers.image.description="Multi-Agent system with Critic-Defender red-team / blue-team debate for academic survey generation"

# System deps (curl for healthcheck, no compiler needed since openai/arxiv are pure python wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
        "openai>=2.0" \
        "python-dotenv>=1.0" \
        "arxiv>=3.0" \
        "requests>=2.30" \
        "PyYAML>=6.0" \
        "matplotlib>=3.10" \
        "httpx>=0.28"

# Copy source
COPY src ./src
COPY tests ./tests
COPY scripts ./scripts
COPY configs ./configs

# Default env (override with -e at runtime)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LLM_PROVIDER=zhipu

# Default entrypoint: full pipeline demo
CMD ["python", "-m", "tests.full_pipeline_demo"]
