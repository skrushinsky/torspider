import sys
from os.path import dirname
import logging
import unittest

from tornado import testing, gen
import redis as pyredis

ROOTDIR = dirname(dirname(dirname(__file__)))
sys.path.append(ROOTDIR)

# import application packages
from torspider import mixins

DOMAINS_SET = "torspider:test:domains"
TASKS_LIST = "torspider:test:tasks"
REPORTS_HASH = "torspider:test:reports"

redis = pyredis.StrictRedis()


class SaveDomainCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        super(SaveDomainCase, self).setUp()
        mixins.RedisClient.setup(known_domains=DOMAINS_SET, io_loop=self.io_loop)

    def tearDown(self):
        super(SaveDomainCase, self).tearDown()
        logging.info('tearDown')
        redis.delete(DOMAINS_SET)
        logging.info('%s deleted.', DOMAINS_SET)

    @testing.gen_test
    def test_save_domain(self):
        res = yield gen.Task(mixins.RedisClient().save_domain, 'tornadoweb.org')
        self.assertEqual(res, 1)


class CheckDomainCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        redis.sadd(DOMAINS_SET, 'tornadoweb.org')
        super(CheckDomainCase, self).setUp()
        mixins.RedisClient.setup(known_domains=DOMAINS_SET, io_loop=self.io_loop)

    def tearDown(self):
        super(CheckDomainCase, self).tearDown()
        logging.info('tearDown')
        redis.delete(DOMAINS_SET)
        logging.info('%s deleted.', DOMAINS_SET)

    @testing.gen_test
    def test_is_known_domain(self):
        res = yield gen.Task(mixins.RedisClient().is_known_domain, 'tornadoweb.org')
        self.assertTrue(res)

    @testing.gen_test
    def test_remove_domain(self):
        res = yield gen.Task(mixins.RedisClient().remove_domain, 'tornadoweb.org')
        self.assertEqual(1, res)


class PutTaskCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        super(PutTaskCase, self).setUp()
        mixins.RedisClient.setup(tasks_queue=TASKS_LIST, io_loop=self.io_loop)

    def tearDown(self):
        super(PutTaskCase, self).tearDown()
        logging.info('tearDown')
        redis.delete(TASKS_LIST)
        logging.info('%s deleted.', TASKS_LIST)

    @testing.gen_test
    def test_put(self):
        yield gen.Task(mixins.RedisClient().put_task, 'http://tornadoweb.org/')
        self.assertEqual(redis.llen(TASKS_LIST), 1)



class GetTaskCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        redis.lpush(TASKS_LIST, 'http://tornadoweb.org/')
        super(GetTaskCase, self).setUp()
        mixins.RedisClient.setup(tasks_queue=TASKS_LIST, io_loop=self.io_loop)

    def tearDown(self):
        super(GetTaskCase, self).tearDown()
        logging.info('tearDown')
        redis.delete(TASKS_LIST)
        logging.info('%s deleted.', TASKS_LIST)

    @testing.gen_test
    def test_is_known_domain(self):
        res = yield gen.Task(mixins.RedisClient().get_task)
        self.assertEqual('http://tornadoweb.org/', res)


    @testing.gen_test
    def test_count(self):
        res = yield gen.Task(mixins.RedisClient().tasks_count)
        self.assertEqual(1, res)


class SaveReportCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        super(SaveReportCase, self).setUp()
        mixins.RedisClient.setup(reports_hash=REPORTS_HASH, io_loop=self.io_loop)

    def tearDown(self):
        super(SaveReportCase, self).tearDown()
        logging.info('tearDown')
        redis.delete(REPORTS_HASH)
        logging.info('%s deleted.', REPORTS_HASH)

    @testing.gen_test
    def test_save_report(self):
        res = yield gen.Task(mixins.RedisClient().save_report, 'http://tornadoweb.org/', 'bar')
        self.assertEqual(1, res)


class LoadReportCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        redis.hset(REPORTS_HASH, 'http://tornadoweb.org/', 'foo')
        super(LoadReportCase, self).setUp()
        mixins.RedisClient.setup(reports_hash=REPORTS_HASH, io_loop=self.io_loop)

    def tearDown(self):
        super(LoadReportCase, self).tearDown()
        logging.info('tearDown')
        redis.delete(REPORTS_HASH)
        logging.info('%s deleted.', REPORTS_HASH)

    @testing.gen_test
    def test_load_report(self):
        res = yield gen.Task(mixins.RedisClient().load_report, 'http://tornadoweb.org/')
        self.assertEqual('foo', res)

    @testing.gen_test
    def test_reports_count(self):
        res = yield gen.Task(mixins.RedisClient().reports_count)
        self.assertEqual(1, res)

def all():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(SaveDomainCase))
    test_suite.addTest(unittest.makeSuite(CheckDomainCase))
    test_suite.addTest(unittest.makeSuite(PutTaskCase))
    test_suite.addTest(unittest.makeSuite(GetTaskCase))
    test_suite.addTest(unittest.makeSuite(SaveReportCase))
    test_suite.addTest(unittest.makeSuite(LoadReportCase))
    return test_suite


if __name__ == '__main__':
    #
    testing.main(verbosity=4)
