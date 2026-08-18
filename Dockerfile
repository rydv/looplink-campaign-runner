FROM node:22-bookworm-slim AS frontend

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY webpack ./webpack
COPY styles ./styles
COPY looplink ./looplink
COPY bundled_assets ./bundled_assets
RUN npm run build


FROM python:3.13-slim AS application

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.7"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . ./
COPY --from=frontend /app/webpack/_build ./webpack/_build

EXPOSE 8000

CMD ["sh", "docker/web-entrypoint.sh"]
