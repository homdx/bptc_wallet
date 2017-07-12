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
    rm -rf $i
    mkdir $i
    #ip='192.168.'
    #ip+=$i
    #ip+='.1'
    ip='192.168.0.100'

    # auto-close terminal
    gnome-terminal --tab -e "/bin/bash -c 'cd $i; ../../main.py -cli -ip $ip -p $port -q -sp -bp localhost:8000'"
    # don't auto-close terminal
    #gnome-terminal --tab -e "/bin/bash -c 'cd $i; ../../main.py -cli -ip $ip -p $port -q -sp -bp localhost:8000; exec /bin/bash -i'"
    
    port=$((port+2))
done