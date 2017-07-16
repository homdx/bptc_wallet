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
port=8000

for i in `seq 1 $n`
do
    #rm -rf $i
    #mkdir $i

    ip='localhost'

    # auto-close terminal
    gnome-terminal --tab -e "/bin/bash -c 'cd $i; ../../main.py -cli -q -ip $ip -p $port -sp'"

    # don't auto-close terminal
    #gnome-terminal --tab -e "/bin/bash -c 'cd $i; ../../main.py -cli -q -ip $ip -p $port -sp; exec /bin/bash -i'"

    port=$((port+2))
done