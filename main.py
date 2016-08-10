#!/usr/bin/python3

import json
import os
from datetime import datetime

import requests

from lib.gerrit import Gerrit
from lib.gitlab import GitlabChecker
from lib.github import GithubChecker
from utils.color_print import warning
from utils.color_print import success
from utils.color_print import fail
from utils.color_print import info

DELTATIME_MINUTE = 10

# for debug
CACHE_MODE = os.getenv('CACHE_MODE')

def check_commit_deltatime(commit_timestamp):
    now_ts = datetime.now().timestamp()

    if (now_ts - commit_timestamp) <= (DELTATIME_MINUTE * 60):
        return True

    return False


def work():
    checkers = []
    base = Gerrit()

    checkers.append(GitlabChecker())
    checkers.append(GithubChecker())

    for c in checkers:
        print('xxxxxxxxxxxxxxxxxx %s xxxxxxxxxxxxxxxxxxxxxxx' % (c.get_name()))
        check(base, c)


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
    print('charging cache...')

    gr_cache_file = 'cache/gitlab.json'
    if not os.path.exists(gr_cache_file):
        gr = Gerrit()
        with open(gr_cache_file, 'w') as fp:
            json.dump(gr.project_data, fp, indent=4, sort_keys=True)

    gl_cache_file = 'cache/gitlab.json'
    if not os.path.exists(gl_cache_file):
        gl = GitlabChecker()
        with open(gl_cache_file, 'w') as fp:
            json.dump(gl.project_data, fp, indent=4, sort_keys=True)

    gh_cache_file = 'cache/github.json'
    if not os.path.exists(gh_cache_file):
        gh = GithubChecker()
        with open(gh_cache_file, 'w') as fp:
            json.dump(gh.project_data, fp, indent=4, sort_keys=True)


if __name__ == '__main__':
    if CACHE_MODE:
        print('cache mode(for debug), load data from cache file')
        charge_cache()

    work()
