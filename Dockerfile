# Set base image (host OS)
FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /anjani/

# Install all required packages
RUN apt-get -qq update && apt-get -qq upgrade -y
RUN apt-get -qq install -y --no-install-recommends \
    git

# copy pyproject.toml and poetry.lock for layer caching
COPY pyproject.toml poetry.lock ./

# ignore pip root user warning
ENV PIP_ROOT_USER_ACTION=ignore

RUN pip install --upgrade pip \
    && pip install poetry

RUN poetry install --no-root --only main -E uvloop

ARG USERBOTINDO_ACCESS_TOKEN
COPY ./entrypoint.sh ./
RUN chmod +x ./entrypoint.sh
RUN ./entrypoint.sh

# copy the rest of files
COPY . .

CMD ["poetry", "run", "anjani"]
