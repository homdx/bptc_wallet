# Get IP and DNS in HPI network
# https://byod.hpi.de/

# Run registry and return its assigned IP
# docker inspect $(docker run -tdi -p 9000:9000 --name br1 chaoste/bptc:registry) -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# docker run --tty --interactive -v ~/Documents/Uni/SS17/hashgraph/data:/home/hashgraph/data chaoste/bptc
docker run -tdi -p 9000:9000 -p 9001:9001 --name br1 chaoste/bptc:registry
docker run -tdi -p 8000:8000 -p 8001:8001 --name bac1 chaoste/bptc:auto_client
docker run -tdi -p 8002:8002 -p 8003:8003 --name bc1 chaoste/bptc:cli
