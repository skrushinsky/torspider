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
to install dependencies before running **setup.py** :

```
$ pip install -r requirements.txt
```

If it fails at some stage because of a missing system package, install the
system package manually with your standard package manager (apt, yum, etc.),
then repeat the above command.

#### Testing

Run unit tests:

```
$ python -m unittest discover tests/ -p test_*.py
```

#### Configuration

Default configuration file is named **default.conf**. To override any of its
predefined settings, put the same key with desired value to **local.conf** or
provide an alternative via command line option. The rule is simple:

* Options from **local.conf** override those from  **default.conf**.
* Options from command line override those from both the configuration files.

To see all available options, run:

```
$ torspider --help
```

##### Seeds

To provide initial URLs, edit **seeds.conf** file. If you do not provide any
**seeds**, the program will be able only to continue previous session. If there
were no previous sessions, or you start torspider with **--clear-tasks** option,
there won't be any tasks for workers.

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
traverse the network following a set of rules. But **how to use the results**,
is up to the plugins. For instance, in one user scenario each page must be
parsed and saved to a database. Another scenario requires extracting some special
information from the page, such as stock prices.

### Entry points

Pluggability is based on [setuptools](https://setuptools.readthedocs.io/en/latest/)
**entry points**. Please, see **setup.py** file.

```
entry_points = {
    ...
    'torspider_init': [],
    'torspider_consume': [],
    'torspider_done': [],
}
```

An external Python application may declare in its **setup.py** the same entry
points and register functions that implement some business logging. For instance,
**torspider-mongo** plugin saves report to [MongoDB](https://docs.mongodb.com/manual/).
 It has following lines in its setup:

```
entry_points = {
    # see: http://amir.rachum.com/blog/2017/07/28/python-entry-points/
    'torspider_init': [
        'mongo_client_init = torspidermongo:init_client',
    ],
    'torspider_consume': [
        'mongo_client_save = torspidermongo:save_report',
    ],
})
```

The entry points are kind of hooks. Currently, the application supports the
following entry points.

#### torspider_init

Initialization. Any configuration steps required by the plugin. such as Connecting
to a database, should be done here. The application calls this before starting workers.

#### torspider_consume

Called by the workers after successfull or unsuccessfull request. The handler
function will be called with a dictionary, consisting of:

* **url** : absolute URL-address of the task/
* **error** : the field is present only if the request failed; contains the error message
* **page** : the fiels is present only if the request succeeded; the object may be queried for
             misc. page attributes: title, text, meta-tags. language etc. (see below)

#### torspider_done

Callback for any clean-up actions.

- - -
In future the list of extension points will probably grow.

### Page object

Object, passed to consumer functions. Contains properties of successfully loaded
page.

#### Available properties

* **url**: the task (in case of redirects may differ from **response.effective_url**)
* **response**: tornado.httpclient.HTTPResponse object
* **soup**: [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) object
* **base**: base address of the page
* **title**: page title
* **meta**: dictionary of meta-tags
* **text**: page content as plain text
* **language**: content language (two-letter code)
* **links**: dictionary of inner and outer links from the page:
             `{'inner': [...], `outer`: [...] }`
* **language**: content language (two-letter code)
* **headers**: important HTTP response headers

NOTE: most of the properties are initialized lazily. E.g., if **language** will not be detected
until you read **page.language** property.

#### Useful methods

* **as_dict()**: returns dictionary, containing all page attributes, which
                  maty be futher serialized.





See:

* http://amir.rachum.com/blog/2017/07/28/python-entry-points/
* https://packaging.python.org/guides/creating-and-discovering-plugins/


#### Concurrency

Default number of workers is **10**, so that even my outdated laptop
with 1.7Gib memory and AMD C-50 processor running Linux with moderate WiFi
connection traverses 100 pages in about 3-5 minutes. Running 50-100 workers on
a contemporary MacBook gives much better results, but after several hours its
WiFi adapter breaks down. So, consider your hardware and network capacity.
This requires trial and error.

Also, tasks may be executed by a number of processes running in parallel. Example
of starting 10 separate processes:

```
$ seq 10 | xargs -Iz -P10 torspider
```
Of course, this is an extreme case!


## TODOs:

1. More configurable settings.
1. Wiki.
1. Throttling: length of the tasks queue should not grow too quickly.
1. Black list of domains / addresses.
1. Pauses between succedent request to the same domain.
1. Additional content types.
1. Monitoring tools.
1. Sphinx-compatiable documentation.
