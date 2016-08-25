import json
import os
from datetime import datetime

import requests
from requests.auth import HTTPDigestAuth

from utils.config import Config
from utils.singleton import Singleton

# for debug
CACHE_MODE = os.getenv('CACHE_MODE')

# base
GERRIT_BASE = 'https://cr.deepin.io'
GERRIT_AUTH_BASE = 'https://cr.deepin.io/a'
FILTER_PREFIX = ['old/']


class Gerrit(Singleton):

    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True

        if os.getenv('GERRIT_USERNAME') and os.getenv('GERRIT_PASSWORD'):
            self.auth = HTTPDigestAuth(os.getenv('GERRIT_USERNAME'), os.getenv('GERRIT_PASSWORD'))
        else:
            c = Config()
            self.auth = HTTPDigestAuth(c.data('gerrit', 'username'), c.data('gerrit', 'password'))

        if CACHE_MODE:
            self.project_data_public = self.__load_from_file('cache/gerrit_public.json')
            self.project_data_all = self.__load_from_file('cache/gerrit_all.json')
        else:
            print('initializing all gerrit project ...')
            self.with_auth = True
            self.project_data_all = self.__init_projects()

            print('initializing public gerrit project ...')
            self.with_auth = False
            self.project_data_public = self.__init_projects()

    def __load_from_file(self, path):
        with open(path) as fp:
            data = json.load(fp)

        return data

    def __get_json(self, path):
        if self.with_auth:
            url = '%s%s' % (GERRIT_AUTH_BASE, path)
            r = requests.get(url, auth=self.auth)
        else:
            url = '%s%s' % (GERRIT_BASE, path)
            r = requests.get(url)

        text = r.text.split('\n', 1)[1]  # remove first line
        data = json.loads(text)

        return data

    def __check_prefix_with_filter(self, proj_name):
        for prefix in FILTER_PREFIX:
            if proj_name.startswith(prefix):
                return True

        return False

    def __init_projects(self):
        project_data = {}
        data = self.__get_json('/projects/')

        for (proj_name, p) in data.items():
            if self.__check_prefix_with_filter(proj_name):
                continue

            print('getting project (%s)' % proj_name)
            p_id = p.get('id')
            branches = self.__get_branches(p_id)
            project_data[proj_name] = {'branches': branches}

        return project_data

    def __get_commit_timestamp(self, project, commit_id):
        url = '/projects/%s/commits/%s' % (project, commit_id)
        data = self.__get_json(url)
        time_str = data.get('committer').get('date')
        time_str = time_str.split('.')[0]
        time_str += '+0000'
        timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S%z').timestamp()

        return timestamp

    def __get_branches(self, proj_name):
        branches = {}
        data = self.__get_json('/projects/%s/branches' % proj_name)

        for p in data:
            name = p.get('ref')

            if not name.startswith('refs/heads'):
                continue

            if name.startswith('refs/heads/'):
                name = name.split('refs/heads/')[1]

            commit_id = p.get('revision')
            ts = self.__get_commit_timestamp(proj_name, commit_id)
            branches[name] = {'commit_id': commit_id, 'timestamp': ts}

        return branches
