docker rm $(docker ps -a -q -f dangling="true")
docker rmi $(docker images -q -f dangling="true")
