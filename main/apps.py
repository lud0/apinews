import logging
import sys

from django.apps import AppConfig

from . import fetcher

log = logging.getLogger(__name__)


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        """ Starts the API scraper only in case of runserver (i.e. prevents it from running while testing) """
        if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
            fetcher.start()
