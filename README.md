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

To stop after passing 5000 pages:

```
$ python torspider/main.py --max-pages=5000
```

To see all available options, run:

```
$ python torspider/main.py --help
```

#### Concurrency

Default number of workers is **10**, so that even my outdated laptop
with 1.7Gib memory and AMD C-50 processor running Linux traverses 100 pages
in about 3-5 minutes. Running 50-100 workers on a contemporary MacBook gives
much better results, but after several hours its WiFi adapter breaks down. So,
consider your hardware and network capacity. This requires trial and error.

## TODOs:

1. More settings should be configurable.
1. Wiki.
1. Throttling (length of the tasks queue should not grow too quickly).
1. Pluggable design: The core should be responsible for traversing the network,
   while results should be handled by plugins.
1. Black list of domains and addresses.
1. Pauses between succedent request to the same domain.
1. Additional content types.
1. Monitoring tools.
1. Sphinx-compatiable documentation.
1. Consider GUI for common tasks.
