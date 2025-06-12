FROM python:3.12-slim-bookworm AS base
WORKDIR /app
COPY poetry.lock pyproject.toml ./
RUN python -m pip install --no-cache-dir poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi --no-root

FROM python:3.12-slim-bookworm
COPY --from=base /app /app
WORKDIR /app
COPY ./src /app/src
RUN mkdir /app/db

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

CMD [".venv/bin/python", "src/main.py"]
