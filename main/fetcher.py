import logging
import multiprocessing
import threading
import time
from collections import deque
from datetime import datetime

from azure.cognitiveservices.search.newssearch import NewsSearchAPI
from django.conf import settings
from msrest.authentication import CognitiveServicesCredentials

log = logging.getLogger(__name__)

# Process-safe queue for queries to be requested to Bing API.
query_queue = multiprocessing.Manager().Queue()

# Bing API client which takes care of the authentication via the API KEY
client = NewsSearchAPI(CognitiveServicesCredentials(settings.AZURE_API_KEY))


def start():
    """
    Spawns the infinite loop dispatcher process that will consume the query queue

    Calls also the initial queue filler to have some data to play with
    """

    proc = multiprocessing.Process(target=dispatcher)
    proc.start()

    time.sleep(1)
    if not proc.is_alive():
        log.error("Problem starting fetcher process")
    else:
        log.info("Fetcher process correctly started")

    # add some queries to the queue
    initial_scrape()


def initial_scrape():
    """
    Set the list of queries to be done via API.

    Each query has the format:
    {'category': <category>, ['count': <max_results>]}
         or
    {'search': <query string>, ['count': <max_results>]}

    where
    <category> is one of the ones listed here for the en-US market:
    https://docs.microsoft.com/en-us/rest/api/cognitiveservices/bing-news-api-v7-reference#news-categories-by-market

    <query string> is a string of one or more terms
    the optional <max_results> is an integer in [1,100], otherwise uses 10 as default
    """

    query_list = [{'category': 'Business', 'count': 50},
                  {'category': 'Sports', 'count': 50},
                  {'category': 'ScienceAndTechnology', 'count': 100},
                  {'search': 'SpaceX', 'count': 100},
                  {'search': 'art exhibition'},
                  ]

    for q in query_list:
        query_queue.put(q)


def dispatcher():
    """
    Given a list of queries, spawns a thread for each one. Each thread will in turn:
    - make the query request via API
    - parse the results
    - insert in the db if not duplicates

    The maximum number of concurrent threads is limited via a semaphore and the API request rate is also limited via
    a rate limiter.
    """

    # limits maximum number of concurrent threads
    max_concurrent_threads = 5
    thread_limiter = threading.BoundedSemaphore(max_concurrent_threads)

    # limits the API requests rate to max_req per time_interval (seconds)
    rate_limiter = RateLimiter(max_req=3, time_interval=1)

    while True:
        while not query_queue.empty():
            query = query_queue.get()
            thread = ScraperThread(query=query, thread_limiter=thread_limiter, rate_limiter=rate_limiter)
            thread.start()

        # this is to terminate nicely upon CTRL+C keyboard interrupt
        try:
            time.sleep(1)
        except:
            break


class ScraperThread(threading.Thread):

    def __init__(self, query, thread_limiter=None, rate_limiter=None):
        super(ScraperThread, self).__init__()
        self.query = query
        self.thread_limiter = thread_limiter
        self.rate_limiter = rate_limiter

    def run(self):
        with self.thread_limiter:
            bns = BingNewsSearch(query=self.query, rate_limiter=self.rate_limiter)
            bns.run()


class BingNewsSearch:

    def __init__(self, query=None, rate_limiter=None):
        self.query = query
        self.rate_limiter = rate_limiter

    def run(self):
        """
        Main method: make the API request, parse the results and insert in db
        """
        response = self.call_api()
        parsed_response = self.parse_response(response)
        self.insert_db(parsed_response)

    def call_api(self):
        if not self.rate_limiter or self.rate_limiter.get_permit():

            response = None
            if not settings.AZURE_DRY_RUN:
                log.debug("requesting API for query: {}".format(self.query))
                if 'category' in self.query:
                    try:
                        response = client.news.category(category=self.query['category'], market="en-us", count=self.query.get('count', 10))
                    except Exception as err:
                        log.error("Exception: {}".format(err))
                elif 'search' in self.query:
                    try:
                        response = client.news.search(query=self.query['search'], market="en-us", count=self.query.get('count', 10))
                    except Exception as err:
                        log.error("Exception: {}".format(err))
            else:
                log.debug("FAKING request API for query: {}".format(self.query))
                time.sleep(2)

            return response

    @staticmethod
    def parse_response(response):
        """
        Parse the response and creates the objects. Only non duplicates objects with valid fields are returned.
        """
        from .models import NewsForm

        if not response:
            return []

        news_objects = []
        for news in response.value:
            try:
                pub_date = datetime.strptime(news.date_published[:19], "%Y-%m-%dT%H:%M:%S")
            except:
                pass
            else:
                nf = NewsForm({'category': news.category,
                               'name': news.name,
                               'content': news.description,
                               'url': news.url,
                               'date': pub_date})

                # uses the convenient is_valid() method of the form class to check if the fields are consistent
                # with the model and the object doesn't violate any constraint (i.e. is unique).
                # Don't save to db right now, will do all at once in insert_db()
                if nf.is_valid():
                    news_objects += nf.save(commit=False),

        log.info("Parsed {0} valid news out of {1} total".format(len(news_objects), len(response.value)))
        return news_objects

    @staticmethod
    def insert_db(parsed_response):
        from .models import News

        if not parsed_response:
            return

        try:
            News.objects.bulk_create(parsed_response)
        except Exception as err:
            log.error("Exception: {}".format(err))


class RateLimiter:
    """
    Simple thread-safe rate limiter: get_permit() waits until enough time has passed
    to guarantee the correct number of requests in the given time interval (in seconds) and returns True.
    If timeout is set, then returns False in case time interval has passed without a permit
    """
    def __init__(self, max_req=2, time_interval=10, timeout=None):
        self.time_interval = time_interval
        self.deque = deque(maxlen=max_req)
        self.timeout = timeout

    def _block(self):
        now = time.time()
        if self.deque.maxlen == len(self.deque):
            if now - self.deque[0] > self.time_interval:
                self.deque.popleft()
                self.deque.append(now)
                return False
            else:
                return True
        else:
            self.deque.append(now)
            return False

    def get_permit(self):
        """
        wait until rate limit is respected and returns True
        if timeout is set, then return False after timeout seconds
        """

        start_time = time.time()
        timed_out = False
        while self._block():
            time.sleep(0.1)
            if self.timeout and time.time() - start_time > self.timeout:
                timed_out = True
                break
        if timed_out:
            return False
        return True
