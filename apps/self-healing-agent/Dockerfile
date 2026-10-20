FROM python:3.12-slim AS base

WORKDIR /app

# Multi-stage so the shipped image only carries the installed deps, not
# pip's build cache — matches the "multi-stage Docker images" work this
# project draws on from production.
FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/deps -r requirements.txt

FROM base AS runtime
COPY --from=deps /deps /usr/local/lib/python3.12/site-packages
COPY src/ ./src/

RUN useradd --no-create-home --shell /usr/sbin/nologin agent
USER agent

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "src/main.py"]
