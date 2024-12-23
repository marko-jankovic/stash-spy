## Overview
Command-line tool designed to interact with GitHub and Stash (Bitbucket Server) APIs to clone repositories and perform Git-related operations. This tool supports cloning repositories from GitHub or Stash, managing rate limits, and working with multiple repositories at once using multithreading.

## Requirements

To use this tool, you need:
1. Python 3.x installed on your system.
2. Access to GitHub or Stash API tokens for authentication.
3. The required Python libraries (`github`, `stashy`, and `concurrent.futures`).

### Install Required Libraries
You can install the required libraries by running the following command:

```bash
pip install github stashy
```

## Setup

1. **Clone the Repository**
   - Clone repo
     ```bash
     git clone [https://github.com/your-repository.git](https://github.com/marko-jankovic/stash-spy.git)
     ```

2. **Get API Tokens**
   - **GitHub**: Go to [GitHub Personal Access Tokens](https://github.com/settings/tokens) to generate a personal access token.
   - **Stash/Bitbucket Server**: Follow your organization's guidelines to generate an API token.

3. **Set Up Your Environment**
   Ensure that you have access to a terminal or command prompt and Python installed. You will run the script from your terminal.

## Running the Tool

### Command-Line Arguments

The tool accepts the following command-line arguments:

- `-token`: **(Required)** API token for GitHub or Stash.
- `-username`: **(Required)** Your GitHub or Stash username.
- `-dest`: **(Required)** Destination folder where the repositories will be cloned.
- `-action`: **(Required)** Action to perform (e.g., `clone`, `analyze`).
- `-platform`: **(Required)** Specify the platform, either `github` or `stash`.
- `-project`: **(Optional)** The name of the project to filter repositories.
- `-olderThan`: **(Optional)** Time in minutes since last modification to consider.
- `-rate-limit`: **(Optional)** Rate limit time window for API requests (default is 60 seconds).
- `-stash-url`: **(Required for Stash)** The URL of the Stash server if using Stash.

### Example 1: Cloning GitHub Repositories

To clone all repositories from a GitHub user or organization, run the following command:
```bash
python index.py -token YOUR_GITHUB_TOKEN -username YOUR_GITHUB_USERNAME -dest /path/to/destination -action clone -platform github
```

To clone a specific project from GitHub:
```bash
python index.py -token YOUR_GITHUB_TOKEN -username YOUR_GITHUB_USERNAME -dest /path/to/destination -action clone -platform github -project "your-project-name"
```

### Example 2: Cloning Stash (Bitbucket Server) Repositories

To clone all repositories from a Stash project:
```bash
python index.py -token YOUR_STASH_TOKEN -username YOUR_STASH_USERNAME -dest /path/to/destination -action clone -platform stash -stash-url http://stash.yourcompany.com
```

To clone a specific project from Stash:
```bash
python index.py -token YOUR_STASH_TOKEN -username YOUR_STASH_USERNAME -dest /path/to/destination -action clone -platform stash -stash-url http://stash.yourcompany.com -project "your-project-name"
```

### Example 3: Setting a Rate Limit for API Requests

If you want to set a custom rate limit for API requests (in seconds), you can specify the `-rate-limit` argument:
```bash
python index.py -token YOUR_TOKEN -username YOUR_USERNAME -dest /path/to/destination -action clone -platform github -rate-limit 120
```

This will set the rate limit to 120 seconds between API requests.

## How the Tool Works

1. **Cloning Repositories**:
   - The tool fetches repositories from GitHub or Stash using the provided credentials and clones them to the specified destination folder.
   - If the `-project` argument is provided, only repositories matching the project name are cloned.
   
2. **Rate Limiting**:
   - The tool automatically checks the rate limit for GitHub or Stash API requests. If the rate limit is reached, it will wait until the limit resets before continuing.

3. **Parallel Cloning**:
   - The tool uses multithreading to clone repositories concurrently, speeding up the process.

4. **Fetching and Pulling Branches**:
   - After cloning each repository, the tool fetches and pulls all branches to ensure the local copy is up-to-date.

## Example of Log Output

During execution, the tool will log various activities in the terminal:
```bash
INFO: Cloning repository 'repo_name' from GitHub to /path/to/destination
INFO: Fetching and pulling branches for /path/to/destination/repo_name
ERROR: Error cloning repository: repository_name
```
