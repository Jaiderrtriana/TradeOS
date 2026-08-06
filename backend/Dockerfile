# TradeOS backend — single containerized deployable
# (TRADEOS_SYSTEM_ARCHITECTURE.md §12.1; Master Plan Sprint 9.1).
#
# Ships application code only. Applying migrations
# (`scripts/migrate.py`) and seeding the first ScoringConfigurationVersion
# (`scripts/seed_configuration.py`) are deliberately NOT run automatically
# by this image's own CMD — see `scripts/migrate.py`'s docstring for why
# migrations and seeding are separate, independently-invoked steps, never
# baked into container startup (a multi-replica deployment must not have
# every replica racing to apply migrations on its own boot).
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# `scripts/*.py` import `app.*` as a top-level package. `python scripts/x.py`
# puts only the script's own directory on sys.path, not the working
# directory — the same reason local development docs require
# `PYTHONPATH=. poetry run python scripts/x.py`. Set once, here, so every
# script invocation inside this image (`docker exec <image> python
# scripts/migrate.py`, `scripts/seed_configuration.py`, etc.) works
# without every caller needing to remember the flag — uvicorn's own CMD
# below already resolves `app.main:app` correctly via its own import
# machinery, so this specifically closes the gap for ad hoc script runs.
ENV PYTHONPATH=/app

EXPOSE 8000

# Liveness only (TRADEOS_API_SPECIFICATION.md §6.0) — no dependency checks.
# Uses Python's own stdlib rather than adding curl, keeping the image lean.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=2)"

# No --reload: this is a production process, not a development server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
