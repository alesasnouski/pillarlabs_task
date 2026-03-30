POSTGRES_DB       ?= annotation_tool
POSTGRES_USER     ?= annotation
POSTGRES_PASSWORD ?= annotation
POSTGRES_HOST     ?= localhost
POSTGRES_PORT     ?= 5432

DATABASE_URL = postgresql+asyncpg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)

psql:
	PGPASSWORD=$(POSTGRES_PASSWORD) psql -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) -U $(POSTGRES_USER) -d $(POSTGRES_DB)

migrate:
	DATABASE_URL=$(DATABASE_URL) uv run alembic upgrade head

test:
	uv run pytest tests/ -v