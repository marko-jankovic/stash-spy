## Overview

The **git_repo_analyzer** tool helps automate the process of cloning and analyzing repositories from GitHub or Stash (Bitbucket Server). It provides a command-line interface (CLI) that can be used to:
- Clone repositories from GitHub or Stash.
- Analyze repositories by checking their structure, branches, commits, and more.
- Handle rate limits for API requests.
- Perform other tasks like fetching all branches and pulling updates from cloned repositories.

---

## Installation

To get started with **git_repo_analyzer**, you need to ensure the following dependencies are installed:

### Dependencies:
1. **Python 3.x**: Ensure that Python is installed on your system.
2. **Required Libraries**:
   - `requests` (for interacting with GitHub and Stash APIs)
   - `github` (for GitHub API)
   - `stashy` (for Stash/Bitbucket Server API)
   - `argparse` (for command-line argument parsing)
   - `subprocess` (for executing system commands like `git`)

You can install the necessary Python libraries using `pip`:

```bash
pip install requests github stashy
```

---

## Usage

Once you have everything set up, you can use the `git_repo_analyzer.py` script to interact with GitHub or Stash. This tool supports different actions like cloning repositories, analyzing them, and checking rate limits.

### Clone Repositories

To clone repositories from GitHub or Stash, use the `-action clone` argument.

#### Command Example:

```bash
python git_repo_analyzer.py -token YOUR_TOKEN -username YOUR_USERNAME -dest /path/to/destination -action clone -platform github
```

#### Arguments:
- **`-token`**: Your GitHub or Stash API token.
- **`-username`**: Your GitHub or Stash username.
- **`-dest`**: Destination directory where the repositories will be cloned.
- **`-action`**: Use `clone` to clone repositories.
- **`-platform`**: Either `github` or `stash`.
- **`-project`**: Optional. The name of a specific project to clone.
- **`-olderThan`**: Optional. Filter repositories based on their last modification time (in minutes).

#### Example:
Clone all repositories from a GitHub user:

```bash
python git_repo_analyzer.py -token your_github_token -username your_github_username -dest ./repos -action clone -platform github
```

---

### Analyze All Repositories

To analyze all repositories in the destination folder, use the `-action analyze` argument. This will perform checks on the cloned repositories in the specified folder.

#### Command Example:

```bash
python git_repo_analyzer.py -token YOUR_TOKEN -username YOUR_USERNAME -dest /path/to/destination -action analyze -platform github
```

#### Explanation:
- This command will analyze all the repositories in the destination folder (`/path/to/destination`).
- You can further customize the analysis with options like `-project` to analyze only a specific repository or `-olderThan` to filter repositories by modification time.

---

### Check Rate Limit

To prevent hitting the rate limit when using GitHub or Stash API, you can check the rate limit status.

#### Command Example:

```bash
python git_repo_analyzer.py -token YOUR_TOKEN -username YOUR_USERNAME -dest /path/to/destination -action check-rate-limit -platform github
```

This will check the rate limit and wait if the requests have exceeded the limit.

---

## Command-Line Arguments

Below are the command-line arguments supported by the Git Repo Analyzer.

| Argument        | Description                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `-token`        | **Required**. API Token for GitHub or Stash.                                 |
| `-username`     | **Required**. GitHub or Stash username.                                      |
| `-dest`         | **Required**. Destination folder where repositories will be cloned or analyzed. |
| `-action`       | **Required**. Action to perform (`clone`, `analyze`, `check-rate-limit`).    |
| `-platform`     | **Required**. The platform to use (`github` or `stash`).                     |
| `-project`      | Optional. The specific project name to filter repositories.                  |
| `-olderThan`    | Optional. Analyze repositories modified within the last `X` minutes.        |
| `-rate-limit`   | Optional. Rate limit time window for API requests (default is 60 seconds).   |
| `-stash-url`    | Optional. The URL for the Stash server (required for Stash platform).       |

---

## Examples

### Example 1: Clone Repositories from GitHub

```bash
python git_repo_analyzer.py -token your_github_token -username your_github_username -dest ./repos -action clone -platform github
```

This command clones all repositories from the specified GitHub user into the `./repos` folder.

### Example 2: Analyze Repositories Older than 30 Minutes

```bash
python git_repo_analyzer.py -token your_github_token -username your_github_username -dest ./repos -action analyze -platform github -olderThan 30
```

This command analyzes repositories that have not been modified in the last 30 minutes.

### Example 3: Check Rate Limit on GitHub

```bash
python git_repo_analyzer.py -token your_github_token -username your_github_username -dest ./repos -action check-rate-limit -platform github
```

This command checks if the rate limit for GitHub API requests has been reached and waits for reset if necessary.

### Example 4: Clone Repositories from Stash

```bash
python git_repo_analyzer.py -token your_stash_token -username your_stash_username -dest ./stash_repos -action clone -platform stash -stash-url http://your.stash.server
```

This command clones all repositories from a Stash server into the `./stash_repos` folder.

