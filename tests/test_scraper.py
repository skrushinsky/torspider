import sys
from os.path import dirname
import logging
import unittest

from tornado import testing
from tornado.options import define
from  tornado.httpclient import HTTPError

# import application packages
from torspider import scraper

define("proxy", type=str, default=None)
define("connect_timeout", type=float, default=10.0, help='Connect timeout')
define("request_timeout", type=float, default=20.0, help='Request timeout')
define("validate_cert", type=bool, default=False, help='Validate certificate')


class HTTPClientCase(testing.AsyncTestCase):
    """Test HTTP client."""
    def setUp(self):
        logging.info('setUp')
        super(HTTPClientCase, self).setUp()
        self.client = scraper.HTTPClient()

    def tearDown(self):
        super(HTTPClientCase, self).tearDown()
        logging.info('tearDown')

    @testing.gen_test
    def test_http(self):
        res = yield self.client.visit('http://httpbin.org/html')
        self.assertIsNotNone(res)

    @testing.gen_test
    def test_https(self):
        #res = yield self.client.visit('https://httpbin.org/html')
        res = yield self.client.visit('https://java.com/')
        self.assertIsNotNone(res)

    @testing.gen_test
    def test_http_error(self):
        with self.assertRaises(HTTPError) as ex:
            logging.info('%s raised', ex)
            yield self.client.visit('http://httpbin.org/status/418')

    @testing.gen_test
    def test_bad_content_type(self):
        with self.assertRaises(AssertionError) as ex:
            logging.info('%s raised', ex)
            yield self.client.visit('http://httpbin.org/image/jpeg')

    # @testing.gen_test
    # def test_bad_language(self):
    #     with self.assertRaises(AssertionError) as ex:
    #         logging.info('%s raised', ex)
    #         yield self.client.visit('http://httpbin.org/image/jpeg')


class PageCase(testing.AsyncTestCase):

    def setUp(self):
        logging.info('setUp')
        super(PageCase, self).setUp()
        self.client = scraper.HTTPClient()
        self.url = 'http://httpbin.org/html'

    def tearDown(self):
        super(PageCase, self).tearDown()
        logging.info('tearDown')

    @testing.gen_test
    def test_title(self):
        res = yield self.client.visit(self.url)
        page = scraper.Page(self.url, res)
        self.assertEqual('Herman Melville - Moby-Dick', page.title)

    @testing.gen_test
    def test_text(self):
        res = yield self.client.visit(self.url)
        page = scraper.Page(self.url, res)
        self.assertIsNotNone(page.text)

    @testing.gen_test
    def test_language(self):
        res = yield self.client.visit(self.url)
        page = scraper.Page(self.url, res)
        self.assertEqual('en', page.language)

    @testing.gen_test
    def test_links(self):
        res = yield self.client.visit('http://httpbin.org/links/10/0')
        page = scraper.Page(self.url, res)
        self.assertEqual(9, len(page.links))

    @testing.gen_test
    def test_inner_links(self):
        res = yield self.client.visit('http://httpbin.org/links/10/0')
        page = scraper.Page(self.url, res)
        inner, _ = page.partition_links()
        self.assertEqual(9, len(inner))


def all():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(HTTPClientCase))
    test_suite.addTest(unittest.makeSuite(PageCase))
    return test_suite


if __name__ == '__main__':
    #
    testing.main(verbosity=4)
