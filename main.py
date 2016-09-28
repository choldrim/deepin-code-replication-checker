#!/usr/bin/python3

import json
import os
from datetime import datetime

from terminaltables import AsciiTable

from lib.gerrit import Gerrit
from lib.gitlab import GitlabChecker
from lib.github import GithubChecker
from lib.bearychat import Bearychat
from utils.color_print import warning
from utils.color_print import success
from utils.color_print import fail

DELTATIME_MINUTE = 10

# for debug
CACHE_MODE = os.getenv('CACHE_MODE')


def check_commit_deltatime(commit_timestamp):
    now_ts = datetime.now().timestamp()

    if (now_ts - commit_timestamp) <= (DELTATIME_MINUTE * 60):
        return True

    return False


def work():
    results = {}

    base = Gerrit()
    gl = GitlabChecker()
    gh = GithubChecker()

    charge_cache(base, gl, gh)

    print('xxxxxxxxxxxxxxxxxx %s xxxxxxxxxxxxxxxxxxxxxxx' % (gl.get_name()))
    results[gl.get_name()] = check(base, gl, with_private=True)

    print('xxxxxxxxxxxxxxxxxx %s xxxxxxxxxxxxxxxxxxxxxxx' % (gh.get_name()))
    results[gh.get_name()] = check(base, gh)

    gen_report(results)

    push_bc_msg(results)


def check(base, target, with_private=False):
    problems = {}

    if with_private:
        base_projects = base.project_data_all
    else:
        base_projects = base.project_data_public

    for (project_orig_name, p) in base_projects.items():
        problem = ''
        project_name = project_orig_name.split('/')[-1:][0]
        print()
        warning('----------------- %s ------------------' % project_name)

        if not target.check_project_exist(project_name):
            msg = 'project (%s) not found' % project_name
            fail('P: ' + msg)
            problem += 'project not found\n'
            problems[project_name] = problem
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
                print('maybe a young commit on %s, skip' % str(d))
                continue
            else:
                base_commit_time = datetime.fromtimestamp(b.get('timestamp'))
                target_commit_time = datetime.fromtimestamp(target.get_timestamp(project_name, branch_name))
                if target_commit_time > base_commit_time:
                    print('maybe commit during checking process')
                    continue

                target_commit = target.get_latest_commit(project_name, branch_name)[:7]
                base_commit = b.get('commit_id')[:7]
                msg = 'target branch (%s) latest commit(%s) time(%s) != gerrit latest commit(%s) time(%s)' \
                      % (branch_name, target_commit, str(target_commit_time), base_commit, str(base_commit_time))
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
        table_str = '\n\n' + table_str
        table_html = table_str.replace('\n', '<br>').replace(' ', '&nbsp')
        table_html = '<p>%s</p>' % table_html
        fp.write(table_html)
        print(table_str)

    if os.getenv('JOB_NAME') and os.getenv('BUILD_NUMBER'):
        report_url = 'https://ci.deepin.io/job/%s/%s/HTML_Report/' % (os.getenv('JOB_NAME'), os.getenv('BUILD_NUMBER'))
        print('Results Report: %s' % report_url)


def push_bc_msg(results):
    problem_str = ""
    for (t, projects) in results.items():
        if len(projects):
            problem_str += "-- **%s** --\n" % t

        for (proj_name, problem) in projects.items():
            problem_str += "%s: %s\n" % (proj_name, problem)

    bc = Bearychat()
    bc.say(problem_str)


def charge_cache(gr, gl, gh):
    print('charging cache...')

    os.makedirs('cache', exist_ok=True)

    gr_cache_file = 'cache/gerrit_public.json'
    with open(gr_cache_file, 'w') as fp:
        json.dump(gr.project_data_public, fp, indent=4, sort_keys=True)

    gr_cache_file = 'cache/gerrit_all.json'
    with open(gr_cache_file, 'w') as fp:
        json.dump(gr.project_data_all, fp, indent=4, sort_keys=True)

    gl_cache_file = 'cache/gitlab.json'
    with open(gl_cache_file, 'w') as fp:
        json.dump(gl.project_data, fp, indent=4, sort_keys=True)

    gh_cache_file = 'cache/github.json'
    with open(gh_cache_file, 'w') as fp:
        json.dump(gh.project_data, fp, indent=4, sort_keys=True)


if __name__ == '__main__':
    if CACHE_MODE:
        print('cache mode(for debug), load data from cache file')

    work()
