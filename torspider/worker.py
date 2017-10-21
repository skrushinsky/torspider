#!/usr/bin/env python
'''
Worker.
'''
from os.path import dirname, abspath
import logging
from tornado import gen
from tornado.options import options
from tornado import httpclient

from scraper import HTTPClient, Page
from urlnorm import norm, join_parts, first_level_domain
import mixins

ROOTDIR = abspath(dirname(dirname(__file__)))

async def add_task(redis, url):
    assert url, 'Empty URL!'
    parts = norm(url)
    domain = first_level_domain(parts[1])
    is_known = await gen.Task(redis.is_known_domain, domain)
    if is_known:
        logging.debug('Skipping known domain <%s>', domain)
        return

    normal = join_parts(parts)
    await gen.Task(redis.put_task, normal)
    await gen.Task(redis.save_domain, domain)
    logging.info('Added task <%s>', normal)


class Worker(mixins.RedisClient, mixins.MongoClient, HTTPClient):

    def __init__(self, name='Worker', *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.name = name

    async def rem_task(self, url):
        parts = norm(url)
        domain = first_level_domain(parts[1])
        await gen.Task(self.remove_domain, domain)


    async def run(self):
        logging.info('%s started.', self.name)
        while True:
            pages_count = await gen.Task(self.reports_count)
            try:
                task = await gen.Task(self.get_task)
                assert task, 'Empty task!'
                logging.info('Got task: <%s>', task)
                res = await self.visit(task)
            except (httpclient.HTTPError, AssertionError, UnicodeError, TypeError) as ex:
                logging.error(ex)
                await self.save_report({'url': task, 'error': str(ex)})
                try:
                    await self.rem_task(task)
                except Exception as ex1:
                    logging.error(ex1)
                continue
            else:
                page = Page(task, res)
                await self.save_report({'url': res.effective_url, 'page': page.as_dict()})

                if pages_count >= options.max_pages:
                    logging.info('Task <%s> completed.', task)
                    logging.warn('Pages limit (%d) exceeded. Exiting...', options.max_pages)
                    break

                inner, outer = page.partition_links()
                if options.follow_outer_links:
                    for link in outer:
                        await add_task(self, link)
                if options.follow_inner_links:
                    for link in inner:
                        await add_task(self, link)

                logging.info('Task <%s> completed.', task)

            finally:
                await gen.sleep(0.01)
