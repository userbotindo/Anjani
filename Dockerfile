# Set base image (host OS)
FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /anjani/

# Install all required packages
RUN apt-get -qq update && apt-get -qq upgrade -y
RUN apt-get -qq install -y --no-install-recommends \
    curl \
    git \
    gnupg2

# copy pyproject.toml and poetry.lock for layer caching
COPY pyproject.toml poetry.lock ./

# ignore pip root user warning
ENV PIP_ROOT_USER_ACTION=ignore

RUN pip install --upgrade pip
RUN pip install poetry

RUN poetry config virtualenvs.create false
RUN poetry install --no-root --only main -E uvloop

# copy the rest of files
COPY . .

RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
