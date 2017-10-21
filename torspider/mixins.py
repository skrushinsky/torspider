import logging
from datetime import datetime

from tornado import gen
from tornadoredis import ConnectionPool, Client
import motor
import pymongo

MAX_CONNECTIONS = 20
KNOWN_URLS = 'torspider:known'
TASKS_QUEUE = 'torspider:tasks'
REPORTS_COLLECTION = 'reports'

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


class MongoClient:
    @classmethod
    def setup(cls, connection_str=None, reports_collection=REPORTS_COLLECTION, io_loop=None):
        dbname = connection_str.split('/')[-1]
        dbconn =  '/'.join(connection_str.split('/')[:-1])
        logging.info('Connecting to database: %s...', dbname)
        conn = pymongo.MongoClient(connection_str)
        client = conn[dbname]
        client[REPORTS_COLLECTION].create_index('url', name='url_unique', unique=True, background=True )
        client[REPORTS_COLLECTION].create_index('ts', name='ts', unique=True, background=True )

        if io_loop:
            conn = motor.motor_tornado.MotorClient(dbconn, io_loop=io_loop)
        else:
            conn = motor.motor_tornado.MotorClient(dbconn)
        cls.db = conn[dbname]
        logging.info('Ready for asyncroneous connections to %s', connection_str)
        cls.reports = reports_collection
        logging.debug('MongoClient ready.')

    async def save_report(self, task):
        report = {
            'ts': datetime.utcnow(),
            'url': task['url']
        }
        if 'error' in task:
            report['error'] = task['error']
            msg = 'failure '
        else:
            report['page'] = task['page']
            msg = ''
        res = await self.db[self.reports].update_one(
            {'url': task['url']},
            {'$set': report},
            upsert=True
        )
        if res.upserted_id:
            logging.info('Inserted %sreport for %s', msg, task['url'])
        return res.upserted_id

    async def reports_count(self):
        return await self.db[self.reports].count()
