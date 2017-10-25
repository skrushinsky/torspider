import sys
import logging
import unittest
from tornado import testing
import redis as pyredis



# import application packages
from torspider import mixins

DOMAINS_SET = "torspider:test:known"
TASKS_LIST = "torspider:test:tasks"
redis = pyredis.StrictRedis()


class SaveDomainCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        super(SaveDomainCase, self).setUp()
        mixins.RedisClient.setup(known_urls=DOMAINS_SET, io_loop=self.io_loop)

    def tearDown(self):
        super(SaveDomainCase, self).tearDown()
        logging.debug('tearDown')
        redis.delete(DOMAINS_SET)
        logging.debug('%s deleted.', DOMAINS_SET)

    @testing.gen_test
    def test_save_visit(self):
        res = yield mixins.RedisClient().save_visit('tornadoweb.org')
        self.assertEqual(res, 1)


class CheckDomainCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        redis.sadd(DOMAINS_SET, 'tornadoweb.org')
        super(CheckDomainCase, self).setUp()
        mixins.RedisClient.setup(known_urls=DOMAINS_SET, io_loop=self.io_loop)

    def tearDown(self):
        super(CheckDomainCase, self).tearDown()
        logging.debug('tearDown')
        redis.delete(DOMAINS_SET)
        logging.debug('%s deleted.', DOMAINS_SET)

    @testing.gen_test
    def test_is_known_address(self):
        res = yield mixins.RedisClient().is_known_address('tornadoweb.org')
        self.assertTrue(res)

    @testing.gen_test
    def test_forget_visit(self):
        res = yield mixins.RedisClient().forget_visit('tornadoweb.org')
        self.assertEqual(1, res)

    @testing.gen_test
    def test_pages_count(self):
        res = yield mixins.RedisClient().pages_count()
        self.assertEqual(1, res)


class PutTaskCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        super(PutTaskCase, self).setUp()
        mixins.RedisClient.setup(tasks_queue=TASKS_LIST, io_loop=self.io_loop)

    def tearDown(self):
        super(PutTaskCase, self).tearDown()
        logging.debug('tearDown')
        redis.delete(TASKS_LIST)
        logging.debug('%s deleted.', TASKS_LIST)

    @testing.gen_test
    def test_put(self):
        yield mixins.RedisClient().put_task('http://tornadoweb.org/')
        self.assertEqual(redis.llen(TASKS_LIST), 1)



class GetTaskCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        redis.lpush(TASKS_LIST, 'http://tornadoweb.org/')
        super(GetTaskCase, self).setUp()
        mixins.RedisClient.setup(tasks_queue=TASKS_LIST, io_loop=self.io_loop)

    def tearDown(self):
        super(GetTaskCase, self).tearDown()
        logging.debug('tearDown')
        redis.delete(TASKS_LIST)
        logging.debug('%s deleted.', TASKS_LIST)

    @testing.gen_test
    def test_get_task(self):
        res = yield mixins.RedisClient().get_task()
        self.assertEqual('http://tornadoweb.org/', res)


    @testing.gen_test
    def test_count(self):
        res = yield mixins.RedisClient().tasks_count()
        self.assertEqual(1, res)


def all():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(SaveDomainCase))
    test_suite.addTest(unittest.makeSuite(CheckDomainCase))
    test_suite.addTest(unittest.makeSuite(PutTaskCase))
    test_suite.addTest(unittest.makeSuite(GetTaskCase))

    return test_suite


if __name__ == '__main__':
    logging.basicConfig(
        #level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s - %(levelname)-8s - %(message)s',
        stream=sys.stderr
    )
    testing.main(verbosity=4)
