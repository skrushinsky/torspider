#!/usr/bin/env python
'''
Main module, starts and dispatches the entire workflow.
'''

import os, sys
from os.path import dirname, abspath
import logging
import datetime
from time import time
from urllib.parse import urlparse
#from pprint import pformat

from tornado import gen
from tornado.options import define, options, parse_command_line #, parse_config_file
from tornado.log import enable_pretty_logging
from tornado.ioloop import IOLoop
from tornado.queues import Queue
from tornado import httpclient
import pymongo
import motor

from scraper import Client, Page
from urlnorm import norm, join_parts

ROOTDIR = abspath(dirname(dirname(__file__)))
sys.path.append(ROOTDIR)
CONF = os.path.join(ROOTDIR, 'conf', 'local.conf')
DEBUG = True

enable_pretty_logging()

define("proxy", type=str, default='localhost:8118')
define("connect_timeout", type=float, default=10.0, help='Connect timeout')
define("request_timeout", type=float, default=20.0, help='Request timeout')
define("delay", type=float, default=3.0, help='Delay between requests to the same host, in seconds')
define("concurrency", type=int, default=10, help='Workers count')
define("validate_cert", type=bool, default=False, help='Validate certificate')
define("mongodb", type=str, default='mongodb://localhost:27017/spider', help='MongoDB connect string')
define("inner_links", type=bool, default=True, help='Follow inner links')
define("outer_links", type=bool, default=False, help='Follow outer links')
define("seeds", type=str, multiple=True, help='Comma separated list of initial urls')

async def url_exists(url, collection):
    """
    Return True if given URL exists in a collection.
    """
    doc = await collection.find_one({'url': url})
    return bool(doc)


async def consumer(inbox=None, db=None):
    """
    Save results from 'inbox' queue to Mongo database.
    """
    async for task in inbox:
        try:
            report = {
                'ts': datetime.datetime.utcnow(),
                'url': task['url']
            }
            if 'error' in task:
                report['error'] = task['error']
                msg = 'failure '
            else:
                report['page'] = task['page']
                msg = ''
            res = await db.reports.update_one(
                {'url': task['url']},
                {'$set': report},
                upsert=True
            )
            if res.upserted_id:
                logging.info('Inserted %sreport for %s', msg, task['url'])
        finally:
            inbox.task_done()
            await gen.sleep(0.01)

async def get_new_links(page=None, db=None):
    old_parts = urlparse(page.url)
    new_links = []
    #logging.info('links: %s', pformat(page.links))
    for link in page.links:
        if await url_exists(link, db.reports):
            logging.warn('<%s> was already visited', link)
            # TODO: analyse failure; if it's not permanent, try to visit
            # failed URL again. Implement a counter and scheduled tasks.
            continue

        new_parts = urlparse(link)
        if not options.outer_links and new_parts[1] != old_parts[1]:
            logging.warn('Skipping outer link <%s>', link)
            continue
        if not options.inner_links and new_parts[1] == old_parts[1]:
            logging.warn('Skipping inner link <%s>', link)
            continue

        new_links.append(link)
        await gen.sleep(0.01)
    return new_links

async def worker(inbox=None, outbox=None, db=None, name=None):
    """
    Scrap URLs from 'inbox' queue.
    New links found at page are appended to inbox.
    Results, as well as failures, go to 'outbox' queue.
    """
    logging.info('%s online', name)
    client = Client()
    async for url in inbox:
        logging.info('<%s>: task <%s>. Queue size: %d', name, url, inbox.qsize())
        logging.debug('<%s>: fetching %s...', name, url)
        try:
            res = await client.visit(url)
        except httpclient.HTTPError as ex:
            report = {'url': url, 'error': str(ex)}
            logging.warn(ex)
        except Exception as ex:
            logging.warn(ex)
            report = {'url': url, 'error': str(ex)}
            raise ex # DEBUG MODE
        else:
            page = Page(url, res)
            report = {'url': res.effective_url, 'page': page.as_dict()}
            links = await get_new_links(page, db)
            for link in links:
                inbox.put(link)
            if len(links) > 0:
                logging.info(
                    '%s: added %d unique links to the queue from %s.',
                    name, len(links), url)
            else:
                logging.info('%s: no new links at %s', name, url)
        finally:
            outbox.put(report)
            await gen.sleep(0.01)
            inbox.task_done()
            logging.info('<%s>: Task <%s> done.', name, url)

    logging.info('<%s>: offline.', name)

async def main():
    starttime = time()
    tasks_q = Queue()
    results_q = Queue()

    dbname = options.mongodb.split('/')[-1]
    dbconn =  '/'.join(options.mongodb.split('/')[:-1])
    logging.debug('Connecting to database: %s...', dbname)
    mongo_client = motor.motor_tornado.MotorClient(dbconn)
    db = mongo_client[dbname]
    await db.reports.create_index([('url', pymongo.ASCENDING)], unique=True)
    await db.reports.create_index([('ts', pymongo.ASCENDING)])
    IOLoop.current().spawn_callback(consumer, results_q, db)
    logging.info('Consumer started.')
    for i in range(options.concurrency):
        IOLoop.current().spawn_callback(worker, tasks_q, results_q, db, 'Worker-%02d' % (i+1))
    logging.info('Started %d workers.', options.concurrency)
    assert options.seeds, 'Please, provide one or more seed URLs'
    for seed in options.seeds:
        url = join_parts(norm(seed.strip()))
        logging.debug('Adding initial task: <%s>', url)
        tasks_q.put(url)
    logging.info('Tasks queue size: %d', tasks_q.qsize())
    await tasks_q.join()
    await results_q.join()
    end_time = time()
    time_taken = end_time - starttime # time_taken is in seconds
    hr, rest = divmod(time_taken, 3600)
    mi, se = divmod(rest, 60)
    logging.info('Done in %dh %02dm %02ds', hr, mi, se)


if __name__ == "__main__":
    #parse_config_file(CONF)
    parse_command_line()
    try:
        IOLoop.current().run_sync(main)
    except KeyboardInterrupt:
        logging.warning('Interrupted.')
    except Exception as ex:
        logging.error(ex, exc_info=DEBUG)
