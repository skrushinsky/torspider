#!/usr/bin/env python
'''
Worker.
'''
from os.path import dirname, abspath
import logging
from tornado import gen
from tornado.options import options
from tornado import httpclient
import pymongo

from .scraper import HTTPClient, Page
from .urlnorm import norm, join_parts, first_level_domain
from .import mixins


async def add_task(redis, url):
    task = join_parts(norm(url))
    logging.debug('Adding %s to tasks queue...', task)
    known = await redis.is_known_address(task)
    if known:
        logging.debug('Skipping known address <%s>', task)
        return
    logging.debug('%s is new', task)
    await redis.put_task(task)
    await redis.save_visit(task)
    logging.info('Added task <%s>', task)


class Worker(mixins.RedisClient, mixins.MongoClient, HTTPClient):

    def __init__(self, name='Worker', *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.name = name

    async def rem_task(self, url):
        parts = norm(url)
        domain = first_level_domain(parts[1])
        await self.forget_visit(domain)


    async def __call__(self):
        logging.info('%s started.', self.name)
        while True:
            try:
                task = await self.get_task()
                if not task:
                    continue
                logging.debug('Got task: <%s>', task)
                res = await self.visit(task)
            except (httpclient.HTTPError, AssertionError, UnicodeError, TypeError) as ex:
                logging.error(ex)
                try:
                    await self.save_report({'url': task, 'error': str(ex)})
                except PyMongoError as ex1:
                    logging.error(ex1)

                try:
                    await self.rem_task(task)
                except Exception as ex2:
                    logging.error(ex2)
                continue
            else:
                page = Page(task, res)
                await self.save_report({'url': res.effective_url, 'page': page.as_dict()})

                pages_count = await self.reports_count()
                if options.max_pages > 0 and pages_count >= options.max_pages:
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

                logging.debug('Task <%s> completed.', task)

            finally:
                logging.debug('%s is sleeping...', self.name)
                await gen.sleep(0.01)
