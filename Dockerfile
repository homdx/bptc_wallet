FROM stibbons31/alpine-s6-python3-twisted

# Expose some ports to make them accessible from outside of the container
# TODO: Later define exposed ports via docker-compose file
EXPOSE 8000
EXPOSE 8001
EXPOSE 9000
EXPOSE 9001

# Setup working directory
ENV projectPath="/home/hashgraph"
WORKDIR ${projectPath}
ADD . $projectPath

# Install deep dependencies
RUN apk update && apk --no-cache --update add libsodium

# Install dependencies required for CLI
RUN pip3 install -r requirements_cli.txt

# Start CLI interface
CMD bash -c "python3 main.py -cli"
