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

for i in `seq 1 $n`
do
    rm -rf members/$i
    mkdir members/$i

    ip='localhost'

    # auto-close terminal
    gnome-terminal --tab -e "/bin/bash -c 'cd members/$i; ../../../main.py -cli -q -ip $ip -p $port -sp -bp localhost:8000'"

    # don't auto-close terminal
    #gnome-terminal --tab -e "/bin/bash -c 'cd members/$i; ../../../main.py -cli -q -ip $ip -p $port -sp -bp localhost:8000; exec /bin/bash -i'"

    port=$((port+2))
done