#!/bin/bash

port=8000

for i in `seq 1 4`
do
    #rm -rf $i
    #mkdir $i

    ip='0.0.0.0'

    # auto-close terminal
    gnome-terminal --tab -e "/bin/bash -c '../main.py -o stakeholders/$i/data -cli -ip $ip -p $port -bp localhost:8000'"

    # don't auto-close terminal
    #gnome-terminal --tab -e "/bin/bash -c '../main.py -o stakeholders/$i/data -cli -ip $ip -p $port -bp localhost:8000; exec /bin/bash -i'"

    port=$((port+2))
done
