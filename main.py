#!/usr/bin/python3

import json
import os
from datetime import datetime

import requests
from terminaltables import SingleTable, AsciiTable

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

CHARGE_CACHE = os.getenv('CHARGE_CACHE')

def check_commit_deltatime(commit_timestamp):
    now_ts = datetime.now().timestamp()

    if (now_ts - commit_timestamp) <= (DELTATIME_MINUTE * 60):
        return True

    return False


def work():
    results = {}

    checkers = []
    base = Gerrit()

    checkers.append(GitlabChecker())
    checkers.append(GithubChecker())

    for c in checkers:
        print('xxxxxxxxxxxxxxxxxx %s xxxxxxxxxxxxxxxxxxxxxxx' % (c.get_name()))
        result = check(base, c)
        results[c.get_name()] = result

    gen_report(results)


def check(base, target):
    problems = {}
    base_projects = base.project_data

    for (project_orig_name, p) in base_projects.items():
        problem = ''
        project_name = project_orig_name.split('/')[-1:][0]
        print()
        warning('----------------- %s ------------------' % project_name)

        if not target.check_project_exist(project_name):
            msg = 'project (%s) not found' % project_name
            fail('P: ' + msg)
            problem += msg + '\n'
            continue

        for (branch_name, b) in p.get('branches').items():
            if not target.check_branch_exist(project_name, branch_name):
                msg = 'branch (%s) not found' % branch_name
                fail('P: ' + msg)
                problem += msg + '\n'
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
                msg = 'latest commit time (%s) is older than gerrit commit time (%s)' % (str(d2), str(d1))
                fail('P: ' + msg)
                problem += msg + '\n'

        if len(problem):
            problems[project_name] = problem

    return problems


def gen_report(results):
    # ready reports file
    os.makedirs('reports', exist_ok=True)
    fp = open('reports/index.html', 'w')

    for (name, result) in results.items():
        table_data = []
        table_data.append(['project', 'problem(s)'])

        for (proj_name, problem) in result.items():
            table_data.append([proj_name, problem])

        term_table = AsciiTable(table_data, name)
        term_table.inner_row_border = True
        table_str = term_table.table
        table_html = table_str.replace('\n', '<br>').replace(' ', '&nbsp')
        table_html = '<p>%s</p>' % table_html
        fp.write(table_html)
        print(table_str)

    if os.getenv('JOB_NAME') and os.getenv('BUILD_NUMBER'):
        report_url = 'https://ci.deepin.io/job/%s/%s/HTML_Report/' % (os.getenv('JOB_NAME'), os.getenv('BUILD_NUMBER'))
        print('For jenkins console: %s' % report_url)


def charge_cache():
    print('charging cache...')

    os.makedirs('cache', exist_ok=True)

    gr_cache_file = 'cache/gitlab.json'
    gr = Gerrit()
    with open(gr_cache_file, 'w') as fp:
        json.dump(gr.project_data, fp, indent=4, sort_keys=True)

    gl_cache_file = 'cache/gitlab.json'
    gl = GitlabChecker()
    with open(gl_cache_file, 'w') as fp:
        json.dump(gl.project_data, fp, indent=4, sort_keys=True)

    gh_cache_file = 'cache/github.json'
    gh = GithubChecker()
    with open(gh_cache_file, 'w') as fp:
        json.dump(gh.project_data, fp, indent=4, sort_keys=True)


if __name__ == '__main__':
    if CHARGE_CACHE:
        charge_cache()

    if CACHE_MODE:
        print('cache mode(for debug), load data from cache file')

    work()
