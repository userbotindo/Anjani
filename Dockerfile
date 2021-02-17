# set base image (host OS)
FROM python:3.9

# set the working directory in the container
WORKDIR /anjani/

RUN apt -qq update && apt -qq upgrade -y
RUN apt -qq install -y --no-install-recommends \
    wget \
    git \
    gnupg2 

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY . .

# command to run on container start
CMD [ "python" "-m" "anjani_bot" ]
