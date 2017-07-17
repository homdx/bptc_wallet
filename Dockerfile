FROM jfloff/alpine-python:latest
MAINTAINER Thomas Kellermeier <t-kellermeier@hotmail.de>

#-------------------------------------------------------------------------------
# Setup system(apk) dependencies
#-------------------------------------------------------------------------------

# Install deep dependencies, build packages
RUN apk add --no-cache --update libsodium libffi-dev openssl-dev

#-------------------------------------------------------------------------------
# Setup application
#-------------------------------------------------------------------------------

# Setup working directory
ENV projectPath="/home/bptc_wallet"
WORKDIR ${projectPath}

# Install dependencies required for CLI
COPY requirements_cli.txt $projectPath
RUN pip install -r requirements_cli.txt
COPY . $projectPath
