#!/bin/bash

port=8000

for i in `seq 1 4`
do
    #rm -rf $i
    #mkdir $i

    ip='0.0.0.0'

    # auto-close terminal
    gnome-terminal --tab -e "/bin/bash -c 'cd stakeholders/$i; ../../../main.py -cli -ip $ip -p $port -sp'"

    # don't auto-close terminal
    #gnome-terminal --tab -e "/bin/bash -c 'cd stakeholders/$i; ../../../main.py -cli -q -ip $ip -p $port -sp; exec /bin/bash -i'"

    port=$((port+2))
done
