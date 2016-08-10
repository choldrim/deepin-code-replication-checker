import json
import re
import os
from datetime import datetime

import requests

from utils.singleton import Singleton
from utils.config import Config

# for debug
CACHE_MODE = os.getenv('CACHE_MODE')

class GitlabChecker(Singleton):

    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True

        if CACHE_MODE:
            self.project_data = self.__load_from_file('cache/gitlab.json')
        else:
            self.project_data = self.__init_projects()


    def get_name(self):
        return 'Gitlab'


    def __load_from_file(self, path):
        with open(path) as fp:
            data = json.load(fp)

        return data


    def __get_json(self, url):
        token = os.getenv('GITLAB_TOKEN')
        if not token:
            c = Config()
            token = c.data('gitlab', 'token')
        h = {
                'PRIVATE-TOKEN': token
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
        print('initializing gitlab project ...')
        project_data = {}
        projects = self.__get_json('https://bj.git.sndu.cn/api/v3/projects?per_page=100')

        for p in projects:
            proj_name = p.get('name')
            print('getting project (%s)' % proj_name)
            p_id = p.get('id')
            branches = self.__get_branches(p_id)
            project_data[proj_name] = {'branches': branches}

        return project_data


    def __get_branches(self, p_id):
        branches = {}
        data = self.__get_json('https://bj.git.sndu.cn/api/v3/projects/%s/repository/branches' % p_id)

        for p in data:
            name = p.get('name')
            time_str = p.get('commit').get('committed_date')
            ts = self.__handle_str_2_timestamp(time_str)
            commit_id = p.get('commit').get('id')
            branches[name] = {'commit_id': commit_id, 'timestamp': ts}

        return branches


    def __handle_str_2_timestamp(self, time_str):
        # like: 2014-12-16T08:45:45.000+08:00
        a = re.compile('.+(\.[0-9]{3})[+-].+')
        spliter = a.findall(time_str)[0]
        tmp_list = time_str.split(spliter)
        time_base = tmp_list[0]
        timezone = tmp_list[1].replace(":", "")
        new_time_str = time_base + timezone
        d = datetime.strptime(new_time_str, '%Y-%m-%dT%H:%M:%S%z')

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
