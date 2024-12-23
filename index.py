import os
import subprocess
import logging
import time
import argparse
from github import Github
from stashy import Stash
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging configuration for displaying logs
logging.basicConfig(format='%(message)s', level=logging.DEBUG)
logger = logging.getLogger('git-repo-analyzer')

class GitRepoAnalyzer:
    def __init__(self, args=None):
        # Create CLI Parser to handle command-line arguments
        parser = argparse.ArgumentParser(description='GitHub and Stash arguments')
        
        # Define the CLI arguments that control the behavior of the script
        parser.add_argument('-token', action='store', dest='token', help='API Token for GitHub or Stash', required=True)
        parser.add_argument('-username', action='store', dest='username', help='GitHub Username or Stash Username', required=True)
        parser.add_argument('-dest', action='store', dest='dest', help='Destination Folder for Cloning Repositories', required=True)
        parser.add_argument('-action', action='store', dest='action', help='Action to Perform (clone, analyze, etc.)', required=True)
        parser.add_argument('-project', action='store', dest='project', help='GitHub or Stash Project Name')  # Optional for clone
        parser.add_argument('-olderThan', action='store', dest='olderThan', type=int, help='Time (in minutes) since last modification to consider')
        parser.add_argument('-rate-limit', action='store', dest='rate_limit', type=int, default=60, help='Rate limit time window (seconds) for API requests')
        parser.add_argument('-platform', action='store', dest='platform', choices=['github', 'stash'], help='Platform to use (GitHub or Stash)', required=True)
        parser.add_argument('-stash-url', action='store', dest='stash_url', help='Stash Server URL', required=False)  # Stash URL argument

        # Parse arguments
        argParams = parser.parse_args()
        self.args = argParams

        # Perform argument validation to ensure necessary inputs are provided
        self.validate_arguments()

        # Dynamically call a method based on the provided 'action' argument
        self.callMethod(argParams.action)

    def validate_arguments(self):
        """Validate that all required arguments are provided"""
        if not self.args.token:
            logger.error("Error: -token is required.")
            exit(1)
        if not self.args.username:
            logger.error("Error: -username is required.")
            exit(1)
        if not self.args.dest:
            logger.error("Error: -dest is required.")
            exit(1)
        if not self.args.action:
            logger.error("Error: -action is required.")
            exit(1)
        if not self.args.platform:
            logger.error("Error: -platform is required (either 'github' or 'stash').")
            exit(1)
        if self.args.platform == 'stash' and not self.args.stash_url:
            logger.error("Error: -stash-url is required when using the Stash platform.")
            exit(1)

    def callMethod(self, methodName):
        """Dynamically call a method based on the action specified in CLI args"""
        try:
            method = getattr(self, methodName)
            method()
        except AttributeError:
            logger.error(f"Error: The action '{methodName}' is not valid.")
            exit(1)
        except Exception as e:
            logger.error(f"Unexpected error occurred: {str(e)}")
            exit(1)

    def isGitFolder(self, path):
        """Check if the given path is a Git repository by looking for the .git directory"""
        return os.path.isdir(os.path.join(path, '.git'))

    def systemCall(self, command, cwd=None):
        """Execute a shell command and return the output"""
        try:
            # Execute the command in the specified directory (cwd), if provided
            if cwd:
                output = subprocess.check_output(f'cd {cwd} && {command}', shell=True)
            else:
                output = subprocess.check_output(command, shell=True)

            return output.decode('utf-8') if output else False
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing command: {command}, Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during system call: {str(e)}")
            return False

    def check_rate_limit(self, platform_instance):
        """Check the API rate limit for GitHub or Stash and wait if necessary"""
        try:
            # Handle rate limiting for GitHub
            if self.args.platform == 'github':
                rate_limit = platform_instance.get_rate_limit().core
                remaining_requests = rate_limit.remaining
                reset_time = rate_limit.reset
                current_time = time.time()

                if remaining_requests == 0:
                    wait_time = reset_time - current_time + 1  # Adding 1 second for safety
                    logger.info(f"GitHub Rate limit exceeded. Waiting for {wait_time} seconds.")
                    time.sleep(wait_time)

            # Placeholder for Stash rate limit handling (needs adjustment for Stash API)
            elif self.args.platform == 'stash':
                remaining_requests = platform_instance.get_rate_limit()  # Placeholder for Stash rate limit check
                if remaining_requests == 0:
                    logger.info("Stash rate limit exceeded. Waiting for reset.")
                    time.sleep(60)  # Placeholder for Stash rate limiting, adjust accordingly.
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            exit(1)

    def cloneRepos(self):
        """Clone repositories from GitHub or Stash based on the provided arguments"""
        try:
            token = self.args.token
            username = self.args.username
            dest = self.args.dest or os.getcwd()

            if self.args.platform == 'github':
                self.cloneGitHubRepos(dest, username, token)
            elif self.args.platform == 'stash':
                stash_url = self.args.stash_url
                self.cloneStashRepos(dest, token, stash_url)
        except Exception as e:
            logger.error(f"Error during repository cloning: {str(e)}")
            exit(1)

    def cloneGitHubRepos(self, dest, username, token):
        """Clone repositories from a GitHub user or organization with pagination"""
        try:
            # Initialize the GitHub API client
            g = Github(token)
            self.check_rate_limit(g)  # Check GitHub API rate limits

            user = g.get_user(username)
            repo_list = []
            page = 1
            per_page = 30  # The number of repositories per page

            if user.type == 'Organization':
                logger.info(f"Cloning repositories from GitHub organization: {username}")
                org_repos = g.get_organization(username).get_repos()
            else:
                logger.info(f"Cloning repositories from GitHub user: {username}")
                org_repos = user.get_repos()

            # Paginate through all pages to get all repositories
            while org_repos:
                for repo in org_repos:
                    repo_list.append(repo)

                # Check if there are more repositories to fetch
                if len(org_repos) == per_page:
                    page += 1
                    org_repos = user.get_repos(page=page, per_page=per_page)
                else:
                    break

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for repo in repo_list:
                    futures.append(executor.submit(self.clone_repo, repo, dest))

                # Wait for all tasks to finish
                for future in as_completed(futures):
                    future.result()

        except Exception as e:
            logger.error(f"Error fetching GitHub repositories: {e}")
            exit(1)

    def cloneStashRepos(self, dest, token, stash_url):
        """Clone all repositories from a Stash project with pagination"""
        try:
            # Initialize the Stash API client
            stash = Stash(stash_url, token)
            self.check_rate_limit(stash)  # Check Stash API rate limits

            repo_list = []
            start = 0
            limit = 50  # Adjust based on the number of repositories per request

            # Loop through all pages of Stash repositories
            while True:
                project_repos = stash.repositories.list(start=start, limit=limit)
                repo_list.extend(project_repos)

                # Check if there are more repositories to fetch
                if len(project_repos) < limit:
                    break
                else:
                    start += limit

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for repo in repo_list:
                    futures.append(executor.submit(self.clone_repo_from_stash, repo, dest))

                # Wait for all tasks to finish
                for future in as_completed(futures):
                    future.result()

        except Exception as e:
            logger.error(f"Error fetching Stash repositories: {e}")
            exit(1)

    def clone_repo_from_stash(self, repo, dest):
        """Clone a single repository from Stash (Bitbucket Server)"""
        try:
            # Extract repository details
            repo_name = repo['name']
            clone_url = repo['links']['clone'][0]['href']
            repo_dest = os.path.join(dest, repo_name)

            if not os.path.exists(repo_dest):
                logger.info(f"Cloning {repo_name} from Stash to {repo_dest}")
                self.systemCall(f'git clone {clone_url} {repo_dest}')
                self.fetchAndPullBranches(repo_dest)  # Pull all branches after cloning
            else:
                logger.info(f"Repository {repo_name} already exists. Skipping.")
        except Exception as e:
            logger.error(f"Error cloning Stash repository {repo['name']}: {e}")
            exit(1)

    def clone_repo(self, repo, dest):
        """Clone a single GitHub repository"""
        try:
            # Extract repository details
            repo_name = repo.name
            clone_url = repo.clone_url
            repo_dest = os.path.join(dest, repo_name)

            if not os.path.exists(repo_dest):
                logger.info(f"Cloning {repo_name} to {repo_dest}")
                self.systemCall(f'git clone {clone_url} {repo_dest}')
                self.fetchAndPullBranches(repo_dest)  # Pull all branches after cloning
            else:
                logger.info(f"Repository {repo_name} already exists. Skipping.")
        except Exception as e:
            logger.error(f"Error cloning GitHub repository {repo.name}: {e}")
            exit(1)

    def fetchAndPullBranches(self, repo_dir):
        """Fetch all branches in a Git repository and pull them"""
        try:
            if not self.isGitFolder(repo_dir):
                logger.error(f"{repo_dir} is not a Git repository!")
                return

            logger.info(f"Fetching all branches in {repo_dir}")
            self.systemCall('git fetch --all', repo_dir)

            branches = self.systemCall('git branch -r', repo_dir)
            if branches:
                allBranches = branches.strip().split()
                for branch in allBranches:
                    branchName = branch.replace('remotes/origin/', '')
                    logger.info(f"Pulling branch {branchName} in {repo_dir}")
                    self.systemCall(f'git checkout {branchName} && git pull origin {branchName}', repo_dir)

        except Exception as e:
            logger.error(f"Error fetching or pulling branches in {repo_dir}: {e}")
            exit(1)

    def analyzeBranches(self, gitDir):
        """Analyze branches in a Git repository"""
        try:
            branches = self.systemCall('git branch -r', gitDir)
            if branches:
                allBranches = branches.strip().split()
                for branch in allBranches:
                    branchName = branch.replace('remotes/origin/', '')
                    logger.debug(f"Branch: {branchName}")
        except Exception as e:
            logger.error(f"Error analyzing branches in {gitDir}: {e}")
            exit(1)

    def analyzeCommits(self, gitDir):
        """Analyze commits in a Git repository"""
        try:
            commits = self.systemCall('git log --oneline', gitDir)
            if commits:
                for commit in commits.splitlines():
                    logger.debug(f"Commit: {commit}")
        except Exception as e:
            logger.error(f"Error analyzing commits in {gitDir}: {e}")
            exit(1)

    def checkMtime(self, path, older_than_minutes):
        """Check if the modification time of a file or directory is older than the specified time"""
        try:
            current_time = time.time()
            file_mtime = os.path.getmtime(path)
            age_in_minutes = (current_time - file_mtime) / 60

            if age_in_minutes > older_than_minutes:
                logger.info(f"File/Directory {path} has not been modified in the last {older_than_minutes} minutes.")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking modification time for {path}: {e}")
            exit(1)

    def analyzeAllRepos(self):
        """Analyze all repositories by checking branches and commits. Optionally, check for modification time"""
        try:
            dest = self.args.dest or os.getcwd()
            older_than_minutes = self.args.olderThan

            # Loop through repositories and analyze branches and commits
            for repo in os.listdir(dest):
                repo_path = os.path.join(dest, repo)
                if self.isGitFolder(repo_path):
                    # Optionally skip repositories that have not been modified recently
                    if older_than_minutes and not self.checkMtime(repo_path, older_than_minutes):
                        logger.info(f"Skipping {repo_path} as it hasn't been modified in the last {older_than_minutes} minutes.")
                        continue
                    self.analyzeBranches(repo_path)
                    self.analyzeCommits(repo_path)
        except Exception as e:
            logger.error(f"Error analyzing repositories in {self.args.dest}: {e}")
            exit(1)

if __name__ == "__main__":
    # Initialize GitRepoAnalyzer and run actions based on arguments
    GitRepoAnalyzer()
