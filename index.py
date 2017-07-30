#!/usr/bin/python

import stashy;
import sys
import os
import re
import subprocess
import argparse

class StashTrace:
    def __init__(self, args = None):
        parser = argparse.ArgumentParser(description='stashy arguments');

        # URL and account variables
        parser.add_argument('-url', action='store', dest='stashUrl', help='Stash Url');
        parser.add_argument('-username', action='store', dest='username', help='Stash Username');
        parser.add_argument('-password', action='store', dest='password', help='Stash Password');
        parser.add_argument('-dest', action='store', dest='dest', help='Destination');
        parser.add_argument('-action', action='store', dest='action', help='Action');

        argParams = parser.parse_args();

        getattr(self, argParams.action)(argParams);


    def fetch(self, argParams):
        if not (argParams.stashUrl and argParams.username and argParams.password):
            print "Stashy login requires username, password and stash url"
            exit();

        # if dest is not defined save in root
        dest = "../" + argParams.dest if argParams.dest else "./";

        # Connect to stash
        stash = stashy.connect(argParams.stashUrl, argParams.username, argParams.password);

        # Iterate over all projects (that you have access to)
        allRepos = stash.projects.list();

        for repo in allRepos:
            # repo name
            repoName = repo[unicode("key")];

            # list of projects
            repoList = stash.projects[repoName].repos.list();

            for projectList in repoList:

                # project name
                projectName = projectList[unicode("name")];

                # absolut dir path
                gitDir = os.path.abspath(dest + "/" + repoName + "/" + projectName);

                # clone project if dir does not exist
                if (os.path.exists(gitDir) == False):

                    # project clone url
                    cloneUrl = projectList[unicode("cloneUrl")];

                    # clone project in root/repoName/projectName
                    self.systemCall("git clone " + cloneUrl + " " + gitDir);

                    # check if dir has .git
                    isGit = self.systemCall("git rev-parse --is-inside-work-tree", gitDir);

                    if isGit != False:
                        print "#####", repoName + "/" + projectName, "#####"
                        self.checkRepo(gitDir)
                        print "-----------------------------------------\n"

                else:
                    print "#####", repoName + "/" + projectName, "#####"
                    self.checkRepo(gitDir, True)
                    print "-----------------------------------------\n"


    def systemCall(self, command, cwd = None):
        # --quiet

        try:
            if cwd:
                output = subprocess.check_output("cd " + cwd + " && " + command, shell=True)
            else:
                output = subprocess.check_output(command, shell=True)

            if len(output) > 0:
                return output

            else:
                return False

        except:
            return False


    def isBranchExist(self, branchName, gitDir):
        return self.systemCall("git branch | grep -w " + branchName, gitDir)


    def checkRepo (self, gitDir, exist = None):
        # deleting the refs to the branches
        # that don't exist on the remote
        self.systemCall("git fetch --prune", gitDir);

        # get list of all remotes
        grepBranhes = self.systemCall("git branch --all | grep origin | grep -v master | grep -v HEAD", gitDir)

        if grepBranhes != False:

            # branch list
            allBranches = re.sub("\s+", " ", grepBranhes).strip().split(" ");

            # git checkout for each branch and git pull
            for branch in allBranches:
                # branch name
                branchName = branch.replace("remotes/origin/", "");

                # if branch exists do --track
                if self.isBranchExist(branchName, gitDir) is False:
                    self.systemCall("git checkout --track " + branchName  + " origin/" + branchName, gitDir);
                else:
                    # checkout branch
                    self.systemCall("git checkout " + branchName, gitDir);

                # --ff-only Refuse to merge and exit with a non-zero status unless the current
                # HEAD is already up-to-date or the merge can be resolved as a fast-forward
                if exist == True:
                    self.systemCall("git pull --ff-only", gitDir);


StashTrace()