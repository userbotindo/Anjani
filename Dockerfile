# set base image (host OS)
FROM python:3.9

# set the working directory in the container
WORKDIR /anjani/

RUN apt -qq update && apt -qq upgrade -y
RUN apt -qq install -y --no-install-recommends \
    wget \
    git \
    gnupg2 

# Copy directory and install dependencies
COPY . .
RUN pip install --upgrade pip
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH="${PATH}:/root/.poetry/bin"

RUN poetry config virtualenvs.create false
RUN poetry install --no-root --no-dev -E uvloop

# command to run on container start
CMD ["python3","-m","anjani_bot"]
