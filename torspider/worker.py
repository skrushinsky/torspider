#!/usr/bin/env python
'''
Worker.
'''
import logging
from tornado import gen
from tornado.options import options
from tornado import httpclient

from .scraper import HTTPClient, Page
from .urlnorm import norm, join_parts
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
    logging.debug('Registered task <%s>', task)


class Worker(tasks.RedisClient, HTTPClient):
    """Its main responsibility is to handle tasks, taken from PENDING queue.

    As soon as new URL is available, worker tries to get corresponding web page.
    Whatever is the result -- success or failure, it is propagated to available
    consumers and recorded to inner Redis structures. Next, links are extracted
    and appended to the PENDING queue.
    """
    def __init__(self, name='Worker', consumers=None, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.name = name
        self.consumers = consumers

    async def consume(self, report, consumers=None):
        logging.debug('Calling consumers')
        for name, func in self.consumers.items():
            logging.debug('Calling consumer <%s> function %s...', name, func)
            try:
                await func(report)
            except Exception as ex:
                logging.error(ex, exc_info=True)

    async def __call__(self):
        logging.debug('%s started.', self.name)
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

                if options.throttling_ratio > 0:
                    # throttling ratio
                    pending_count = await self.pending_count()
                    if pending_count > 0:
                        r = passed_count / pending_count
                        if r < options.throttling_ratio:
                            logging.info('passed_count / pending_count = %.1f. Waiting...', r)
                            continue

                # Extract links from the page
                inner, outer = page.partition_links()
                i = 0
                if options.follow_outer_links:
                    for link in outer:
                        await add_task(self, link)
                        i += 1
                if options.follow_inner_links:
                    for link in inner:
                        await add_task(self, link)
                        i += 1
                logging.info('Registered %d new tasks from %s', i+1, res.effective_url)
                logging.debug('Task <%s> completed.', task)

            finally:
                logging.debug('%s is sleeping...', self.name)
                await gen.sleep(0.01)
