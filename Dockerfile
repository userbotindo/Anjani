FROM python:3.10-slim-bullseye as base

ENV POETRY_NO_INTERACTION=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_CACHE_DIR='/tmp/poetry_cache' \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get -qq update \
    && apt-get -qq install -y --no-install-recommends curl


FROM base as builder
WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN pip install --upgrade pip \
    && pip install poetry

RUN poetry install --no-root --only main -E uvloop

RUN apt-get -qq install -y --no-install-recommends git

ARG USERBOTINDO_ACCESS_TOKEN
COPY ./preinstall.sh ./
RUN chmod +x ./preinstall.sh
RUN ./preinstall.sh && rm -rf $POETRY_CACHE_DIR


FROM base as runner
WORKDIR /app

ENV VENV_PATH=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder $VENV_PATH $VENV_PATH

COPY . .

CMD ["python", "-m", "anjani"]
