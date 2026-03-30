FROM python:3.14-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN uv run playwright install chromium --with-deps

COPY main.py alembic.ini ./
COPY app/ ./app/
COPY migrations/ ./migrations/

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
