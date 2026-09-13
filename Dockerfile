FROM python:3.11-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY scenarios ./scenarios
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "--no-sync", "accessflow", "replay", "scenarios/dev/text_correction.json"]
