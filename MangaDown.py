import os.path
import parsel
import subprocess
from util import *
import random
import pickle
import copy
from util import *


class MangaDown(object):
    def __init__(self, url, path):
        self.url = url
        self.path = path
        self.session = requests.session()
        self.session.headers = create_headers()

    def _get_info(self):
        resp = try_until_response_get(self.url, headers=self.session.headers, trys=3)
        return resp

    def download(self):
        data = parsel.Selector(self._get_info())
        data.xpath("")



    def main(self):
        pass



