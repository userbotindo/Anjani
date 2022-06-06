# Set base image (host OS)
FROM python:3.9.13-slim-bullseye

# Set the working directory in the container
WORKDIR /anjani/

# Install all required packages
RUN apt-get -qq update && apt-get -qq upgrade -y
RUN apt-get -qq install -y --no-install-recommends \
    wget \
    curl \
    git \
    gnupg2 \
    imagemagick \
    apt-transport-https \
    libjpeg-turbo-progs \
    libpng-dev \
    libwebp-dev

# Set for tesseract repository
RUN gpg --keyserver keyserver.ubuntu.com --recv-keys 82F409933771AC78
RUN gpg --output /root/82F409933771AC78.gpg --export 82F409933771AC78
RUN mv /root/82F409933771AC78.gpg /etc/apt/trusted.gpg.d/
RUN echo "deb https://notesalexp.org/tesseract-ocr5/bullseye/ bullseye main" \
    | tee /etc/apt/sources.list.d/notesalexp.list > /dev/null
RUN apt-get update -oAcquire::AllowInsecureRepositories=true
RUN apt-get install notesalexp-keyring -oAcquire::AllowInsecureRepositories=true
RUN apt-get -qq update && apt-get -qq upgrade -y
RUN apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-osd \
    tesseract-ocr-eng \
    tesseract-ocr-ind \
    libarchive13

# Copy directory and install dependencies
COPY . /anjani
RUN pip install --upgrade pip
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

# Add poetry environment
ENV PATH="${PATH}:/root/.local/bin:$PATH"

RUN poetry config virtualenvs.create false
RUN poetry install --no-root --no-dev -E all

# Command to run when container started
CMD ["python3", "-m", "anjani"]
