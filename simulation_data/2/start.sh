#!/bin/bash

# registry
gnome-terminal --tab -e "/bin/bash -c 'python3 ../../member_registry.py; exec /bin/bash -i'"

# clients
var=8000
for dir in *; do
	if [[ -d $dir ]]; then
		gnome-terminal --tab -e "/bin/bash -c 'cd $dir; python3 ../../../main.py -p $var; exec /bin/bash -i'"
		var=$((var+2))
	fi
done