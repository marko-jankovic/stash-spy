#!/usr/bin/python

import stashy
import os
import re
import subprocess
import argparse
import logging
import sys
import signal
import time
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger('stash-spy')

redirectErrors = True

class StashTrace:
    def __init__(self, args=None):
        # Create CLI Parser
        parser = argparse.ArgumentParser(description='Stashy arguments')

        # URL and account variables
        parser.add_argument('-url', action='store', dest='stashUrl', help='Stash Url')
        parser.add_argument('-username', action='store', dest='username', help='Stash Login Username')
        parser.add_argument('-user', action='store', dest='user', help='User Email')
        parser.add_argument('-password', action='store', dest='password', help='Stash Login Password')
        parser.add_argument('-dest', action='store', dest='dest', help='Folder Path')
        parser.add_argument('-action', action='store', dest='action', help='Stash Action')
        parser.add_argument('-project', action='store', dest='project', help='Project Name')
        parser.add_argument('-olderThan', action='store', dest='olderThan', help='Set fetch time in minutes')
        parser.add_argument('-log-level', action='store', dest='log_level', default='INFO', help='Set log level (DEBUG, INFO, ERROR)')

        signal.signal(signal.SIGINT, self.exitGracefully)
        signal.signal(signal.SIGTERM, self.exitGracefully)
        signal.signal(signal.SIGQUIT, self.exitGracefully)

        # Parsing CLI options
        argParams = parser.parse_args()

        # Set log level based on input argument
        log_levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'ERROR': logging.ERROR
        }
        log_level = log_levels.get(argParams.log_level.upper(), logging.INFO)
        logging.basicConfig(level=log_level)

        # Call method based on action
        return self.callMethod(argParams.action, argParams)

    def exitGracefully(self, signum, frame):
        logger.error('Gracefully Exit...')

    def callMethod(self, methodName, args):
        method = getattr(self, methodName)
        return method(args)

    def isGitFolder(self, path):
        if self.isDir(path):
            return self.systemCall('git rev-parse -q --is-inside-work-tree', path)
        return False

    def isDir(self, path):
        try:
            return os.path.isdir(path)
        except:
            return False

    def systemCall(self, command, cwd=None):
        # 2> redirects stderr to nowhere
        redirectStderr = ' 2>/dev/null' if redirectErrors else ''
        try:
            if cwd:
                subprocess.call(f'cd {cwd}{redirectStderr} && find ./.git -name "*.lock" -type f -delete{redirectStderr}', shell=True)
                output = subprocess.check_output(f'cd {cwd}{redirectStderr} && {command}{redirectStderr}', shell=True)
            else:
                output = subprocess.check_output(f'{command}{redirectStderr}', shell=True)

            if len(output) > 0:
                return output
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess failed with error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    def rate_limited_call(self, command, cwd=None, rate_limit_delay=2):
        output = self.systemCall(command, cwd)
        time.sleep(rate_limit_delay)
        return output

    def cloneAllRepos(self, dest, projectName, projectList):
        logger.debug(f'\n### {projectName} ###')

        def clone_repo(repo):
            repoName = repo[unicode('name')].replace(' ', '-').lower()
            projectPath = os.path.join(projectName, repoName)
            gitDir = os.path.abspath(os.path.join(dest, projectPath))

            if not os.path.exists(gitDir) or not self.isGitFolder(gitDir):
                cloneUrl = repo[unicode('cloneUrl')]
                self.systemCall(f'git clone {cloneUrl} {gitDir}')
                self.checkRepo(gitDir)
            else:
                self.checkRepo(gitDir, True)

        with ThreadPoolExecutor() as executor:
            executor.map(clone_repo, projectList)

    def cleanStaleRepos(self, dest, threshold_days=30):
        cutoff_time = time.time() - (threshold_days * 86400)

        for root, dirs, files in os.walk(dest):
            for dir_name in dirs:
                repo_path = os.path.join(root, dir_name)
                if os.path.isdir(repo_path) and self.isGitFolder(repo_path):
                    mtime = os.stat(repo_path).st_mtime
                    if mtime < cutoff_time:
                        logger.info(f"Removing stale repository: {repo_path}")
                        self.systemCall(f'rm -rf {repo_path}')

    def backup_repo(self, gitDir, backup_remote='backup'):
        self.systemCall(f'git remote add {backup_remote} <backup-repository-url> || true', gitDir)
        self.systemCall(f'git push {backup_remote} --all', gitDir)
        self.systemCall(f'git push {backup_remote} --tags', gitDir)

    def checkRepo(self, gitDir, exist=None):
        projectName = gitDir.split('/')[-1]
        logger.debug(f'  ... git fetch --prune "{projectName}" ...')
        self.systemCall('git fetch --prune --quiet', gitDir)

        logger.debug(f'  ... grep all "{projectName}" branches ....')
        grepBranhes = self.systemCall('git branch --all --quiet | grep origin | grep -v HEAD', gitDir)

        if grepBranhes:
            allBranches = re.sub('\s+|\*', ' ', grepBranhes).strip().split(' ')

            for branch in allBranches:
                branchName = branch.replace('remotes/origin/', '')

                if self.verifyBranch(branchName, gitDir):
                    logger.debug(f'\n  ... git checkout #{branchName} ....')
                    self.systemCall(f'git checkout -B {branchName} --force --quiet', gitDir)

                    logger.debug(f'  ... git reset --hard origin/{branchName}....')
                    self.systemCall(f'git reset --hard --quiet origin/{branchName}', gitDir)
                else:
                    logger.debug(f'  ... switching to origin/{branchName} branch ....')
                    self.systemCall(f'git branch {branchName} origin/{branchName} --quiet', gitDir)

    def verifyBranch(self, branchName, gitDir):
        return self.systemCall(f'git rev-parse --verify --quiet {branchName}', gitDir)

    def get_github_repos(self, user, token):
        url = f'https://api.github.com/users/{user}/repos'
        headers = {'Authorization': f'token {token}'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()  # List of repos
        else:
            logger.error("Failed to fetch repositories")
            return []

    def pull(self, argParams):
        cwd = argParams.project or os.getcwd()
        projectName = cwd.split('/')[-1]
        logger.debug(f'\n### {cwd} ###')

        for filename in os.listdir(cwd):
            if not filename.startswith('.'):
                abspath = os.path.abspath(os.path.join(cwd, filename))

                if self.isGitFolder(abspath):
                    logger.debug(f'\n> Checking #{argParams.project}/{filename} ...')
                    shouldRun = self.checkMtime(abspath, projectName, filename, argParams.olderThan)

                    if shouldRun:
                        self.checkRepo(abspath, True)

                elif self.isDir(abspath):
                    subwd = abspath

                    for dirName in os.listdir(subwd):
                        if not dirName.startswith('.'):
                            subabspath = os.path.abspath(os.path.join(subwd, dirName))

                            if self.isGitFolder(subabspath):
                                logger.debug(f'\n> Checking #{projectName}/{dirName} ...')
                                shouldRun = self.checkMtime(subabspath, projectName, dirName, argParams.olderThan)

                                if shouldRun:
                                    self.checkRepo(subabspath, True)

    def checkMtime(self, dest, projectName, repoName, olderThan):
        tmpDir = os.path.abspath(os.path.join(dest, projectName, '.tmp'))
        tmpFile = os.path.join(tmpDir, repoName)

        if not os.path.exists(tmpDir): 
            os.makedirs(tmpDir)

        if os.path.isfile(tmpFile):
            mtime = os.stat(tmpFile).st_mtime
        else:
            mtime = 0

        minOld = int((time.time() - mtime) / 60)
        humanTime = time.strftime("%M:%S", time.gmtime(time.time() - mtime))

        if minOld >= int(olderThan or 1):
            open(tmpFile, 'w').close()
            return True
        else:
            logger.debug(f' ... {projectName}/{repoName} has been updated before {humanTime} min')
            return False

    def clone(self, argParams):
        if not (argParams.stashUrl and argParams.username and argParams.password):
            logger.error('Stashy login requires username, password and stash url')
            exit()

        stash = stashy.connect(argParams.stashUrl, argParams.username, argParams.password)

        dest = '../' + argParams.dest if argParams.dest else './'

        if argParams.project:
            projectList = stash.projects[argParams.project].repos.list()
            self.cloneAllRepos(dest, argParams.project, projectList)
        else:
            allProjects = stash.projects.list()

            for project in allProjects:
                projectList = stash.projects[project['key']].repos.list()
                self.cloneAllRepos(dest, project['key'], projectList)

StashTrace()
