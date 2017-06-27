# FROM stibbons31/alpine-s6-python3-twisted
FROM jfloff/alpine-python:latest-slim
MAINTAINER Thomas Kellermeier <t-kellermeier@hotmail.de>

#-------------------------------------------------------------------------------
# Setup system(apk) dependencies
#-------------------------------------------------------------------------------

# Install deep dependencies, build packages
RUN apk add --no-cache --update \
    g++ \
    libffi-dev \
    make \
    openssl-dev \
    python3-dev \
    libsodium

# clean up
RUN rm -rf \
    /root/.cache \
    /tmp/*

#-------------------------------------------------------------------------------
# Setup application
#-------------------------------------------------------------------------------

# Expose some ports to make them accessible from outside of the container
# TODO: Later define exposed ports via docker-compose file
EXPOSE 8000
EXPOSE 8001
EXPOSE 9000
EXPOSE 9001

# Setup working directory
ENV projectPath="/home/bptc_wallet"
WORKDIR ${projectPath}
ADD . $projectPath

# Install dependencies required for CLI
RUN pip install -r requirements_cli.txt

# Start CLI interface
# CMD bash -c "python main.py -cli"
