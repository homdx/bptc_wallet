# docker run --tty --interactive -v ~/Documents/Uni/SS17/hashgraph/data:/home/hashgraph/data chaoste/bptc
docker run -tdi -p 9000:9000 -p 8001:8001 --name br1 chaoste/bptc:registry
docker run -tdi -p 8000:8000 -p 8001:8001 --name bac1 chaoste/bptc:auto_client
