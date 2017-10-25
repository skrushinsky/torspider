import logging
from tornado import gen
from tornadoredis import ConnectionPool, Client

MAX_CONNECTIONS = 200
KNOWN_URLS = 'torspider:known'
TASKS_QUEUE = 'torspider:tasks'

class RedisClient:
    """Class responsible for requests to Redis.
    """
    pool = None

    @classmethod
    def setup(cls,
              known_urls=KNOWN_URLS,
              tasks_queue=TASKS_QUEUE,
              max_connections=MAX_CONNECTIONS,
              **conn_args):
        cls.pool = ConnectionPool(max_connections=max_connections, **conn_args)
        cls.known_urls = known_urls
        cls.tasks = tasks_queue
        logging.debug('RedisClient ready.')


    async def save_visit(self, url):
        client = Client(connection_pool=self.pool)
        res = await gen.Task(client.sadd, self.known_urls, url)
        await gen.Task(client.disconnect)
        return res

    async def pages_count(self):
        client = Client(connection_pool=self.pool)
        res = await gen.Task(client.scard, self.known_urls)
        await gen.Task(client.disconnect)
        return res

    async def forget_visit(self, url):
        client = Client(connection_pool=self.pool)
        res = await gen.Task(client.srem, self.known_urls, url)
        await gen.Task(client.disconnect)
        return res

    async def is_known_address(self, url):
        client = Client(connection_pool=self.pool)
        res = await gen.Task(client.sismember, self.known_urls, url)
        await gen.Task(client.disconnect)
        return res

    async def put_task(self, task):
        client = Client(connection_pool=self.pool)
        logging.debug('%s --> %s', task, self.tasks)
        res = await gen.Task(client.lpush, self.tasks, task)
        await gen.Task(client.disconnect)
        return res

    async def get_task(self):
        client = Client(connection_pool=self.pool)
        logging.debug('Waiting for a task...')
        res = await gen.Task(client.brpop, self.tasks)
        await gen.Task(client.disconnect)
        return res[self.tasks]

    async def tasks_count(self):
        client = Client(connection_pool=self.pool)
        res = await gen.Task(client.llen, self.tasks)
        await gen.Task(client.disconnect)
        return res

    async def clear_all(self):
        client = Client(connection_pool=self.pool)
        res = await gen.Task(client.delete, self.tasks, self.known_urls)
        await gen.Task(client.disconnect)
        return res
