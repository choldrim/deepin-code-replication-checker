import json
import re
import os
from datetime import datetime

import requests

from utils.singleton import Singleton
from utils.config import Config

# for debug
CACHE_MODE = os.getenv('CACHE_MODE')

class GithubChecker(Singleton):

    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True

        if CACHE_MODE:
            self.project_data = self.__load_from_file('cache/github.json')
        else:
            self.project_data = self.__init_projects()

    def get_name(self):
        return 'Github'


    def __load_from_file(self, path):
        with open(path) as fp:
            data = json.load(fp)

        return data


    def __get_json(self, url):
        token = os.getenv('GITHUB_TOKEN')

        if not token:
            c = Config()
            token = c.data('github', 'token')

        h = {
                'Authorization': 'token %s' % token
            }
        r = requests.get(url, headers=h)
        r_json = r.json()

        while True:
            if not r.headers.get('Link'):
                break;

            a = re.compile('.*<(.+)>; rel="next".*')
            re_list = a.findall(r.headers.get('Link'))

            if not len(re_list):
                break;

            next_link = re_list[0]

            r = requests.get(next_link, headers=h)
            r_json += r.json()

        return r_json


    def __init_projects(self):
        print('initializing github project ...')
        project_data = {}
        projects = self.__get_json('https://api.github.com/users/linuxdeepin/repos?per_page=100')

        for p in projects:
            proj_name = p.get('name')
            print('getting project (%s)' % proj_name)
            branches = self.__get_branches(proj_name)
            project_data[proj_name] = {'branches': branches}

        return project_data


    def __get_branches(self, proj_name):
        branches = {}
        data = self.__get_json('https://api.github.com/repos/linuxdeepin/%s/branches' % proj_name)

        for b in data:
            name = b.get('name')
            commit_id = b.get('commit').get('sha')
            ts = self.__get_commit_timestamp(proj_name, commit_id)
            branches[name] = {'commit_id': commit_id, 'timestamp': ts}

        return branches

    def __get_commit_timestamp(self, project, commit_id):
        url = 'https://api.github.com/repos/linuxdeepin/%s/git/commits/%s' % (project, commit_id)
        data = self.__get_json(url)
        time_str = data.get('committer').get('date')
        ts = self.__handle_str_2_timestamp(time_str)

        return ts


    def __handle_str_2_timestamp(self, time_str):
        # like: 2016-04-01T06:43:07Z
        time_str = time_str.split('Z')[0]
        time_str += '+0000'
        d = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S%z')

        return d.timestamp()


    def check_project_exist(self, project_name):
        if project_name in self.project_data:
            return True

        return False


    def check_branch_exist(self, project_name, branch_name):
        if project_name in self.project_data \
                and branch_name in self.project_data.get(project_name).get('branches'):
            return True

        return False


    def check_branch_commit(self, project_name, branch_name, commit_id):
        if project_name in self.project_data \
                and branch_name in self.project_data.get(project_name).get('branches') \
                and commit_id == self.project_data.get(project_name).get('branches')\
                .get(branch_name).get('commit_id'):
            return True

        return False

    def get_timestamp(self, project_name, branch_name):
        if project_name in self.project_data \
                and branch_name in self.project_data.get(project_name).get('branches'):
            ts = self.project_data.get(project_name).get('branches').get(branch_name)\
                    .get('timestamp')
            return ts

        return 0

