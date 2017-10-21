#from pprint import pformat
#import logging
from tornado import gen
from tornadoredis import ConnectionPool, Client


MAX_CONNECTIONS = 20
KNOWN_DOMAINS = 'torspider:known'
TASKS_QUEUE = 'torspider:tasks'
REPORTS_HASH = 'torspider:reports'

class RedisClient:
    pool = None

    @classmethod
    def setup(cls,
              known_domains=KNOWN_DOMAINS,
              tasks_queue=TASKS_QUEUE,
              reports_hash=REPORTS_HASH,
              max_connections=MAX_CONNECTIONS,
              **conn_args):
        cls.pool = ConnectionPool(max_connections=max_connections, **conn_args)
        cls.known_domains = known_domains
        cls.tasks = tasks_queue
        cls.reports = reports_hash

    @gen.engine
    def save_domain(self, domain_name, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.sadd, self.known_domains, domain_name)
        callback(res)
        yield gen.Task(client.disconnect)

    @gen.engine
    def remove_domain(self, domain_name, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.srem, self.known_domains, domain_name)
        callback(res)
        yield gen.Task(client.disconnect)

    @gen.engine
    def is_known_domain(self, domain_name, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.sismember, self.known_domains, domain_name)
        callback(res)
        yield gen.Task(client.disconnect)

    @gen.engine
    def put_task(self, task, callback=None):
        client = Client(connection_pool=self.pool)
        #logging.info('Putting task %s to %s', task, self.tasks)
        res = yield gen.Task(client.lpush, self.tasks, task)
        callback(res)
        yield gen.Task(client.disconnect)

    @gen.engine
    def get_task(self, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.brpop, self.tasks)
        #logging.info('get_task result: %s', pformat(res))
        callback(res[self.tasks])
        yield gen.Task(client.disconnect)

    @gen.engine
    def tasks_count(self, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.llen, self.tasks)
        callback(res)
        yield gen.Task(client.disconnect)

    @gen.engine
    def save_report(self, url=None, msg=None, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.hset, self.reports, url, msg)
        callback(res)
        yield gen.Task(client.disconnect)

    @gen.engine
    def load_report(self, url=None, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.hget, self.reports, url)
        callback(res)

    @gen.engine
    def reports_count(self, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.hlen, self.reports)
        callback(res)
        yield gen.Task(client.disconnect)

    @gen.engine
    def clear_all(self, callback=None):
        client = Client(connection_pool=self.pool)
        res = yield gen.Task(client.delete, self.tasks, self.reports, self.known_domains)
        callback(res)
