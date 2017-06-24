#!/bin/bash

# clients
var=8000
for dir in *; do
	if [[ -d $dir ]]; then
		gnome-terminal --tab -e "/bin/bash -c 'cd $dir; ../../../main.py -p $var; exec /bin/bash -i'"
		var=$((var+2))
	fi
done