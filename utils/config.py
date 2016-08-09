import os
from configparser import ConfigParser

from utils.singleton import Singleton

CONFIG_PATH = './config.ini'

class Config(Singleton):
    def __init__(self, path=CONFIG_PATH):
        if hasattr(self, '_init'):
            return
        self._init = True
        self.config = ConfigParser()
        self.config.read(path)

    def data(self, s, n):
        return self.config[s][n]


