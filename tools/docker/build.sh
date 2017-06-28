docker build . -f tools/docker/images/bptc -t chaoste/bptc:bptc -t chaoste/bptc:lates
docker push chaoste/bptc:bptc
docker build . -f tools/docker/images/cli -t chaoste/bptc:cli
docker push chaoste/bptc:cli
docker build . -f tools/docker/images/registry -t chaoste/bptc:registry
docker push chaoste/bptc:registry
docker build . -f tools/docker/images/auto_client -t chaoste/bptc:auto_client
docker push chaoste/bptc:auto_client
# docker push chaoste/bptc
