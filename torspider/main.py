#!/usr/bin/env python
'''
Main module, starts and dispatches the entire workflow.
'''

import os, sys
from os.path import dirname, abspath
import logging
from tornado import gen
from tornado.options import define, options, parse_command_line, parse_config_file
from tornado.log import enable_pretty_logging
from tornado.ioloop import IOLoop
import mixins

ROOTDIR = abspath(dirname(dirname(__file__)))
sys.path.append(ROOTDIR)
CONF = os.path.join(ROOTDIR, 'conf', 'local.conf')

from worker import Worker, add_task
from utils import iter_file

enable_pretty_logging()

define("proxy", type=str, default='localhost:8118')
define("mongodb", type=str, default='mongodb://localhost:27017/spider', help='MongoDB connect string')
define("connect_timeout", type=float, default=10.0, help='Connect timeout')
define("request_timeout", type=float, default=20.0, help='Request timeout')
define("validate_cert", type=bool, default=False, help='Validate certificate')
define("max_pages", type=int, default=0, help='Maximum pages, 0 - no limit')
define("seeds", type=str,  multiple=True, default='conf/seeds.txt', help='Path to list of initial URLs')
define("clear", type=bool, default=False, help='Clear existing data')
define("workers", type=int, default=30, help='Workers count')

io_loop = IOLoop.current()

async def main():
    mixins.RedisClient.setup()
    redis = mixins.RedisClient()
    if options.clear:
        await gen.Task(redis.clear_all)

    for seed in iter_file(options.seeds):
        logging.info('Adding seed: %s', seed)
        await add_task(redis, seed.strip())

    for i in range(options.workers):
        w = Worker('Worker-%d' % (i+1))
        io_loop.spawn_callback(w.run)

    while True:
        tasks_count = await gen.Task(redis.tasks_count)
        pages_count = await gen.Task(redis.reports_count)
        #logging.info('Pages: %d, Tasks: %d', pages_count, tasks_count)
        if tasks_count > 0 and pages_count >= options.max_pages:
            logging.warn('Pages limit (%d) exceeded. Exiting...', options.max_pages)
            break
        gen.sleep(5.0)

if __name__ == "__main__":
    parse_config_file(CONF)
    parse_command_line()
    try:
        io_loop.run_sync(main)
    except KeyboardInterrupt:
        logging.warning('Interrupted.')
    except Exception as ex:
        logging.error(ex, exc_info=True)
