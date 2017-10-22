# torspider

Fast asynchroneous web-crawler based on [Tornado framework](http://tornadoweb.org).
Tested on OSX and Linux.

## Usage

### Prerequisits

* Python >= 3.5
* Redis server
* MongoDB

### Installation

#### Required packages

To install required Python packages, run from the project root:

```
$ pip install -r requirements.txt
```

#### Testing

Run unit tests one by one:

```
$ python tests/test_urlnorm.py
$ python tests/test_scraper.py
$ python tests/test_mixins.py
```

#### Configuration

1. Copy **conf/default.conf** to **conf/local.conf** and edit the latter.
1. To provide initial URLs, edit **conf/seeds.txt** file.

Please, note: options from command line override those from the configuration file.


### Running

```
$ python torspider/main.py
```

With extra logging:

```
$ python torspider/main.py --logging=debug
```

With 50 asynchroneous workers:

```
$ python torspider/main.py --workers=50
```

To stop after passing 200 pages:

```
$ python torspider/main.py --workers=50
```

To see all available options, run:

```
$ python torspider/main.py --help
```


## TODOs:

1. More settings should be configurable.
1. Throttling (tasks queue should be )
1. Make it pluggable: The core should be responsible for traversing the network,
   while results should be handled by plugins.
1. Handle additional content types.
1. GUI.
