#from pprint import pformat
import logging
from datetime import datetime

from tornado import gen
from tornadoredis import ConnectionPool, Client
import motor
import pymongo

MAX_CONNECTIONS = 20
KNOWN_DOMAINS = 'torspider:known'
TASKS_QUEUE = 'torspider:tasks'
REPORTS_COLLECTION = 'reports'

class RedisClient:
    """Class responsible for requests to Redis.
    """
    pool = None

    @classmethod
    def setup(cls,
              known_domains=KNOWN_DOMAINS,
              tasks_queue=TASKS_QUEUE,
              max_connections=MAX_CONNECTIONS,
              **conn_args):
        cls.pool = ConnectionPool(max_connections=max_connections, **conn_args)
        cls.known_domains = known_domains
        cls.tasks = tasks_queue


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
