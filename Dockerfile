# Set base image (host OS)
FROM python:3.9.16-slim-bullseye

# Set the working directory in the container
WORKDIR /anjani/

# Install all required packages
RUN apt-get -qq update && apt-get -qq upgrade -y
RUN apt-get -qq install -y --no-install-recommends \
    curl \
    git \
    gnupg2

# Copy directory and install dependencies
COPY . /anjani

# ignore pip root user warning
ENV PIP_ROOT_USER_ACTION=ignore

RUN pip install --upgrade pip
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

# Add poetry environment
ENV PATH="${PATH}:/root/.local/bin:$PATH"

RUN poetry config virtualenvs.create false
RUN poetry install --no-root --only main -E uvloop

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
