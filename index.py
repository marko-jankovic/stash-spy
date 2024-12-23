import os
import subprocess
import logging
import time
import argparse
from github import Github
from stashy import Stash
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging configuration
logging.basicConfig(format='%(message)s', level=logging.DEBUG)
logger = logging.getLogger('git-repo-analyzer')

class GitRepoAnalyzer:
    def __init__(self, args=None):
        # Create CLI Parser to handle command-line arguments
        parser = argparse.ArgumentParser(description='GitHub and Stash arguments')
        
        # Unified arguments for GitHub and Stash interactions
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

        # Perform argument validation
        self.validate_arguments()

        # Perform the action based on provided method name
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
            if self.args.platform == 'github':
                rate_limit = platform_instance.get_rate_limit().core
                remaining_requests = rate_limit.remaining
                reset_time = rate_limit.reset
                current_time = time.time()

                if remaining_requests == 0:
                    wait_time = reset_time - current_time + 1  # Adding 1 second for safety
                    logger.info(f"GitHub Rate limit exceeded. Waiting for {wait_time} seconds.")
                    time.sleep(wait_time)

            elif self.args.platform == 'stash':
                # Placeholder for Stash rate limiting (adjust as per Stash API capabilities)
                remaining_requests = platform_instance.get_rate_limit()  # Pseudo-code for Stash rate limit check
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
            g = Github(token)
            self.check_rate_limit(g)

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

            # Paginate through all pages
            while org_repos:
                for repo in org_repos:
                    repo_list.append(repo)

                # Check if there are more repositories to fetch
                if len(org_repos) == per_page:
                    page += 1
                    org_repos = user.get_repos(page=page, per_page=per_page)
                else:
                    break

            # Filter repositories based on the project name, if provided
            if self.args.project:
                repo_list = [repo for repo in repo_list if repo.name == self.args.project]
                if not repo_list:
                    logger.info(f"No repositories found for project: {self.args.project}")
                    return

            # Clone the repositories
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
            stash = Stash(stash_url, token)
            self.check_rate_limit(stash)

            repo_list = []
            start = 0
            limit = 50  # Adjust based on the number of repositories per request

            while True:
                project_repos = stash.repositories.list(start=start, limit=limit)
                repo_list.extend(project_repos)

                # Check if there are more repositories to fetch
                if len(project_repos) < limit:
                    break
                else:
                    start += limit

            # Filter repositories based on the project name, if provided
            if self.args.project:
                repo_list = [repo for repo in repo_list if repo['name'] == self.args.project]
                if not repo_list:
                    logger.info(f"No repositories found for project: {self.args.project}")
                    return

            # Clone the repositories
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
            repo_name = repo['name']
            clone_url = repo['links']['clone'][0]['href']
            repo_dest = os.path.join(dest, repo_name)

            if not os.path.exists(repo_dest):
                logger.info(f"Cloning {repo_name} from Stash to {repo_dest}")
                self.systemCall(f'git clone {clone_url} {repo_dest}')
                self.fetchAndPullBranches(repo_dest)
            else:
                logger.info(f"Repository {repo_name} already exists. Skipping.")
        except Exception as e:
            logger.error(f"Error cloning repository from Stash: {e}")

    def clone_repo(self, repo, dest):
        """Clone a single repository from GitHub"""
        try:
            repo_name = repo.name
            clone_url = repo.clone_url
            repo_dest = os.path.join(dest, repo_name)

            if not os.path.exists(repo_dest):
                logger.info(f"Cloning {repo_name} from GitHub to {repo_dest}")
                self.systemCall(f'git clone {clone_url} {repo_dest}')
                self.fetchAndPullBranches(repo_dest)
            else:
                logger.info(f"Repository {repo_name} already exists. Skipping.")
        except Exception as e:
            logger.error(f"Error cloning repository from GitHub: {e}")

    def fetchAndPullBranches(self, repo_dest):
        """Fetch and pull all branches of a repository"""
        try:
            logger.info(f"Fetching and pulling branches for {repo_dest}")
            self.systemCall('git fetch --all', cwd=repo_dest)
            self.systemCall('git pull --all', cwd=repo_dest)
        except Exception as e:
            logger.error(f"Error pulling branches for {repo_dest}: {e}")

if __name__ == '__main__':
    # Initialize and run the GitRepoAnalyzer
    GitRepoAnalyzer()
