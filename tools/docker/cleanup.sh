docker rm $(docker ps -a -q)
docker rmi $(docker images --quiet --filter "dangling=true")
