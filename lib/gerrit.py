import json
import os
from datetime import datetime

import requests

from utils.singleton import Singleton

# for debug
CACHE_MODE = os.getenv('CACHE_MODE')

class Gerrit(Singleton):
    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True

        if CACHE_MODE:
            self.project_data = self.__load_from_file('cache/gerrit.json')
        else:
            self.project_data = self.__init_projects()

    def __load_from_file(self, path):
        with open(path) as fp:
            data = json.load(fp)

        return data


    def __get_json(self, url):
        r = requests.get(url)
        text = r.text.split('\n', 1)[1]  # remove first line
        data = json.loads(text)

        return data


    def __init_projects(self):
        print('initializing gerrit project ...')
        project_data = {}
        data = self.__get_json('https://cr.deepin.io/projects/')

        for (proj_name, p) in data.items():
            print('getting project (%s)' % proj_name)
            p_id = p.get('id')
            branches = self.__get_branches(p_id)
            project_data[proj_name] = {'branches': branches}

        return project_data


    def __get_commit_timestamp(self, project, commit_id):
        url = 'https://cr.deepin.io/projects/%s/commits/%s' % (project, commit_id)
        data = self.__get_json(url)
        time_str = data.get('committer').get('date')
        time_str = time_str.split('.')[0]
        time_str += '+0000'
        timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S%z').timestamp()

        return timestamp


    def __get_branches(self, proj_name):
        branches = {}
        data = self.__get_json('https://cr.deepin.io/projects/%s/branches' % proj_name)

        for p in data:
            if p.get('ref') == 'HEAD':
                continue

            name = p.get('ref')

            if 'refs/heads/' in name:
                name = name.split('refs/heads/')[1]

            commit_id = p.get('revision')
            ts = self.__get_commit_timestamp(proj_name, commit_id)
            branches[name] = {'commit_id': commit_id, 'timestamp': ts}

        return branches

