#!/usr/bin/python

import stashy;
import sys
import os
import re
import subprocess
import argparse

class StashTrace:
    def __init__(self, args = None):
        # Create CLI Parser
        parser = argparse.ArgumentParser(description='stashy arguments');

        # URL and account variables
        parser.add_argument('-url', action='store', dest='stashUrl', help='Stash Url');
        parser.add_argument('-username', action='store', dest='username', help='Stash Username');
        parser.add_argument('-password', action='store', dest='password', help='Stash Password');
        parser.add_argument('-dest', action='store', dest='dest', help='Folder Path');
        parser.add_argument('-action', action='store', dest='action', help='Stash Action');
        parser.add_argument('-project', action='store', dest='project', help='Project Name');

        # Parsing CLI options
        argParams = parser.parse_args();

        # get {argParams.action} method
        return self.callMethod(argParams.action, argParams);


    def callMethod(self, methodName, args):
        method = getattr(self, methodName);

        return method(args);


    def clone(self, argParams):
        # stash url, username and password are mandatory
        if not (argParams.stashUrl and argParams.username and argParams.password):
            print "Stashy login requires username, password and stash url"
            exit();

        # Connect to stash
        stash = stashy.connect(argParams.stashUrl, argParams.username, argParams.password);

        # if dest is not defined save in root
        dest = "../" + argParams.dest if argParams.dest else "./";

        if argParams.project:
            projectList = stash.projects[argParams.project].repos.list();

            self.cloneAllRepos(dest, argParams.project, projectList);
        else:
            # Iterate over all projects (that you have access to)
            allProjects = stash.projects.list();

            for project in allProjects:
                projectList = stash.projects[project[unicode("key")]].repos.list();

                self.cloneAllRepos(dest, project[unicode("key")], projectList);


    def cloneAllRepos(self, dest, projectName , projectList):
        for repo in projectList:

            # repo name
            repoName = repo[unicode("name")];

            projectPath = os.path.join(projectName, repoName);

            # absolut dir path
            gitDir = os.path.abspath(os.path.join(dest, projectPath));

            # clone repo if dir does not exist
            if (os.path.exists(gitDir) == False):

                # repo clone url
                cloneUrl = repo[unicode("cloneUrl")];

                # clone repo in root/projectName/repoName
                self.systemCall("git clone " + cloneUrl + " " + gitDir);

                # check if dir has .git
                isGit = self.systemCall("git rev-parse --is-inside-work-tree", gitDir);

                if isGit != False:
                    print "#####", projectPath, "#####"
                    self.checkRepo(gitDir)
                    print "-----------------------------------------\n"

            else:
                print "#####", projectPath, "#####"
                self.checkRepo(gitDir, True)
                print "-----------------------------------------\n"


    def systemCall(self, command, cwd = None):
        # --quiet

        try:
            if cwd:
                output = subprocess.check_output("cd " + cwd + " && " + command, shell=True)
            else:
                print "###################", command, "################";
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
                    self.systemCall("git checkout --track origin/" + branchName, gitDir);
                else:
                    # checkout branch
                    self.systemCall("git checkout " + branchName, gitDir);

                # --ff-only Refuse to merge and exit with a non-zero status unless the current
                # HEAD is already up-to-date or the merge can be resolved as a fast-forward
                if exist == True:
                    self.systemCall("git pull --ff-only", gitDir);


StashTrace()