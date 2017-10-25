import sys
import logging
import unittest

from torspider import urlnorm

class UrlNormTestCase(unittest.TestCase):
    """Test urlnorm.norm and join_parts functions."""
    def test_no_scheme(self):
        res = urlnorm.norm('//httpbin.org/')
        self.assertEqual(('http', 'httpbin.org', '/', '', '', ''), res)

    def test_default_authority(self):
        res = urlnorm.norm('/', 'httpbin.org')
        self.assertEqual(('http', 'httpbin.org', '/', '', '', ''), res)

    def test_no_default_authority(self):
        with self.assertRaises(AssertionError):
            urlnorm.norm('/')

    def test_non_default_port(self):
        res = urlnorm.norm('http://httpbin.org:8080/')
        self.assertEqual(('http', 'httpbin.org:8080', '/', '', '', ''), res)

    def test_collapse(self):
        res = urlnorm.norm('http://httpbin.org/encoding//./utf8')
        self.assertEqual( ('http', 'httpbin.org', '/encoding/utf8', '', '', ''), res)

    def test_remove_fragments(self):
        res = urlnorm.norm('http://httpbin.org/encoding/utf8#frag')
        self.assertEqual( ('http', 'httpbin.org', '/encoding/utf8', '', '', ''), res)

    def test_international(self):
        res = urlnorm.norm('http://xn--h1alffa9f.xn--h1aegh.museum/')
        self.assertEqual( ('http', 'россия.иком.museum', '/', '', '', ''), res)

    def test_unquote(self):
        res = urlnorm.norm('http://example.com/El%20Ni%C3%B1o/')
        self.assertEqual( ('http', 'example.com', '/El Niño/', '', '', ''), res)

    def test_case(self):
        res = urlnorm.norm('HTTP://EXAMPLE.COM/')
        self.assertEqual( ('http', 'example.com', '/', '', '', ''), res)

    def test_join_parts(self):
        res = urlnorm.join_parts(('http', 'httpbin.org', '/encoding/utf8', '', '', ''))
        self.assertEqual('http://httpbin.org/encoding/utf8', res)


class DomainExtractCase(unittest.TestCase):
    """Test misc utilities from urlnorm module."""

    def test_get_domain(self):
        res = urlnorm.get_domain('http://httpbin.org/encoding/utf8')
        self.assertEqual('httpbin.org', res)

    def test_first_level_domain_from_secondary(self):
        res = urlnorm.first_level_domain('quarters.lunarium.ru')
        self.assertEqual('lunarium.ru', res)

    def test_long_subdomain(self):
        res = urlnorm.first_level_domain('some.deep.subdomain.httpbin.org')
        self.assertEqual('httpbin.org', res)

    def test_first_level_domain_from_first(self):
        res = urlnorm.first_level_domain('httpbin.org')
        self.assertEqual('httpbin.org', res)

    def test_get_first_level_domain(self):
        res = urlnorm.get_first_level_domain('http://subdomain.httpbin.org/encoding/utf8')
        self.assertEqual('httpbin.org', res)


def all():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(UrlNormTestCase))
    test_suite.addTest(unittest.makeSuite(DomainExtractCase))
    return test_suite


if __name__ == '__main__':
    logging.basicConfig(
        #level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s - %(levelname)-8s - %(message)s',
        stream=sys.stderr
    )
    #logging.getLogger("UrlNormTestCase").setLevel(logging.DEBUG)
    #logging.getLogger("DomainExtractCase").setLevel(logging.DEBUG)
    unittest.main(verbosity=4)
