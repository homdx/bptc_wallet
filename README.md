# BPT Hashgraph

## Setup Linux
```shell
  sudo apt install cython python3-dev libffi-dev libgl1-mesa-dev
  pip install -r requirements.txt
```
You also need the libsodium.so for libnacl - Therefore download it from [here](https://download.libsodium.org/libsodium/releases/).
If you only want to run the application via the CLI you don't have to install all modules
named in requirements.txt. Instead you can use requirements_cli.txt.

## Start UI client
```shell
  python main.py
```

## Start CLI client
```shell
  python main.py -cli
```



## Docker

There is a dockerfile which sets up all command line dependencies (e.g. not kivy) and a docker-compose file defining a network of 3 clients interacting with each other.
You can find detailed descriptions on how to use docker in our repository in the wiki.

##### Build docker image
```shell
  docker build . -t chaoste/bptc
```


## Build Android package
Install Buildozer following the instructions on its Github page. Note the difference between
installation for Python 2 and Python 3.

Look at the [documentation](http://buildozer.readthedocs.io/en/latest/installation.html)
for installing the right dependencies for your OS. Buildozer and its dependency Crystax
NDK require about 15 GB disk space.

After setting up Buildozer run:

```shell
  buildozer android debug deploy run
```

## Execution
Starting bokeh
```shell
  bokeh serve viz.py
```

Starting bokeh and browser
```shell
  bokeh serve --show viz.py
```

## Debugging
Start registry, multiple clients and bokeh on Windows:
```
  tools\scripts\start_clients
```
The clients will automatically start listening on events, register at the
registry and query other members.