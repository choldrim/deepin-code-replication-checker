import json
import os

import requests

from utils.singleton import Singleton
from utils.config import Config


class Bearychat(Singleton):

    def __init__(self):
        self.hook = os.getenv('BC_HOOK')

        if not self.hook:
            c = Config()
            self.hook = c.data('bearychat', 'hook')

    def say(self, text):
        if not text:
            return

        h = {'Content-Type': 'application/json; charset=UTF-8'}
        text_dict = {'text': text}
        payload = {'payload': json.dumps(text_dict)}

        r = requests.post(self.hook, params=payload, headers=h)
        return r.json()
