#!/usr/bin/env python
'''
Worker.
'''
import logging
from tornado import gen
from tornado.options import options
from tornado import httpclient

from .scraper import HTTPClient, Page
from .urlnorm import norm, join_parts, first_level_domain
from . import tasks


async def add_task(redis, url):
    task = join_parts(norm(url))
    logging.debug('Adding %s to tasks queue...', task)
    known = await redis.is_known_task(task)
    if known:
        logging.debug('Skipping known address <%s>', task)
        return
    logging.debug('%s is new', task)
    await redis.put_task(task)
    logging.info('Registered task <%s>', task)


class Worker(tasks.RedisClient, HTTPClient):

    def __init__(self, name='Worker', consumers=None, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.name = name
        self.consumers = consumers

    async def consume(self, report, consumers=None):
        logging.info('Calling consumers')
        for name, func in self.consumers.items():
            logging.info('Calling consumer <%s> function %s...', name, func)
            try:
                await func(report)
            except Exception as ex:
                logging.error(ex, exc_info=True)

    async def __call__(self):
        logging.info('%s started.', self.name)
        while True:
            try:
                task = await self.get_task() # the task is now in 'working' set
                logging.debug('Got task: <%s>', task)
                res = await self.visit(task)
            except (httpclient.HTTPError, AssertionError, UnicodeError, TypeError) as ex:
                logging.error(ex)
                await self.consume({'url': task, 'error': str(ex)})
                await self.register_failure(task)
                continue
            else:
                page = Page(task, res)
                await self.consume({'url': task, 'page': page})
                await self.register_success(task)
                passed_count = await self.passed_count()
                if options.max_pages > 0 and passed_count >= options.max_pages:
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
