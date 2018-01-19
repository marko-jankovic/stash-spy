#!/usr/bin/python

import stashy;
import os;
import re;
import subprocess;
import argparse;
import logging;
import sys;
import signal;
import time;

#logging.basicConfig(
#    format='%(asctime)s %(name)s: %(levelname)s %(message)s (#pid %(process)d)',
#    datefmt='%H:%M:%S',
#    level=10
#);

logging.basicConfig(
    format='%(message)s',
    level=10
);

logger = logging.getLogger('stash-spy');

class StashTrace:
    def __init__(self, args = None):
        # Create CLI Parser
        parser = argparse.ArgumentParser(description='stashy arguments');

        # URL and account variables
        parser.add_argument('-url', action='store', dest='stashUrl', help='Stash Url');
        parser.add_argument('-username', action='store', dest='username', help='Stash Login Username');
        parser.add_argument('-user', action='store', dest='user', help='User Email');
        parser.add_argument('-password', action='store', dest='password', help='Stash Login Password');
        parser.add_argument('-dest', action='store', dest='dest', help='Folder Path');
        parser.add_argument('-action', action='store', dest='action', help='Stash Action');
        parser.add_argument('-project', action='store', dest='project', help='Project Name');
        parser.add_argument('-olderThan', action='store', dest='olderThan', help='Set fetch time in minutes');

        signal.signal(signal.SIGINT, self.exitGracefully);
        signal.signal(signal.SIGTERM, self.exitGracefully);
        signal.signal(signal.SIGQUIT, self.exitGracefully);

        # Parsing CLI options
        argParams = parser.parse_args();

        # get {argParams.action} method
        return self.callMethod(argParams.action, argParams);


    def exitGracefully(self,signum, frame):
        logger.error('Gracefully Exit...');

    def callMethod(self, methodName, args):
        method = getattr(self, methodName);

        return method(args);

    # check if current folder is git
    def isGitFolder(self, path):
        return self.systemCall('git rev-parse --is-inside-work-tree --quiet', path);

    # save all users to file
    def getAllContributors(self, argParams):
        cwd = argParams.project or os.getcwd();

        for filename in os.listdir(cwd):
            if not filename.startswith('.'):
                abspath = os.path.abspath(os.path.join(cwd, filename));

                try:
                    isDir = os.path.isdir(abspath);
                except:
                    isDir = False;

                isGit = self.isGitFolder(abspath);
                dumpPath = os.path.abspath(cwd)  + '/all-users.txt';

                if isDir and isGit:
                    users = self.systemCall('git log --pretty="%an %ae%n%cn %ce" | sort | uniq', abspath);

                    if users:
                        with open(dumpPath, 'a') as dumpFile:
                            dumpFile.write('\n' + users);
                elif isDir:
                    subwd = abspath;

                    for filename in os.listdir(subwd):
                        if not filename.startswith('.'):
                            subabspath = os.path.abspath(os.path.join(subwd, filename));
                            isDir = os.path.isdir(subabspath);
                            isGit = self.isGitFolder(subabspath);

                            if isDir and isGit:
                                users = self.systemCall('git log --pretty="%an %ae%n%cn %ce" | sort | uniq', subabspath);

                                if users:
                                    with open(dumpPath, 'a') as dumpFile:
                                        dumpFile.write('\n' + users);

                                    # read line by line
                                    uniqlines = set(open(dumpPath).readlines());
                                    # sort lines and write to file
                                    open(dumpPath, 'w').writelines(sorted(uniqlines));

    # extract all commits by user name
    def getAllCommitsByUserName(self, argParams):
        cwd = argParams.project or os.getcwd();

        for filename in os.listdir(cwd):
            if not filename.startswith('.'):
                abspath = os.path.abspath(os.path.join(cwd, filename));

                try:
                    isDir = os.path.isdir(abspath);
                except:
                    isDir = False;

                isGit = self.isGitFolder(abspath);
                dumpName = argParams.user.split('@')[0];
                dumpPath = os.path.abspath(cwd)  + '/' + dumpName + '.txt';

                if isDir and isGit:
                    log = self.systemCall('git log --all --no-merges --author="<' + argParams.user + '>" --pretty=tformat:"%ar %s"', abspath);

                    if log:
                        with open(dumpPath, 'a') as dumpFile:
                            dumpFile.write('\n\n### ' + filename + ' ### \n\n' + log)
                elif isDir:
                    subwd = abspath;

                    for filename in os.listdir(subwd):
                        if not filename.startswith('.'):
                            subabspath = os.path.abspath(os.path.join(subwd, filename));
                            isDir = os.path.isdir(subabspath);
                            isGit = self.isGitFolder(subabspath);

                            if isDir and isGit:
                                log = self.systemCall('git log --all --no-merges --author="<' + argParams.user + '>" --pretty=tformat:"%ar %s"', subabspath);

                                if log:
                                    with open(dumpPath, 'a') as dumpFile:
                                        dumpFile.write('\n\n### ' + filename + ' ### \n\n' + log)


    def clone(self, argParams):
        # stash url, username and password are mandatory
        if not (argParams.stashUrl and argParams.username and argParams.password):
            logger.error('Stashy login requires username, password and stash url')
            exit();

        # Connect to stash
        stash = stashy.connect(argParams.stashUrl, argParams.username, argParams.password);

        # if dest is not defined save in root
        dest = '../' + argParams.dest if argParams.dest else './';

        if argParams.project:
            projectList = stash.projects[argParams.project].repos.list();

            self.cloneAllRepos(dest, argParams.project, projectList, argParams.olderThan);
        else:
            # Iterate over all projects (that you have access to)
            allProjects = stash.projects.list();

            for project in allProjects:
                projectList = stash.projects[project[unicode('key')]].repos.list();

                self.cloneAllRepos(dest, project[unicode('key')], projectList, argParams.olderThan);


    def checkMtime(self, dest, projectName, repoName, olderThan):
        # hidden dir path
        tmpDir = os.path.abspath(os.path.join(dest, projectName, '.tmp'));
        # tmp file path
        tmpFile = os.path.join(tmpDir, repoName);

        # create hidden dir for storing tmp files
        if not os.path.exists(tmpDir): os.makedirs(tmpDir);

        # most recent content modification expressed in seconds
        if os.path.isfile(tmpFile):
            mtime = os.stat(tmpFile).st_mtime;
        else:
            mtime = 0;

        # determine how old is file in seconds
        minOld = int((time.time() - mtime)/60);
        humanTime = time.strftime("%M:%S", time.gmtime(time.time() - mtime));

        if minOld >= int(olderThan or 1):
            # create temp file
            open(tmpFile, 'w').close();

            return True;
        else:
            logger.debug(' ... %s/%s has been updated before %s min', projectName, repoName, humanTime);
            return False;

    def cloneAllRepos(self, dest, projectName , projectList, olderThan):
        logger.debug('\n### %s ###', projectName);

        for repo in projectList:

            # repo name
            repoName = repo[unicode('name')].replace(' ', '-').lower();

            # replace space with dash and lowercase
            projectPath = os.path.join(projectName, repoName);

            # absolute dir path
            gitDir = os.path.abspath(os.path.join(dest, projectPath));

            logger.debug('\n> Checking #%s/%s ...', projectName, repoName);
            # check if last pull happend before N minutes
            shouldRun = self.checkMtime(dest, projectName, repoName, olderThan);

            if shouldRun is True:
                # clone repo if dir does not exist
                if (os.path.exists(gitDir) == False):

                    # repo clone url
                    cloneUrl = repo[unicode('cloneUrl')];

                    # clone repo in root/projectName/repoName
                    self.systemCall('git clone ' + cloneUrl + ' ' + gitDir);

                    # check if dir has .git
                    isGit = self.isGitFolder(gitDir);

                    if isGit != False:
                        self.checkRepo(gitDir)
                else:
                    self.checkRepo(gitDir, True);


    def systemCall(self, command, cwd = None):
        try:
            if cwd:
                # fix for "fatal: Unable to create '/*/.git/index.lock': File exists."
                subprocess.check_output('cd ' + cwd + ' && ' + 'find ./.git -name "*.lock" -type f -delete 2>/dev/null', shell=True);

                output = subprocess.check_output('cd ' + cwd + ' && ' + command, shell=True);
            else:
                output = subprocess.check_output(command, shell=True);

            if len(output) > 0:
                return output;

            else:
                return False;

        except:
            return False;


    def verifyBranch(self, branchName, gitDir):
        return self.systemCall('git rev-parse --verify --quiet ' + branchName, gitDir)


    def checkRepo (self, gitDir, exist = None):
        projectName = gitDir.split('/')[-1];

        logger.debug('  ... git fetch --prune "%s" ...', projectName);
        # deleting the refs to the branches
        # that don't exist on the remote
        self.systemCall('git fetch --prune --quiet', gitDir);

        logger.debug('  ... grep all "%s" branches ....', projectName);
        # get list of all remotes
        grepBranhes = self.systemCall('git branch --all --quiet | grep origin | grep -v master | grep -v HEAD', gitDir)

        if grepBranhes != False:
            # branch list, replace space and asterisk
            allBranches = re.sub('\s+|\*', ' ', grepBranhes).strip().split(' ');

            # git checkout for each branch and git pull
            for branch in allBranches:
                # branch name
                branchName = branch.replace('remotes/origin/', '');

                # if branch does not exists localy
                if self.verifyBranch(branchName, gitDir) is False:
                    logger.debug('  ... switching to origin/%s branch ....', branchName);
                    # create local branch {branchName}
                    self.systemCall('git branch ' + branchName + ' origin/' + branchName + ' --quiet', gitDir);
                else:
                    logger.debug('\n  ... git checkout #%s ....', branchName);
                    self.systemCall('git checkout -B ' + branchName + ' --force --quiet', gitDir);

                    logger.debug('  ... git fetch --all ....');
                    self.systemCall('git fetch --all --quiet', gitDir);

                    logger.debug('  ... git reset --hard origin/%s....', branchName);
                    # "git fetch" downloads the latest from remote without trying to merge or rebase anything
                    # "git reset" for reseting the origin/{branchName} branch to what we just fetched
                    # --hard option changes all the files in working tree to match the files in origin/{branchName}
                    self.systemCall('git reset --hard --quiet origin/' + branchName, gitDir);

                    logger.debug('  ... git pull origin %s....', branchName);
                    self.systemCall('git pull origin ' + branchName + ' --quiet', gitDir);


StashTrace()