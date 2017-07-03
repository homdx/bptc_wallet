#!/bin/bash

# clients
var=8000
for dir in *; do
	if [[ -d $dir ]]; then
		gnome-terminal --tab -e "/bin/bash -c 'cd $dir; ../../../main.py -cli -p $var -sp; exec /bin/bash -i'"
		var=$((var+2))
	fi
done