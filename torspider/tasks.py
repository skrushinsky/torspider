import logging
from functools import wraps
from tornado import gen
from tornadoredis import ConnectionPool, Client

MAX_CONNECTIONS = 200

PENDING_Q = 'torspider:pending_lst'
PENDING_S = 'torspider:pending_set'
WORKING_S = 'torspider:working_set'
SUCCESS_S = 'torspider:success_set'
FAILURE_S = 'torspider:failure_set'

def with_redis_pool(f):
    @wraps(f)
    async def wrapped(*args, **kw):
        obj = args[0]
        kw['client'] = Client(connection_pool=obj.pool)
        res = await f(*args, **kw)
        await gen.Task(kw['client'].disconnect)
        return res
    return wrapped


class RedisClient:
    """Class responsible for requests to Redis.
    """
    pool = None

    @classmethod
    def setup(cls,
              pending_q=PENDING_Q,
              pending_s=PENDING_S,
              working_s=WORKING_S,
              success_s=SUCCESS_S,
              failure_s=FAILURE_S,
              max_connections=MAX_CONNECTIONS,
              **conn_args):
        cls.pool = ConnectionPool(max_connections=max_connections, **conn_args)

        cls.pending_q = pending_q
        cls.pending_s = pending_s
        cls.working_s = working_s
        cls.success_s = success_s
        cls.failure_s = failure_s

        logging.debug('RedisClient ready.')

    @with_redis_pool
    async def _move_task(self, task, from_set=None, to_set=None, client=None):
        pipe = client.pipeline()
        pipe.srem(from_set, task)
        pipe.sadd(to_set, task)
        rem_res, add_res = await gen.Task(pipe.execute)
        if rem_res != 1:
            logging.error('Task %s not found in %s set', task, from_set)
        if add_res != 1:
            logging.error('Task %s not found in %s set', task, to_set)
        return rem_res, add_res

    @with_redis_pool
    async def _is_member(self, task, set_name=None, client=None):
        return await gen.Task(client.sismember, set_name, task)

    @with_redis_pool
    async def put_task(self, task, client=None):
        """Register pending task.
        Result:
        Argument is in PENDING set and PENDING queue
        """
        logging.debug('Registering <%s> as penging...', task)
        pipe = client.pipeline()
        pipe.sadd(self.pending_s, task)
        pipe.lpush(self.pending_q, task)
        return await gen.Task(pipe.execute)

    @with_redis_pool
    async def pending_count(self, client=None):
        """Pending tasks count."""
        return await gen.Task(client.scard, self.pending_s)


    @with_redis_pool
    async def get_task(self, client=None):
        """Wait for a new task in PENDING queue. When a task is available,
        pop it from the queue, then move from PENDING to WORKING set.
        Return the task.
        """
        item = await gen.Task(client.brpop, self.pending_q)
        task = item[self.pending_q]
        await self._move_task(task, self.pending_s, self.working_s)
        return task

    async def register_success(self, task):
        """Move task from WORKING to SUCCESS set.
        Return tuple of (1, 1) if operation was successfull:
        the first number is count of items deleted from the source set,
        the second is count of items adfded to the target set.
        """
        return await self._move_task(task, self.working_s, self.success_s)

    async def register_failure(self, task):
        """Move task from WORKING to FAILURE set.
        Return tuple of (1, 1) if operation was successfull:
        the first number is count of items deleted from the source set,
        the second is count of items adfded to the target set.
        """
        return await self._move_task(task, self.working_s, self.failure_s)

    @with_redis_pool
    async def passed_count(self, client=None):
        """Return sum of items in SUCCESS and FAILURE set.
        """
        pipe = client.pipeline()
        pipe.scard(self.success_s)
        pipe.scard(self.failure_s)
        res = await gen.Task(pipe.execute)
        return sum(res)


    async def is_known_task(self, task):
        """Return True if given task is member of any set,
        i.e. is registered in the system.
        """
        if await self._is_member(task, self.pending_s):
            return True
        if await self._is_member(task, self.working_s):
            return True
        if await self._is_member(task, self.success_s):
            return True
        if await self._is_member(task, self.failure_s):
            return True
        return False


    @with_redis_pool
    async def clear_all(self, client=None):
        """Clear all data structures."""
        return await gen.Task(client.delete,
                              self.pending_q,
                              self.pending_s,
                              self.working_s,
                              self.success_s,
                              self.failure_s)
