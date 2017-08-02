#!/bin/bash

usage()
{
    echo "Usage: $0 <n>"
    exit 1
}

if [ $# -ne 1 ]
then
    usage
fi

n=$1
port=8008

mkdir users

for i in `seq 1 $n`
do
    rm -rf users/$i
    mkdir users/$i

    ip='0.0.0.0'

    # auto-close terminal
    gnome-terminal --tab -e "/bin/bash -c '../main.py -o users/$i/data -cli -ip $ip -p $port -bp localhost:8000'"

    # don't auto-close terminal
    #gnome-terminal --tab -e "/bin/bash -c '../main.py -o users/$i/data -cli -ip $ip -p $port -bp localhost:8000; exec /bin/bash -i'"

    port=$((port+2))
done