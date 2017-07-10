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
var=8000

for i in `seq 1 $n`
do
    rm -rf $i
    mkdir $i
    # auto-close terminal
    gnome-terminal --tab -e "/bin/bash -c 'cd $i; ../../main.py -p $var -sp -bp localhost:8000 -cli'"
    # don't auto-close terminal
    #gnome-terminal --tab -e "/bin/bash -c 'cd $i; ../../main.py -p $var -sp -bp localhost:8000 -cli; exec /bin/bash -i'"
    var=$((var+2))
done