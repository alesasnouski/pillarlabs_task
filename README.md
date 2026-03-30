# Web Browser Annotation Tool

A full-stack web application designed to gather clicks, typing, and scrolling across web pages.
This tool serves as an interface for annotating web workflows, generating datasets that can be used to train AI agents to browse the web pages.

---

## Quick Start (Docker)

The fastest and most reliable way to get the application running locally is via Docker. The API, tracking, PostgreSQL database, and initial data seeding are fully automated.

```bash
# 1. Setup environment variables
mv .env.example .env

# 2. Add your API keys to the newly created .env file
nano .env # Important: Set your ANTHROPIC_API_KEY

# 3. Build and run the containers in the background
docker compose up -d --build
```

**4. Open the App** 
Navigate to [http://localhost:8000](http://localhost:8000) in your browser.

> **Note**: A default test user is automatically provisioned into the database for testing.
>
> - **Email:** `test@example.com`
> - **Password:** `secret`

---

## Stack

- **Backend**: Python 3.14, FastAPI
- **Database**: PostgreSQL (`SQLModel` & `SQLAlchemy`)
- **Browser**: Playwright (Chromium)
- **Frontend**: Jinja2, Alpine.js
- **Migrations**: Alembic
- **Package Manager**: `uv`
- **Testing**: `pytest`
