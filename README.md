# torspider

Fast asynchronous web-crawler based on [Tornado framework](http://tornadoweb.org).

Tested on:

* MacOSX
* Debian-based Linux.

## Usage

### Prerequisites

* Unix
* Python >= 3.5
* Redis server

### Installation

#### Required packages

To install required Python packages, run from the project root:

```
$ python setup.py install develop
```

Linux installation may require additional steps for building
[pycurl](http://pycurl.io) with SSL support. If so, you may find more convenient
to install the dependencies before running **setup.py** :

```
$ pip install -r requirements.txt
```

If it fails at some stage because of a missing system package, install the
system package manually with your standard package manager (apt, yum, etc.),
then repeat the above command.

#### Testing

To run all the unit tests:

```
$ python -m unittest discover tests/ -p test_*.py
```

#### Configuration

Default configuration file is named **default.conf**. To override any of its
predefined settings, put desired key/value pair to **local.conf** or
provide an alternative via command-line option. The rule is simple:

* Options from **local.conf** override those from  **default.conf**.
* Options from command line override those from both the configuration files.

To see all available command-line options, run:

See also [the detailed options description](https://github.com/skrushinsky/torspider/wiki/Options).


```
$ torspider --help
```

##### Seeds

To provide initial URLs, edit **seeds.conf** file. If you do not provide any
**seeds**, the program will be able only to continue previous session. If there
were no previous sessions, or you start torspider with **--clear-tasks** option,
there won't be any tasks for workers.

##### Enabling Plugins

**plugins.conf** file contains list of available plugins. To disable a plugin,
comment it out with **#** symbol, like that:

```
# mongo_client
```


### Running

```
$ torspider
```

With extra logging:

```
$ torspider --logging=debug
```

With 50 asynchronous workers:

```
$ torspider --workers=50
```

To stop after passing 5000 pages:

```
$ torspider --max-pages=5000
```

To clear all data from previous session:

```
$ torspider --clear-tasks
```


## Extending

The program is *pluggable*. Briefly speaking, its primary responsibility is to
traverse the network following a set of rules. **How to use the results** is
entirely up to plugins. In one scenario each page must be parsed and saved
to a database. Another scenario requires extracting some special information
from the page, such as stock prices.

See [Wiki article](https://github.com/skrushinsky/torspider/wiki/Extending).

- - -

## TODOs

1. More entry points for plugins, e.g. let them control where to go from a page.
1. More configurable settings, at the first place: request headers.
1. Black list of domains / addresses.
1. Pauses between succedent request to the same domain.
1. Additional content types.
1. Monitoring tools.
1. Sphinx-compatiable documentation.
