import sys
import logging
from functools import partial
import unittest
from tornado import testing
import redis as pyredis
from torspider import tasks

PENDING_Q = 'torspider:test:pending_lst'
PENDING_S = 'torspider:test:pending_set'
WORKING_S = 'torspider:test:working_set'
SUCCESS_S = 'torspider:test:success_set'
FAILURE_S = 'torspider:test:failure_set'


class TaskCase(testing.AsyncTestCase):
    sync_redis = pyredis.StrictRedis()

    def setUp(self):
        logging.debug('setUp')
        super(TaskCase, self).setUp()
        tasks.RedisClient.setup(
            pending_q=PENDING_Q,
            pending_s=PENDING_S,
            working_s=WORKING_S,
            success_s=SUCCESS_S,
            failure_s=FAILURE_S,
            io_loop=self.io_loop)
        self.client = tasks.RedisClient()

    def tearDown(self):
        logging.debug('tearDown')
        super(TaskCase, self).tearDown()
        self.sync_redis.delete(PENDING_Q)
        self.sync_redis.delete(PENDING_S)
        self.sync_redis.delete(WORKING_S)
        self.sync_redis.delete(SUCCESS_S)
        self.sync_redis.delete(FAILURE_S)


class PutTaskCase(TaskCase):
    def setUp(self):
        super(PutTaskCase, self).setUp()
        self.task = 'http://tornadoweb.org/'
        f = partial(self.client.put_task, self.task)
        self.io_loop.run_sync(f)

    @testing.gen_test
    def test_queue(self):
        self.assertEqual(self.sync_redis.llen(PENDING_Q), 1)

    @testing.gen_test
    def test_set(self):
        self.assertTrue(self.sync_redis.sismember(PENDING_S, self.task))


class GetTaskCase(TaskCase):
    def setUp(self):
        super(GetTaskCase, self).setUp()
        self.task = 'http://tornadoweb.org/'
        f = partial(self.client.put_task, self.task)
        self.io_loop.run_sync(f)

    @testing.gen_test
    def test_queue(self):
        task = yield self.client.get_task()
        self.assertEqual(self.task, task)

    @testing.gen_test
    def test_pending_set(self):
        yield self.client.get_task()
        self.assertFalse(self.sync_redis.sismember(PENDING_S, self.task))

    @testing.gen_test
    def test_working_set(self):
        yield self.client.get_task()
        self.assertTrue(self.sync_redis.sismember(WORKING_S, self.task))

class RegisterSuccessCase(TaskCase):
    """
    Put task to the queue, gt it back, then register as 'passed'.
    Make sure, data structures are in proper state.
    """
    def setUp(self):
        super(RegisterSuccessCase, self).setUp()
        self.task = 'http://tornadoweb.org/'
        self.io_loop.run_sync(partial(self.client.put_task, self.task))

    async def _get_and_register(self):
        task = await self.client.get_task()
        await self.client.register_success(task)

    @testing.gen_test
    def test_tasks_queue(self):
        yield self._get_and_register()
        self.assertEqual(0, self.sync_redis.llen(PENDING_Q))

    @testing.gen_test
    def test_pending_set(self):
        yield self._get_and_register()
        self.assertFalse(self.sync_redis.sismember(PENDING_S, self.task))

    @testing.gen_test
    def test_working_set(self):
        yield self._get_and_register()
        self.assertFalse(self.sync_redis.sismember(WORKING_S, self.task))

    @testing.gen_test
    def test_success_set(self):
        yield self._get_and_register()
        self.assertTrue(self.sync_redis.sismember(SUCCESS_S, self.task))

    @testing.gen_test
    def test_failure_set(self):
        yield self._get_and_register()
        self.assertFalse(self.sync_redis.sismember(FAILURE_S, self.task))


class RegisterFailureCase(TaskCase):
    """
    Put task to the queue, gt it back, then register as 'failed'.
    Make sure, data structures are in proper state.
    """
    def setUp(self):
        super(RegisterFailureCase, self).setUp()
        self.task = 'http://tornadoweb.org/'
        self.io_loop.run_sync(partial(self.client.put_task, self.task))

    async def _get_and_register(self):
        task = await self.client.get_task()
        await self.client.register_failure(task)

    @testing.gen_test
    def test_tasks_queue(self):
        yield self._get_and_register()
        self.assertEqual(0, self.sync_redis.llen(PENDING_Q))

    @testing.gen_test
    def test_pending_set(self):
        yield self._get_and_register()
        self.assertFalse(self.sync_redis.sismember(PENDING_S, self.task))

    @testing.gen_test
    def test_working_set(self):
        yield self._get_and_register()
        self.assertFalse(self.sync_redis.sismember(WORKING_S, self.task))

    @testing.gen_test
    def test_success_set(self):
        yield self._get_and_register()
        self.assertFalse(self.sync_redis.sismember(SUCCESS_S, self.task))

    @testing.gen_test
    def test_failure_set(self):
        yield self._get_and_register()
        self.assertTrue(self.sync_redis.sismember(FAILURE_S, self.task))


class PassedCountCase(TaskCase):
    def setUp(self):
        self.sync_redis.sadd(SUCCESS_S, 'http://example.com/a/1')
        self.sync_redis.sadd(FAILURE_S, 'http://example.com/b/2')
        super(PassedCountCase, self).setUp()

    @testing.gen_test
    def test_count(self):
        count = yield self.client.passed_count()
        self.assertEqual(2, count)

class PendingCountCase(TaskCase):
    def setUp(self):
        super(PendingCountCase, self).setUp()
        self.task = 'http://tornadoweb.org/'
        f = partial(self.client.put_task, self.task)
        self.io_loop.run_sync(f)

    @testing.gen_test
    def test_count(self):
        count = yield self.client.pending_count()
        self.assertEqual(1, count)



class KnownTaskCase(TaskCase):
    """Make sure the a registered task is 'known' in any state."""
    def setUp(self):
        super(KnownTaskCase, self).setUp()
        self.task = 'http://tornadoweb.org/'

    @testing.gen_test
    def test_pending(self):
        yield self.client.put_task(self.task)
        b = yield self.client.is_known_task(self.task)
        self.assertTrue(b)

    @testing.gen_test
    def test_working(self):
        yield self.client.put_task(self.task)
        yield self.client.get_task()
        b = yield self.client.is_known_task(self.task)
        self.assertTrue(b)

    @testing.gen_test
    def test_success(self):
        yield self.client.put_task(self.task)
        yield self.client.get_task()
        yield self.client.register_success(self.task)
        b = yield self.client.is_known_task(self.task)
        self.assertTrue(b)

    @testing.gen_test
    def test_failure(self):
        yield self.client.put_task(self.task)
        yield self.client.get_task()
        yield self.client.register_failure(self.task)
        b = yield self.client.is_known_task(self.task)
        self.assertTrue(b)

class UnknownTaskCase(TaskCase):
    """Make sure the a registered task is 'known' in any state."""
    def setUp(self):
        super(UnknownTaskCase, self).setUp()
        self.task = 'http://tornadoweb.org/'

    @testing.gen_test
    def test_unregistered(self):
        yield self.client.put_task(self.task)
        b = yield self.client.is_known_task('http://tornadoweb.org/foo')
        self.assertFalse(b)


def all():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(PutTaskCase))
    test_suite.addTest(unittest.makeSuite(GetTaskCase))
    test_suite.addTest(unittest.makeSuite(RegisterSuccessCase))
    test_suite.addTest(unittest.makeSuite(RegisterFailureCase))
    test_suite.addTest(unittest.makeSuite(PassedCountCase))
    test_suite.addTest(unittest.makeSuite(PendingCountCase))
    test_suite.addTest(unittest.makeSuite(KnownTaskCase))
    test_suite.addTest(unittest.makeSuite(UnknownTaskCase))
    return test_suite


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s - %(levelname)-8s - %(message)s',
        stream=sys.stderr
    )
    testing.main(verbosity=3)
