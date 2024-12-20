# Stashy Repository Manager

This is a Python script that helps to manage multiple Git repositories hosted on **Stash/Bitbucket Server** (formerly known as Stash). It supports repository cloning, updating, and cleaning, as well as flexible logging and rate-limiting features.

---

## Features

- **Clone repositories** from **Stash/Bitbucket Server**.
- **Update repositories** by fetching and resetting branches.
- **Clean stale repositories** based on a defined threshold.
- **Support for parallel cloning** to speed up repository management.
- **Flexible logging** with configurable log levels (`DEBUG`, `INFO`, `ERROR`).
- **Rate-limiting** to avoid hitting API limits or overloading the server.

---

## Requirements

- Python 3.x
- `stashy` module (for interacting with Stash/Bitbucket Server)
- `git` installed on your machine

Install dependencies:

```bash
pip install stashy
```

---

## Setup and Configuration

### 1. Clone the repository or download the script.

```bash
git clone https://github.com/yourusername/stashy-repository-manager.git
cd stashy-repository-manager
```

### 2. Configure the script

The script uses command-line arguments to customize the execution. You can use the following options:

- `-url` (Required): The base URL of your Stash/Bitbucket Server (e.g., `https://stash.example.com`).
- `-username` (Required): Your username for authentication.
- `-password` (Required): Your password or access token.
- `-dest` (Optional): Destination directory where repositories should be cloned.
- `-action` (Required): The action to perform (`clone`, `pull`, `clean`).
- `-project` (Optional): A specific project or repository to act upon (leave empty to operate on all projects).
- `-olderThan` (Optional): Time threshold (in minutes) for cleaning stale repositories.
- `-log-level` (Optional): Set the log level (`DEBUG`, `INFO`, `ERROR`).

---

## Actions

### 1. Clone Repositories

To clone all repositories for a specific project or all projects from **Stash/Bitbucket Server**:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action clone -dest ./repositories -project your_project_name
```

This will clone all repositories from `your_project_name` into the `repositories` folder.

To clone all repositories across all projects in Stash:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action clone -dest ./repositories
```

### 2. Pull (Update) Repositories

To update all cloned repositories by fetching the latest changes:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action pull -dest ./repositories -olderThan 60
```

This will check all repositories in the `repositories` folder that were updated more than 60 minutes ago.

### 3. Clean Stale Repositories

To clean repositories that haven't been updated in the last 30 days:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action clean -dest ./repositories -olderThan 43200
```

This will remove repositories that haven't been modified in the last 30 days (`43200` minutes).

---

## Logging

The script uses Python's built-in `logging` module to log events. The log level can be set with the `-log-level` argument:

- `DEBUG`: Logs detailed information (useful for debugging).
- `INFO`: Logs general progress and status.
- `ERROR`: Logs only error messages.

Example with `DEBUG` level:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action clone -dest ./repositories -log-level DEBUG
```

---

## Example Workflow

### Clone repositories from a specific project:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action clone -project 'my-project' -dest ./repos
```

### Pull (update) repositories older than 30 minutes:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action pull -dest ./repos -olderThan 30
```

### Clean repositories that haven't been updated in the last 7 days:

```bash
python stashy_repos.py -url https://stash.example.com -username your_username -password your_password -action clean -dest ./repos -olderThan 10080
```

---

## Additional Features

- **Parallel Cloning**: The script uses multithreading (`ThreadPoolExecutor`) to clone repositories in parallel, making it faster for large numbers of repositories.
- **Rate Limiting**: The script includes a rate-limiting feature to avoid hitting API or Git server rate limits. You can adjust the rate limit by modifying the script.
- **Stash/Bitbucket Server Integration**: The script works specifically with **Stash/Bitbucket Server** repositories by providing the necessary login credentials.
