#!/usr/bin/env python
'''
Main module, starts and dispatches the entire workflow.
'''
import logging
from tornado import gen
from tornado.options import define, options, parse_command_line, parse_config_file
from tornado.log import enable_pretty_logging
from tornado.ioloop import IOLoop
import pkg_resources
from . import tasks

from pkg_resources import Requirement, resource_filename
DEFAULT_CONF = resource_filename(Requirement.parse('torspider'),"default.conf")
LOCAL_CONF = resource_filename(Requirement.parse('torspider'),"local.conf")
SEEDS_CONF = resource_filename(Requirement.parse('torspider'),"seeds.conf")
PLUGINS_CONF = resource_filename(Requirement.parse('torspider'),"plugins.conf")

from .worker import Worker, add_task
from .utils import iter_file

enable_pretty_logging()


define("proxy", type=str, default='localhost:8118')
define("connect_timeout", type=float, default=10.0, help='Connect timeout')
define("request_timeout", type=float, default=20.0, help='Request timeout')
define("validate_cert", type=bool, default=False, help='Validate certificate')
define("max_pages", type=int, default=100, help='Maximum pages, 0 - no limit')
define("clear_tasks", type=bool, default=True, help='Clear existing data')
define("workers", type=int, default=10, help='Workers count')
define("follow_outer_links", type=bool, default=True, help='Follow outer links')
define("follow_inner_links", type=bool, default=False, help='Follow inner links')
define("throttling_ratio", type=float, default=0.9,
       help='minimal completed / pending tasks ratio, 0 -- no throttling')

io_loop = IOLoop.current()
enabled_plugins = []

def process_entry_point(point_name, *args, **kwargs):
    for entry_point in pkg_resources.iter_entry_points(point_name):
        if entry_point.name in enabled_plugins:
            f = entry_point.load()
            f(*args, **kwargs)

async def main():
    tasks.RedisClient.setup()
    redis = tasks.RedisClient()

    consumers = {
        ep.name: ep.load()
        for ep in pkg_resources.iter_entry_points('torspider_consume')
        if ep.name in enabled_plugins
    }

    if options.clear_tasks:
        await redis.clear_all()

    for seed in iter_file(SEEDS_CONF):
        await add_task(redis, seed.strip())
        logging.info('Added seed: %s.', seed)

    for i in range(options.workers):
        w = Worker('Worker-%d' % (i+1), consumers=consumers)
        io_loop.spawn_callback(w)

    logging.info('Waiting...')
    while True:
        passed_count = await redis.passed_count()
        #logging.info('Pages: %d, Tasks: %d', passed_count, tasks_count)
        if options.max_pages > 0 and passed_count >= options.max_pages:
            logging.warn('Pages limit (%d) exceeded. Exiting...', options.max_pages)
            break
        gen.sleep(5.0)


def run_main():
    parse_config_file(DEFAULT_CONF)
    parse_config_file(LOCAL_CONF)
    parse_command_line()

    for plugin_name in iter_file(PLUGINS_CONF):
        enabled_plugins.append(plugin_name)

    process_entry_point('torspider_init')
    try:
        io_loop.run_sync(main)
    except KeyboardInterrupt:
        logging.warning('Interrupted.')
    except Exception as ex:
        logging.error(ex, exc_info=True)
    finally:
        process_entry_point('torspider_done')


if __name__ == "__main__":
    run_main()
