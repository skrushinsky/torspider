#!/usr/bin/env python
'''
Worker.
'''
import os
from os.path import dirname, abspath
import logging
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

from tornado import gen
from tornado.options import options
from tornado import httpclient
from tornado.platform.asyncio import to_tornado_future

from selenium.common.exceptions import TimeoutException

from scraper import HTTPClient, get_screenshot, Page
from urlnorm import norm, join_parts, first_level_domain
import mixins
import utils

THREAD_POOL_SIZE = 64
ROOTDIR = abspath(dirname(dirname(__file__)))

def blocking(method):
    """Wraps the method in an async method, and executes the function on `self.executor`."""
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        fut = self.executor.submit(method, self, *args, **kwargs)
        return await to_tornado_future(fut)
    return wrapper

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


class Worker(mixins.RedisClient, HTTPClient):
    executor = ThreadPoolExecutor(THREAD_POOL_SIZE)


    def __init__(self, name='Worker', *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.name = name

    async def rem_task(self, url):
        parts = norm(url)
        domain = first_level_domain(parts[1])
        await gen.Task(self.remove_domain, domain)


    @blocking
    def go_for_screenshot(self, url):

        image = get_screenshot(url,
            timeout=options.request_timeout,
            phantomjs=options.phantomjs,
            size=options.screen_size)
        return utils.save_screenshot(image, url,
            screenshots_dir=os.path.join(ROOTDIR, options.screenshots_dir)
        )


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
                try:
                    await self.rem_task(task)
                except Exception as ex1:
                    logging.error(ex1)
                continue
            else:
                page = Page(task, res)
                try:
                    fname = await self.go_for_screenshot(res.effective_url)
                except (AssertionError, TypeError, TimeoutException) as ex:
                    logging.error(ex)
                    await self.rem_task(task)
                else:
                    await gen.Task(self.save_report, task, fname)

                if pages_count >= options.max_pages:
                    logging.info('Task <%s> completed.', task)
                    logging.warn('Pages limit (%d) exceeded. Exiting...', options.max_pages)
                    break

                _, outer = page.partition_links()
                for link in outer:
                    await add_task(self, link)

                logging.info('Task <%s> completed.', task)

            finally:
                await gen.sleep(0.01)
