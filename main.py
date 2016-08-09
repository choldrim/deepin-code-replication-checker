#!/usr/bin/python3

import json
import re
import os
from configparser import ConfigParser
from datetime import datetime

import requests

from utils.singleton import Singleton
from utils.color_print import warning
from utils.color_print import success
from utils.color_print import fail
from utils.color_print import info

DELTATIME_MINUTE = 10
CONFIG_PATH = './config.ini'

# for debug
CACHE_MODE = os.getenv('CACHE_MODE')

class Config(Singleton):
    def __init__(self, path=CONFIG_PATH):
        if hasattr(self, '_init'):
            return
        self._init = True
        self.config = ConfigParser()
        self.config.read(path)

    def data(self, s, n):
        return self.config[s][n]


class GitlabChecker(Singleton):

    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True

        if CACHE_MODE:
            self.project_data = self.__load_from_file('cache/gitlab.json')
        else:
            self.project_data = self.__init_projects()

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
        project_data = {}
        projects = self.__get_json('https://bj.git.sndu.cn/api/v3/projects')

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

        

class Base:
    def __init__(self):
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
        project_data = {}
        data = self.__get_json('https://cr.deepin.io/projects/')

        for (proj_name, p) in data.items():
            print('getting project (%s)' % proj_name)
            p_id = p.get('id')
            branches = self.__get_branches(p_id)

            for (name, b) in branches.items():
                commit_id = b.get('commit_id')
                b['timestamp'] = self.__get_commit_timestamp(p_id, commit_id)

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


    def __get_branches(self, name):
        branches = {}
        data = self.__get_json('https://cr.deepin.io/projects/%s/branches' % name)

        for p in data:
            if p.get('ref') == 'HEAD':
                continue
            name = p.get('ref')
            if 'refs/heads/' in name:
                name = name.split('refs/heads/')[1]
            branches[name] = {'commit_id': p.get('revision')}

        return branches


def check_commit_deltatime(commit_timestamp):
    now_ts = datetime.now().timestamp()

    if (now_ts - commit_timestamp) <= (DELTATIME_MINUTE * 60):
        return True

    return False


def work():
    base = Base()

    # gitlab
    gitlab = GitlabChecker()
    check(base, gitlab)


def check(base, target):
    base_projects = base.project_data

    for (project_orig_name, p) in base_projects.items():
        project_name = project_orig_name.split('/')[-1:][0]
        print()
        warning('----------------- %s ------------------' % project_name)
        if not target.check_project_exist(project_name):
            fail('W: project (%s) not found' % project_name)
            continue

        for (branch_name, b) in p.get('branches').items():
            if not target.check_branch_exist(project_name, branch_name):
                fail('W: branch (%s) not found' % branch_name)
                continue

            # check commit id match
            if target.check_branch_commit(project_name, branch_name, b.get('commit_id')):
                success('branch (%s) matched' % branch_name)
                continue

            # else, check commit deltatime
            if check_commit_deltatime(b.get('timestamp')):
                d = datetime.fromtimestamp(b.get('timestamp'))
                print('may be a young commit on %s, skip' % str(d))
                continue
            else:
                d1 = datetime.fromtimestamp(b.get('timestamp'))
                d2 = datetime.fromtimestamp(target.get_timestamp(project_name, branch_name))
                fail('W: target commit (%s) is fallen behind base (%s)' % (str(d2), str(d1)))


def charge_cache():
    b = Base()
    with open('cache/gitlab.json', 'w') as fp:
        json.dump(b.project_data, fp, indent=4, sort_keys=True)

    b = GitlabChecker()
    with open('cache/gitlab.json', 'w') as fp:
        json.dump(b.project_data, fp, indent=4, sort_keys=True)


if __name__ == '__main__':
    #charge_cache()

    if CACHE_MODE:
        print('cache mode, load data from cache file')

    work()
